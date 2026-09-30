from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

SS_LINK_SUBSTRING = "_ss_"
PALM_LINK_PREFIX = "ahr_palm_"
KNUCKLE_LINK_SUFFIX = "_4x4_palm_link"
FINGERTIP_SS_SUBSTRING = "fingertip_ss"
AFTC_SUBSTRING = "aftc"
EXTRA_FRAME_LINKS = ("th_fingertip",)
DEFAULT_AXIS_LENGTH = 0.015
FINGERTIP_AXIS_LENGTH = 0.048
DEFAULT_LINE_WIDTH = 2.0
FINGERTIP_LINE_WIDTH = 4.8


def _is_sparseskin_frame(link_name: str) -> bool:
    return (
        SS_LINK_SUBSTRING in link_name
        or link_name.startswith(PALM_LINK_PREFIX)
        or link_name.endswith(KNUCKLE_LINK_SUFFIX)
        or AFTC_SUBSTRING in link_name
    )


def _default_urdf_path(sparseskin: bool = False) -> str:
    name = "hand_ss.urdf" if sparseskin else "hand.urdf"
    return str(Path(__file__).resolve().parent / name)


def _default_joint_config_path() -> Path:
    return Path(__file__).resolve().parent.parent / "joint_config.json"


def _load_joint_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or _default_joint_config_path()
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _hardware_pose_to_sim_by_name(
    joint_config: dict[str, Any], pose_name: str = "open"
) -> dict[str, float]:
    """
    Map leapXela.sim.hand_pose[pose_name] (hardware motor order) to sim rad by joint name.

    Motor indices follow leapXela.hardware.map (th 0-3, if 4-7, mf 8-11, rf 12-15).
    """
    leap = joint_config["leapXela"]
    hw = leap["hardware"]
    sim = leap["sim"]
    pose = list(sim["hand_pose"][pose_name])
    if len(pose) != 16:
        raise ValueError(
            f"Expected 16 values in hand_pose['{pose_name}'], got {len(pose)}"
        )

    by_name: dict[str, float] = {}
    for finger in ("th", "if", "mf", "rf"):
        for idx_str, joint in hw["map"][finger].items():
            idx = int(idx_str)
            name = f"{finger}_{joint}"
            section = "thumb" if finger == "th" else "fingers"
            hw_limits = hw[section][joint]
            hw_val = float(pose[idx])
            hw_zero = float(hw_limits["zero"])
            inverted = float(hw_limits["lower"]) > float(hw_limits["upper"])
            # Inverse of uniform sim->hardware offset used in teleop conversion.
            sim_val = (hw_zero - hw_val) if inverted else (hw_val - hw_zero)
            by_name[name] = sim_val
    return by_name


def _make_pybullet_ready_urdf(source_urdf: Path) -> Path:
    """Rewrite package://assets/... to absolute paths next to the URDF."""
    urdf_text = source_urdf.read_text(encoding="utf-8")
    urdf_text = urdf_text.replace(
        "package://assets/",
        f"{(source_urdf.parent / 'assets').as_posix()}/",
    )
    temp_dir = Path(tempfile.mkdtemp(prefix="xela_hand_pybullet_"))
    temp_urdf = temp_dir / source_urdf.name
    temp_urdf.write_text(urdf_text, encoding="utf-8")
    return temp_urdf


def _is_large_frame(link_name: str) -> bool:
    return (
        FINGERTIP_SS_SUBSTRING in link_name
        or AFTC_SUBSTRING in link_name
        or link_name == "th_fingertip"
    )


def _axis_length(link_name: str) -> float:
    if _is_large_frame(link_name):
        return FINGERTIP_AXIS_LENGTH
    return DEFAULT_AXIS_LENGTH


def _line_width(link_name: str) -> float:
    if _is_large_frame(link_name):
        return FINGERTIP_LINE_WIDTH
    return DEFAULT_LINE_WIDTH


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


def _get_frame_link_indices(p, body_id: int) -> Dict[str, int]:
    link_name_to_index: Dict[str, int] = {}
    for joint_index in range(p.getNumJoints(body_id)):
        info = p.getJointInfo(body_id, joint_index)
        child_name = info[12].decode("utf-8")
        link_name_to_index[child_name] = joint_index

    frame_links = {
        name: index
        for name, index in link_name_to_index.items()
        if _is_sparseskin_frame(name)
    }
    for name in EXTRA_FRAME_LINKS:
        if name in link_name_to_index:
            frame_links[name] = link_name_to_index[name]
    return frame_links


