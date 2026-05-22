#!/usr/bin/env python3
"""Interactive PyBullet viewer for the right LEAP hand URDF.

Loads ``robot_pybullet.urdf`` and creates one GUI slider per revolute joint,
bounded by that joint's lower/upper limits from the URDF. Moving a slider
updates the corresponding finger joint in real time.
"""

from __future__ import annotations

import argparse
import os
import time

import pybullet as p


def _decode_name(name) -> str:
    return name.decode("utf-8") if isinstance(name, bytes) else str(name)


def _slider_joints(body_id: int) -> list[tuple[int, str, float, float]]:
    """Return (joint_index, name, lower, upper) for actuated revolute joints only.

    Fixed joints (e.g. realtip attachments) are ignored — no sliders, no control.
    """
    joints: list[tuple[int, str, float, float]] = []
    for joint_index in range(p.getNumJoints(body_id)):
        info = p.getJointInfo(body_id, joint_index)
        joint_type = info[2]
        if joint_type == p.JOINT_FIXED:
            continue
        if joint_type != p.JOINT_REVOLUTE:
            continue
        lower = float(info[8])
        upper = float(info[9])
        name = _decode_name(info[1])
        joints.append((joint_index, name, lower, upper))
    return joints


def run_viewer(*, use_gui: bool = True) -> None:
    urdf_dir = os.path.dirname(os.path.abspath(__file__))
    urdf_path = os.path.join(urdf_dir, "robot_pybullet.urdf")

    cid = p.connect(p.GUI if use_gui else p.DIRECT)
    if cid < 0:
        raise RuntimeError("Failed to connect to PyBullet.")

    try:
        p.setAdditionalSearchPath(urdf_dir)
        p.resetDebugVisualizerCamera(
            cameraDistance=0.35,
            cameraYaw=55,
            cameraPitch=-25,
            cameraTargetPosition=[0.0, 0.0, 0.05],
        )
        p.setGravity(0, 0, 0)
        p.setRealTimeSimulation(0)

        body_id = p.loadURDF(
            urdf_path,
            basePosition=[-0.1, 0.01, 0.03],
            baseOrientation=p.getQuaternionFromEuler([1.57, 0, 3.14]),
            useFixedBase=True,
        )
        if body_id < 0:
            raise RuntimeError(f"Failed to load URDF: {urdf_path}")

        revolute = _slider_joints(body_id)
        slider_ids: list[int] = []
        joint_indices: list[int] = []

        for joint_index, name, lower, upper in revolute:
            initial = 0.0 if lower <= 0.0 <= upper else 0.5 * (lower + upper)
            p.resetJointState(body_id, joint_index, initial)
            joint_indices.append(joint_index)
            if use_gui:
                slider_ids.append(
                    p.addUserDebugParameter(name, lower, upper, initial)
                )

        print(f"Loaded {urdf_path}")
        print(f"Body id={body_id}, revolute joints={len(revolute)}")
        for joint_index, name, lower, upper in revolute:
            print(f"  joint {joint_index} ({name}): [{lower:.3f}, {upper:.3f}] rad")

        if not use_gui:
            # Debug parameters are GUI-only; just step with initial joint poses.
            for _ in range(240):
                p.stepSimulation()
                time.sleep(1.0 / 240.0)
            return

        while p.isConnected(cid):
            for joint_index, slider_id in zip(joint_indices, slider_ids):
                target = p.readUserDebugParameter(slider_id)
                p.resetJointState(body_id, joint_index, target)
            p.stepSimulation()
            time.sleep(1.0 / 240.0)
    finally:
        try:
            p.disconnect(cid)
        except Exception:
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PyBullet LEAP right-hand viewer with per-joint sliders."
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Use DIRECT connection instead of GUI (no interactive sliders).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_viewer(use_gui=not args.direct)


if __name__ == "__main__":
    main()
