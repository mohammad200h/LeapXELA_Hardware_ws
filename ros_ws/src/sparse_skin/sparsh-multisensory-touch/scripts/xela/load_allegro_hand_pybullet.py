#!/usr/bin/env python3
"""Load the XELA Allegro hand model in PyBullet.

PyBullet cannot load a `.xacro` file directly, so this script loads the
generated `ahrcpcpn.urdf` and rewrites its `package://xela_models/...` mesh
URIs to absolute local paths first.

Sensor patch link frames (used for taxel FK) are drawn as RGB axes:
  red = X, green = Y, blue = Z.
"""

from __future__ import annotations

import pathlib
import tempfile
import time
from typing import Dict, List, Tuple

import pybullet as p
import pybullet_data


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]  # .../sparsh-multisensory-touch
XELA_ROOT = PROJECT_ROOT / "assets" / "xela"
URDF_PATH = XELA_ROOT / "urdf" / "ahrcpcpn.urdf"
XACRO_PATH = XELA_ROOT / "urdf" / "allegro_hand_right.xacro"

# Sensor patch links used for taxel forward kinematics (see tactile_ssl/data/xela/utils.py).
# Grouped by body part: thumb / if (index) / mf (middle) / rf (ring) / palm.
PATCH_LINKS_BY_PART = {
    "thumb": (
        "3aftc_palm_link",
        "link_15_4x4_palm_link",
        "link_14_4x4_palm_link",
    ),
    "if": (
        "0aftc_palm_link",
        "link_2_4x4_palm_link",
        "link_1A_4x4_palm_link",
        "link_1B_4x4_palm_link",
    ),
    "mf": (
        "1aftc_palm_link",
        "link_6_4x4_palm_link",
        "link_5A_4x4_palm_link",
        "link_5B_4x4_palm_link",
    ),
    "rf": (
        "2aftc_palm_link",
        "link_10_4x4_palm_link",
        "link_9A_4x4_palm_link",
        "link_9B_4x4_palm_link",
    ),
    "palm": (
        "ahr_palm_2_4x6_palm_link",
        "ahr_palm_1_4x6_palm_link",
        "ahr_palm_3_4x6_palm_link",
    ),
}
PATCH_LINK_NAMES = tuple(
    name for names in PATCH_LINKS_BY_PART.values() for name in names
)


def make_pybullet_ready_urdf(source_urdf: pathlib.Path, asset_root: pathlib.Path) -> pathlib.Path:
    """Create a temporary URDF with local absolute mesh paths."""
    urdf_text = source_urdf.read_text()
    urdf_text = urdf_text.replace("package://xela_models/", f"{asset_root.as_posix()}/")

    temp_dir = pathlib.Path(tempfile.mkdtemp(prefix="xela_pybullet_"))
    temp_urdf = temp_dir / source_urdf.name
    temp_urdf.write_text(urdf_text)
    return temp_urdf


def print_joint_summary(body_id: int) -> None:
    print(f"Loaded body id: {body_id}")
    print(f"Number of joints: {p.getNumJoints(body_id)}")
    for joint_index in range(p.getNumJoints(body_id)):
        joint_info = p.getJointInfo(body_id, joint_index)
        joint_name = joint_info[1].decode("utf-8")
        joint_type = joint_info[2]
        print(f"  joint[{joint_index:03d}] {joint_name} type={joint_type}")


def build_link_name_to_index(body_id: int) -> Dict[str, int]:
    link_name_to_index: Dict[str, int] = {}
    for joint_index in range(p.getNumJoints(body_id)):
        joint_info = p.getJointInfo(body_id, joint_index)
        child_link_name = joint_info[12].decode("utf-8")
        link_name_to_index[child_link_name] = joint_index
    return link_name_to_index


def get_patch_link_indices(body_id: int) -> Dict[str, int]:
    link_name_to_index = build_link_name_to_index(body_id)
    patch_link_indices: Dict[str, int] = {}
    missing_links: List[str] = []

    for link_name in PATCH_LINK_NAMES:
        if link_name in link_name_to_index:
            patch_link_indices[link_name] = link_name_to_index[link_name]
        else:
            missing_links.append(link_name)

    if missing_links:
        print("Warning: patch links not found in URDF:")
        for link_name in missing_links:
            print(f"  - {link_name}")

    return patch_link_indices