def _joint_slider_limits(lower: float, upper: float) -> tuple[float, float]:
    if lower <= upper:
        return lower, upper
    return upper, lower


def _create_joint_sliders(
    p,
    body_id: int,
    initial_pose_by_name: dict[str, float] | None = None,
) -> list[tuple[int, int]]:
    initial_pose_by_name = initial_pose_by_name or {}
    sliders: list[tuple[int, int]] = []
    for joint_idx in range(p.getNumJoints(body_id)):
        info = p.getJointInfo(body_id, joint_idx)
        if info[2] not in (p.JOINT_REVOLUTE, p.JOINT_PRISMATIC):
            continue
        name = info[1].decode("utf-8")
        lo, hi = _joint_slider_limits(float(info[8]), float(info[9]))
        if lo == hi:
            lo, hi = -3.14, 3.14
        if name in initial_pose_by_name:
            start = float(initial_pose_by_name[name])
        else:
            start = 0.5 * (lo + hi)
        start = min(max(start, lo), hi)
        slider_id = p.addUserDebugParameter(name, lo, hi, start)
        p.resetJointState(body_id, joint_idx, start)
        sliders.append((joint_idx, slider_id))
        print(f"  slider {name}: start={start:.4f} [{lo:.4f}, {hi:.4f}]")
    return sliders


def _apply_joint_sliders(p, body_id: int, sliders: list[tuple[int, int]]) -> None:
    for joint_idx, slider_id in sliders:
        pos = p.readUserDebugParameter(slider_id)
        p.resetJointState(body_id, joint_idx, pos)


class _SsFrameVisualizer:
    """Draw and update RGB coordinate frames on sparse-skin links."""

    def __init__(self, p, body_id: int) -> None:
        self._p = p
        self.body_id = body_id
        self.link_indices = _get_frame_link_indices(p, body_id)
        self.axis_line_ids: Dict[str, Tuple[int, int, int]] = {}
        self.label_ids: Dict[str, int] = {}
        if not self.link_indices:
            print("Warning: sparseskin=True but no sparse-skin frame links found in URDF")
            return
        print(f"Drawing frames on {len(self.link_indices)} sparseskin links:")
        for link_name in sorted(self.link_indices):
            print(f"  - {link_name}")
        self._create()

    def _get_link_frame(
        self, link_index: int
    ) -> Tuple[Tuple[float, float, float], Tuple[float, float, float, float]]:
        link_state = self._p.getLinkState(
            self.body_id, link_index, computeForwardKinematics=True
        )
        return link_state[4], link_state[5]

    def _create(self) -> None:
        p = self._p
        for link_name, link_index in self.link_indices.items():
            origin, orientation = self._get_link_frame(link_index)
            length = _axis_length(link_name)
            width = _line_width(link_name)
            x_end, y_end, z_end = _axis_endpoints(p, origin, orientation, length)
            self.axis_line_ids[link_name] = (
                p.addUserDebugLine(origin, x_end, [1.0, 0.0, 0.0], lineWidth=width),
                p.addUserDebugLine(origin, y_end, [0.0, 1.0, 0.0], lineWidth=width),
                p.addUserDebugLine(origin, z_end, [0.0, 0.0, 1.0], lineWidth=width),
            )
            self.label_ids[link_name] = p.addUserDebugText(
                link_name,
                [origin[0], origin[1], origin[2] + 0.006],
                textColorRGB=[1.0, 1.0, 0.0],
                textSize=1.5 if _is_large_frame(link_name) else 1.0,
            )

    def update(self) -> None:
        if not self.link_indices:
            return
        p = self._p
        for link_name, link_index in self.link_indices.items():
            origin, orientation = self._get_link_frame(link_index)
            length = _axis_length(link_name)
            width = _line_width(link_name)
            x_end, y_end, z_end = _axis_endpoints(p, origin, orientation, length)
            x_id, y_id, z_id = self.axis_line_ids[link_name]
            p.addUserDebugLine(
                origin, x_end, [1.0, 0.0, 0.0],
                replaceItemUniqueId=x_id, lineWidth=width,
            )
            p.addUserDebugLine(
                origin, y_end, [0.0, 1.0, 0.0],
                replaceItemUniqueId=y_id, lineWidth=width,
            )
            p.addUserDebugLine(
                origin, z_end, [0.0, 0.0, 1.0],
                replaceItemUniqueId=z_id, lineWidth=width,
            )
            p.addUserDebugText(
                link_name,
                [origin[0], origin[1], origin[2] + 0.006],
                textColorRGB=[1.0, 1.0, 0.0],
                textSize=1.5 if _is_large_frame(link_name) else 1.0,
                replaceItemUniqueId=self.label_ids[link_name],
            )


