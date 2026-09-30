#!/usr/bin/env python3
"""Load leapXela_ss/robot.urdf in PyBullet.

PyBullet does not resolve package:// mesh URIs, so this script rewrites them
to absolute paths under leapXela_ss/ before loading.

Coordinate frames (red=X, green=Y, blue=Z) are drawn on every link whose name
contains "_ss_" (e.g. 46_ss_1, 44_ss_rf_3, fingertip_ss_rf_1).
"""

from __future__ import annotations

import pathlib
import tempfile
import time
from typing import Dict, List, Tuple

import pybullet as p
import pybullet_data

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
URDF_PATH = SCRIPT_DIR / "robot.urdf"
SS_LINK_SUBSTRING = "_ss_"
FINGERTIP_SS_SUBSTRING = "fingertip_ss"
EXTRA_FRAME_LINKS = ("th_fingertip",)
DEFAULT_AXIS_LENGTH = 0.015
FINGERTIP_AXIS_LENGTH = 0.04 * 1.2  # 0.048 m (+20%)
DEFAULT_LINE_WIDTH = 2.0
FINGERTIP_LINE_WIDTH = 4.0 * 1.2  # 4.8


def make_pybullet_ready_urdf(source_urdf: pathlib.Path) -> pathlib.Path:
    """Rewrite package://assets/... to absolute paths next to the URDF."""
    urdf_text = source_urdf.read_text()
    urdf_text = urdf_text.replace(
        "package://assets/",
        f"{(source_urdf.parent / 'assets').as_posix()}/",
    )

    temp_dir = pathlib.Path(tempfile.mkdtemp(prefix="leapxela_ss_pybullet_"))
    temp_urdf = temp_dir / source_urdf.name
    temp_urdf.write_text(urdf_text)
    return temp_urdf


def build_link_name_to_index(body_id: int) -> Dict[str, int]:
    link_name_to_index: Dict[str, int] = {}
    for joint_index in range(p.getNumJoints(body_id)):
        joint_info = p.getJointInfo(body_id, joint_index)
        child_link_name = joint_info[12].decode("utf-8")
        link_name_to_index[child_link_name] = joint_index
    return link_name_to_index


def get_frame_link_indices(body_id: int) -> Dict[str, int]:
    """Return link indices for '_ss_' links plus explicit extras (e.g. th_fingertip)."""
    link_name_to_index = build_link_name_to_index(body_id)
    frame_links = {
        name: index
        for name, index in link_name_to_index.items()
        if SS_LINK_SUBSTRING in name
    }
    for name in EXTRA_FRAME_LINKS:
        if name in link_name_to_index:
            frame_links[name] = link_name_to_index[name]
        else:
            print(f"Warning: extra frame link not found: {name}")
    if not frame_links:
        print(f"Warning: no frame links were found.")
    return frame_links


def is_large_fingertip_frame(link_name: str) -> bool:
    return FINGERTIP_SS_SUBSTRING in link_name or link_name == "th_fingertip"


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


def get_link_axis_length(link_name: str) -> float:
    if is_large_fingertip_frame(link_name):
        return FINGERTIP_AXIS_LENGTH
    return DEFAULT_AXIS_LENGTH


def get_link_line_width(link_name: str) -> float:
    if is_large_fingertip_frame(link_name):
        return FINGERTIP_LINE_WIDTH
    return DEFAULT_LINE_WIDTH


def get_link_label_size(link_name: str) -> float:
    if is_large_fingertip_frame(link_name):
        return 1.5
    return 1.0