def print_patch_frames_by_part(patch_link_indices: Dict[str, int]) -> None:
    """Print sensor patch frame names grouped by palm / thumb / mf / rf / if."""
    print("Sensor patch frames by part:")
    for part_name, link_names in PATCH_LINKS_BY_PART.items():
        print(f"  {part_name}:")
        for link_name in link_names:
            status = "ok" if link_name in patch_link_indices else "MISSING"
            print(f"    - {link_name}  [{status}]")


def _axis_endpoints(
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


def get_patch_axis_length(link_name: str, default: float) -> float:
    if "aftc" in link_name:
        return 0.05
    return default


class PatchFrameVisualizer:
    """Draw and update coordinate frames at XELA sensor patch links."""

    def __init__(
        self,
        body_id: int,
        patch_link_indices: Dict[str, int],
        axis_length: float = 0.015,
        line_width: float = 2.0,
    ) -> None:
        self.body_id = body_id
        self.patch_link_indices = patch_link_indices
        self.axis_length = axis_length
        self.line_width = line_width
        self.axis_line_ids: Dict[str, Tuple[int, int, int]] = {}
        self.label_ids: Dict[str, int] = {}
        self.axis_lengths: Dict[str, float] = {
            link_name: get_patch_axis_length(link_name, axis_length)
            for link_name in patch_link_indices
        }
        self.line_widths: Dict[str, float] = {
            link_name: 4.0 if "aftc" in link_name else line_width
            for link_name in patch_link_indices
        }
        self._create()

    def _create(self) -> None:
        for link_name, link_index in self.patch_link_indices.items():
            origin, orientation = self._get_link_frame(link_index)
            axis_length = self.axis_lengths[link_name]
            line_width = self.line_widths[link_name]
            x_end, y_end, z_end = _axis_endpoints(origin, orientation, axis_length)
            self.axis_line_ids[link_name] = (
                p.addUserDebugLine(origin, x_end, [1.0, 0.0, 0.0], lineWidth=line_width),
                p.addUserDebugLine(origin, y_end, [0.0, 1.0, 0.0], lineWidth=line_width),
                p.addUserDebugLine(origin, z_end, [0.0, 0.0, 1.0], lineWidth=line_width),
            )
            label = link_name.replace("_palm_link", "").replace("link_", "")
            self.label_ids[link_name] = p.addUserDebugText(
                label,
                [origin[0], origin[1], origin[2] + 0.006],
                textColorRGB=[1.0, 1.0, 0.0],
                textSize=1.5 if "aftc" in link_name else 1.0,
            )

    def _get_link_frame(self, link_index: int) -> Tuple[Tuple[float, float, float], Tuple[float, float, float, float]]:
        link_state = p.getLinkState(
            self.body_id,
            link_index,
            computeForwardKinematics=True,
        )
        origin = link_state[4]
        orientation = link_state[5]
        return origin, orientation

    def update(self) -> None:
        for link_name, link_index in self.patch_link_indices.items():
            origin, orientation = self._get_link_frame(link_index)
            axis_length = self.axis_lengths[link_name]
            line_width = self.line_widths[link_name]
            x_end, y_end, z_end = _axis_endpoints(origin, orientation, axis_length)
            x_line_id, y_line_id, z_line_id = self.axis_line_ids[link_name]
            p.addUserDebugLine(origin, x_end, [1.0, 0.0, 0.0], replaceItemUniqueId=x_line_id, lineWidth=line_width)
            p.addUserDebugLine(origin, y_end, [0.0, 1.0, 0.0], replaceItemUniqueId=y_line_id, lineWidth=line_width)
            p.addUserDebugLine(origin, z_end, [0.0, 0.0, 1.0], replaceItemUniqueId=z_line_id, lineWidth=line_width)
            label = link_name.replace("_palm_link", "").replace("link_", "")
            p.addUserDebugText(
                label,
                [origin[0], origin[1], origin[2] + 0.006],
                textColorRGB=[1.0, 1.0, 0.0],
                textSize=1.5 if "aftc" in link_name else 1.0,
                replaceItemUniqueId=self.label_ids[link_name],
            )


class FrameColorLegend:
    """Draw a fixed world-space legend for patch frame axis colors."""

    def __init__(
        self,
        origin: Tuple[float, float, float] = (-0.10, -0.10, 0.22),
        axis_length: float = 0.035,
        line_width: float = 3.0,
    ) -> None:
        self.origin = origin
        self.axis_length = axis_length
        self.line_width = line_width

        x_end = [origin[0] + axis_length, origin[1], origin[2]]
        y_end = [origin[0], origin[1] + axis_length, origin[2]]
        z_end = [origin[0], origin[1], origin[2] + axis_length]

        self.axis_line_ids = (
            p.addUserDebugLine(origin, x_end, [1.0, 0.0, 0.0], lineWidth=line_width),
            p.addUserDebugLine(origin, y_end, [0.0, 1.0, 0.0], lineWidth=line_width),
            p.addUserDebugLine(origin, z_end, [0.0, 0.0, 1.0], lineWidth=line_width),
        )
        label_offset = axis_length * 0.25
        self.text_ids = (
            p.addUserDebugText(
                "Patch frame guide",
                [origin[0], origin[1], origin[2] + axis_length + 0.012],
                textColorRGB=[1.0, 1.0, 1.0],
                textSize=1.2,
            ),
            p.addUserDebugText(
                "X = Red",
                [x_end[0] + label_offset, x_end[1], x_end[2]],
                textColorRGB=[1.0, 0.0, 0.0],
                textSize=1.2,
            ),
            p.addUserDebugText(
                "Y = Green",
                [y_end[0], y_end[1] + label_offset, y_end[2]],
                textColorRGB=[0.0, 1.0, 0.0],
                textSize=1.2,
            ),
            p.addUserDebugText(
                "Z = Blue",
                [z_end[0], z_end[1], z_end[2] + label_offset],
                textColorRGB=[0.0, 0.0, 1.0],
                textSize=1.2,
            ),
        )

    @staticmethod
    def print_console_guide() -> None:
        print("Coordinate frame color guide (patch link frames):")
        print("  X axis -> Red")
        print("  Y axis -> Green")
        print("  Z axis -> Blue")
        print("A world-aligned legend is also drawn in the PyBullet viewport.")


def load_ground_plane() -> None:
    """Load the PyBullet ground plane if available."""
    data_path = pathlib.Path(pybullet_data.getDataPath()).resolve()
    plane_path = data_path / "plane.urdf"
    try:
        if plane_path.exists():
            p.loadURDF(str(plane_path))
        else:
            p.loadURDF("plane.urdf")
    except p.error:
        print(f"Warning: could not load ground plane from {plane_path}; continuing without it.")


def main() -> None:
    if not URDF_PATH.exists():
        raise FileNotFoundError(f"URDF not found: {URDF_PATH}")

    temp_urdf = make_pybullet_ready_urdf(URDF_PATH, XELA_ROOT)

    print(f"Xacro source: {XACRO_PATH}")
    print(f"Generated URDF used for PyBullet: {URDF_PATH}")
    print(f"Temporary URDF for loading: {temp_urdf}")

    client_id = p.connect(p.GUI)
    if client_id < 0:
        raise RuntimeError("Failed to connect to PyBullet GUI")

    p.setAdditionalSearchPath(str(pybullet_data.getDataPath()))
    p.setGravity(0.0, 0.0, -9.81)
    p.configureDebugVisualizer(p.COV_ENABLE_GUI, 1)

    load_ground_plane()

    start_position = [0.0, 0.0, 0.15]
    start_orientation = p.getQuaternionFromEuler([0.0, 0.0, 0.0])
    hand_id = p.loadURDF(
        str(temp_urdf),
        basePosition=start_position,
        baseOrientation=start_orientation,
        useFixedBase=True,
        flags=p.URDF_USE_INERTIA_FROM_FILE,
    )

    print_joint_summary(hand_id)

    patch_link_indices = get_patch_link_indices(hand_id)
    print_patch_frames_by_part(patch_link_indices)
    print(f"Visualizing {len(patch_link_indices)} sensor patch frames.")
    FrameColorLegend.print_console_guide()
    FrameColorLegend()
    frame_visualizer = PatchFrameVisualizer(hand_id, patch_link_indices, axis_length=0.015)

    for _ in range(240):
        p.stepSimulation()
        frame_visualizer.update()
        time.sleep(1.0 / 240.0)

    print("Close the PyBullet window or press Ctrl+C to exit.")
    try:
        while p.isConnected():
            p.stepSimulation()
            frame_visualizer.update()
            time.sleep(1.0 / 240.0)
    except KeyboardInterrupt:
        pass
    finally:
        if p.isConnected():
            p.disconnect()


if __name__ == "__main__":
    main()