def _run_pybullet(
    urdf_path: str,
    use_gui: bool = True,
    sparseskin: bool = False,
    initial_pose_by_name: dict[str, float] | None = None,
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
        urdf_path = _default_urdf_path(sparseskin=sparseskin)

    urdf = Path(urdf_path).expanduser().resolve()
    if not urdf.exists():
        raise FileNotFoundError(f"URDF not found: {urdf}")
    if urdf.is_dir():
        raise IsADirectoryError(
            f"URDF path points to a directory, not a file: {urdf}"
        )

    ready_urdf = _make_pybullet_ready_urdf(urdf)

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
            str(ready_urdf),
            basePosition=[0.0, 0.0, 0.2],
            baseOrientation=p.getQuaternionFromEuler([0.0, 0.0, 0.0]),
            useFixedBase=True,
        )

        frame_viz = _SsFrameVisualizer(p, body_id) if sparseskin else None
        sliders: list[tuple[int, int]] = []
        if use_gui:
            print("Initializing joint sliders from hand_pose:")
            sliders = _create_joint_sliders(p, body_id, initial_pose_by_name)
        elif initial_pose_by_name:
            for joint_idx in range(p.getNumJoints(body_id)):
                info = p.getJointInfo(body_id, joint_idx)
                if info[2] not in (p.JOINT_REVOLUTE, p.JOINT_PRISMATIC):
                    continue
                name = info[1].decode("utf-8")
                if name in initial_pose_by_name:
                    p.resetJointState(body_id, joint_idx, float(initial_pose_by_name[name]))

        if use_gui:
            while p.isConnected(cid):
                _apply_joint_sliders(p, body_id, sliders)
                if frame_viz is not None:
                    frame_viz.update()
                p.stepSimulation()
                time.sleep(1.0 / 240.0)
        else:
            for _ in range(240):
                if frame_viz is not None:
                    frame_viz.update()
                p.stepSimulation()
                time.sleep(1.0 / 240.0)
    finally:
        try:
            p.disconnect(cid)
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize hand URDF in PyBullet.")
    parser.add_argument(
        "--urdf",
        default=None,
        help="Path to URDF (default: hand_ss.urdf with --sparseskin, else hand.urdf)",
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
        help="Load/regenerate hand_ss.urdf and draw RGB axes on sparse-skin frames",
    )
    parser.add_argument(
        "--pose",
        default="open",
        help="Initial hand_pose key from joint_config.json (default: open)",
    )
    args = parser.parse_args()

    sparseskin = bool(args.sparseskin)
    urdf_path = args.urdf or _default_urdf_path(sparseskin=sparseskin)

    if args.urdf is None:
        try:
            from hand import write_hand_urdf
        except ImportError:  # pragma: no cover
            from .hand import write_hand_urdf  # type: ignore
        write_hand_urdf(urdf_path, sparseskin=sparseskin)

    joint_config = _load_joint_config()
    initial_pose = _hardware_pose_to_sim_by_name(joint_config, pose_name=args.pose)

    use_gui = not args.direct
    print(f"Loading URDF in PyBullet: {urdf_path}")
    print(f"PyBullet GUI: {use_gui}")
    print(f"sparseskin: {sparseskin}")
    print(f"initial pose: {args.pose}")
    _run_pybullet(
        urdf_path=urdf_path,
        use_gui=use_gui,
        sparseskin=sparseskin,
        initial_pose_by_name=initial_pose,
    )


if __name__ == "__main__":
    main()
