from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Dict, List, Tuple

SS_LINK_SUBSTRING = "_ss_"
PALM_LINK_PREFIX = "ahr_palm_"
KNUCKLE_LINK_SUFFIX = "_4x4_palm_link"
DEFAULT_AXIS_LENGTH = 0.015
DEFAULT_LINE_WIDTH = 2.0


def _default_urdf_path() -> str:
    return str(Path(__file__).resolve().parent / "palm.urdf")


def _is_sparseskin_frame(link_name: str) -> bool:
    return (
        SS_LINK_SUBSTRING in link_name
        or link_name.startswith(PALM_LINK_PREFIX)
        or link_name.endswith(KNUCKLE_LINK_SUFFIX)
    )


def _axis_endpoints(
    p,
    origin: Tuple[float, float, float],
    orientation: Tuple[float, float, float, float],
    axis_length: float,
) -> Tuple[List[float], List[float], List[float]]:
    rot = p.getMatrixFromQuaternion(orientation)
    x_axis = (rot[0], rot[3], rot[6])
    y_axis = (rot[1], rot[4], rot[7])
    z_axis = (rot[2], rot[5], rot[8])

    def endpoint(axis: Tuple[float, float, float]) -> List[float]:
        return [
            origin[0] + axis_length * axis[0],
            origin[1] + axis_length * axis[1],
            origin[2] + axis_length * axis[2],
        ]

    return endpoint(x_axis), endpoint(y_axis), endpoint(z_axis)


def _get_ss_link_indices(p, body_id: int) -> Dict[str, int]:
    link_indices: Dict[str, int] = {}
    for joint_index in range(p.getNumJoints(body_id)):
        info = p.getJointInfo(body_id, joint_index)
        child_name = info[12].decode("utf-8")
        if _is_sparseskin_frame(child_name):
            link_indices[child_name] = joint_index
    return link_indices


def _draw_ss_frames(p, body_id: int) -> None:
    """Draw RGB axes + labels on sparse-skin / palm sensor frame links."""
    link_indices = _get_ss_link_indices(p, body_id)
    if not link_indices:
        print("Warning: sparseskin=True but no sparse-skin frame links found in URDF")
        return

    print(f"Drawing frames on {len(link_indices)} sparseskin links:")
    for link_name, link_index in sorted(link_indices.items()):
        link_state = p.getLinkState(body_id, link_index, computeForwardKinematics=True)
        origin, orientation = link_state[4], link_state[5]
        x_end, y_end, z_end = _axis_endpoints(
            p, origin, orientation, DEFAULT_AXIS_LENGTH
        )
        p.addUserDebugLine(origin, x_end, [1.0, 0.0, 0.0], lineWidth=DEFAULT_LINE_WIDTH)
        p.addUserDebugLine(origin, y_end, [0.0, 1.0, 0.0], lineWidth=DEFAULT_LINE_WIDTH)
        p.addUserDebugLine(origin, z_end, [0.0, 0.0, 1.0], lineWidth=DEFAULT_LINE_WIDTH)
        p.addUserDebugText(
            link_name,
            [origin[0], origin[1], origin[2] + 0.006],
            textColorRGB=[1.0, 1.0, 0.0],
            textSize=1.0,
        )
        print(f"  - {link_name}")


def _run_pybullet(
    urdf_path: str, use_gui: bool = True, sparseskin: bool = False
) -> None:
    try:
        import pybullet as p  # type: ignore
        import pybullet_data  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "PyBullet is required. Install it (e.g. `sudo apt install python3-pybullet` "
            "or `pip install pybullet`)."
        ) from e

    if not str(urdf_path).strip():
        urdf_path = _default_urdf_path()

    urdf = Path(urdf_path).expanduser().resolve()
    if not urdf.exists():
        raise FileNotFoundError(f"URDF not found: {urdf}")
    if urdf.is_dir():
        raise IsADirectoryError(
            f"URDF path points to a directory, not a file: {urdf}"
        )

    cid = p.connect(p.GUI if use_gui else p.DIRECT)
    try:
        data_path = Path(pybullet_data.getDataPath()).resolve()
        p.setAdditionalSearchPath(str(data_path))
        p.setAdditionalSearchPath(str(urdf.parent))
        p.setGravity(0, 0, -9.81)
        try:
            plane_path = data_path / "plane.urdf"
            p.loadURDF(str(plane_path) if plane_path.exists() else "plane.urdf")
        except Exception:
            pass

        body_id = p.loadURDF(
            str(urdf),
            basePosition=[0.0, 0.0, 0.0],
            baseOrientation=p.getQuaternionFromEuler([0.0, 0.0, 0.0]),
            useFixedBase=True,
        )

        if sparseskin:
            _draw_ss_frames(p, body_id)

        if use_gui:
            while p.isConnected(cid):
                p.stepSimulation()
                time.sleep(1.0 / 240.0)
        else:
            for _ in range(240):
                p.stepSimulation()
                time.sleep(1.0 / 240.0)
    finally:
        try:
            p.disconnect(cid)
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize palm URDF in PyBullet.")
    parser.add_argument(
        "--urdf",
        default=None,
        help="Path to URDF (default: palm.urdf in this directory)",
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Use DIRECT connection instead of GUI",
    )
    parser.add_argument(
        "--sparseskin",
        action="store_true",
        default=False,
        help="Regenerate palm with sparse-skin frames and draw RGB axes on them",
    )
    args = parser.parse_args()

    urdf_path = args.urdf or _default_urdf_path()
    sparseskin = bool(args.sparseskin)

    if sparseskin and args.urdf is None:
        try:
            from palm import write_palm_urdf
        except ImportError:  # pragma: no cover
            from .palm import write_palm_urdf  # type: ignore
        write_palm_urdf(urdf_path, sparseskin=True)

    use_gui = not args.direct
    print(f"Loading URDF in PyBullet: {urdf_path}")
    print(f"PyBullet GUI: {use_gui}")
    print(f"sparseskin: {sparseskin}")
    _run_pybullet(urdf_path=urdf_path, use_gui=use_gui, sparseskin=sparseskin)


if __name__ == "__main__":
    main()