class LinkFrameVisualizer:
    """Draw and update RGB coordinate frames at selected links."""

    def __init__(
        self,
        body_id: int,
        link_indices: Dict[str, int],
    ) -> None:
        self.body_id = body_id
        self.link_indices = link_indices
        self.axis_lengths = {
            link_name: get_link_axis_length(link_name) for link_name in link_indices
        }
        self.line_widths = {
            link_name: get_link_line_width(link_name) for link_name in link_indices
        }
        self.label_sizes = {
            link_name: get_link_label_size(link_name) for link_name in link_indices
        }
        self.axis_line_ids: Dict[str, Tuple[int, int, int]] = {}
        self.label_ids: Dict[str, int] = {}
        self._create()

    def _get_link_frame(
        self, link_index: int
    ) -> Tuple[Tuple[float, float, float], Tuple[float, float, float, float]]:
        link_state = p.getLinkState(
            self.body_id,
            link_index,
            computeForwardKinematics=True,
        )
        return link_state[4], link_state[5]

    def _create(self) -> None:
        for link_name, link_index in self.link_indices.items():
            origin, orientation = self._get_link_frame(link_index)
            axis_length = self.axis_lengths[link_name]
            line_width = self.line_widths[link_name]
            x_end, y_end, z_end = _axis_endpoints(origin, orientation, axis_length)
            self.axis_line_ids[link_name] = (
                p.addUserDebugLine(origin, x_end, [1.0, 0.0, 0.0], lineWidth=line_width),
                p.addUserDebugLine(origin, y_end, [0.0, 1.0, 0.0], lineWidth=line_width),
                p.addUserDebugLine(origin, z_end, [0.0, 0.0, 1.0], lineWidth=line_width),
            )
            self.label_ids[link_name] = p.addUserDebugText(
                link_name,
                [origin[0], origin[1], origin[2] + 0.006],
                textColorRGB=[1.0, 1.0, 0.0],
                textSize=self.label_sizes[link_name],
            )

    def update(self) -> None:
        for link_name, link_index in self.link_indices.items():
            origin, orientation = self._get_link_frame(link_index)
            axis_length = self.axis_lengths[link_name]
            line_width = self.line_widths[link_name]
            x_end, y_end, z_end = _axis_endpoints(origin, orientation, axis_length)
            x_line_id, y_line_id, z_line_id = self.axis_line_ids[link_name]
            p.addUserDebugLine(
                origin, x_end, [1.0, 0.0, 0.0],
                replaceItemUniqueId=x_line_id, lineWidth=line_width,
            )
            p.addUserDebugLine(
                origin, y_end, [0.0, 1.0, 0.0],
                replaceItemUniqueId=y_line_id, lineWidth=line_width,
            )
            p.addUserDebugLine(
                origin, z_end, [0.0, 0.0, 1.0],
                replaceItemUniqueId=z_line_id, lineWidth=line_width,
            )
            p.addUserDebugText(
                link_name,
                [origin[0], origin[1], origin[2] + 0.006],
                textColorRGB=[1.0, 1.0, 0.0],
                textSize=self.label_sizes[link_name],
                replaceItemUniqueId=self.label_ids[link_name],
            )


def print_joint_summary(body_id: int) -> None:
    print(f"Loaded body id: {body_id}")
    print(f"Number of joints: {p.getNumJoints(body_id)}")
    for joint_index in range(p.getNumJoints(body_id)):
        info = p.getJointInfo(body_id, joint_index)
        name = info[1].decode("utf-8")
        jtype = info[2]
        child = info[12].decode("utf-8")
        print(f"  joint[{joint_index:03d}] {name:30s} type={jtype} -> {child}")


def main() -> None:
    if not URDF_PATH.is_file():
        raise FileNotFoundError(f"URDF not found: {URDF_PATH}")

    ready_urdf = make_pybullet_ready_urdf(URDF_PATH)

    p.connect(p.GUI)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)
    p.loadURDF("plane.urdf")

    robot_id = p.loadURDF(
        ready_urdf.as_posix(),
        basePosition=[0, 0, 0.15],
        baseOrientation=p.getQuaternionFromEuler([0, 0, 0]),
        useFixedBase=True,
        flags=p.URDF_USE_INERTIA_FROM_FILE,
    )
    print_joint_summary(robot_id)

    frame_link_indices = get_frame_link_indices(robot_id)
    print(f"\nDrawing frames on {len(frame_link_indices)} links:")
    for link_name in sorted(frame_link_indices):
        print(f"  - {link_name}")

    frame_visualizer = LinkFrameVisualizer(robot_id, frame_link_indices)

    while p.isConnected():
        frame_visualizer.update()
        p.stepSimulation()
        time.sleep(1.0 / 240.0)


if __name__ == "__main__":
    main()
