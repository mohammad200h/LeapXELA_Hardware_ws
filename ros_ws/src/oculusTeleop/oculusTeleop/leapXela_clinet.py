#!/usr/bin/env python3
"""
ROS 2 subscriber: cmd_xela JointState -> LeapXela hand in PyBullet.

Subscribes to the topic published by avp_leap_server (default: cmd_xela) and
drives the leapXela_right URDF using the same 16-D LEAP joint layout and
PyBullet index padding as Bidex_VisionPro_Teleop/avp_leapXela.py.
"""

from __future__ import annotations

import os

import pybullet as p
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

NUM_LEAP_JOINTS = 16

# LEAP sim index -> LeapXela revolute order (if_mcp, if_rot, ..., th_ipl).
_LEAP_INDEX_FOR_XELA = (
    1, 0, 2, 3,
    5, 4, 6, 7,
    9, 8, 10, 11,
    12, 13, 14, 15,
)

# Default publish order from leap_publisher when JointState.name is empty.
_PUBLISHER_JOINT_NAMES = (
    "1", "0", "2", "3",
    "5", "4", "6", "7",
    "9", "8", "10", "11",
    "12", "13", "14", "15",
)


def _decode_name(name) -> str:
    return name.decode("utf-8") if isinstance(name, bytes) else str(name)


def _urdf_dir() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "leapXela_right")


def _revolute_joint_indices(body_id: int) -> list[int]:
    indices: list[int] = []
    for joint_index in range(p.getNumJoints(body_id)):
        if p.getJointInfo(body_id, joint_index)[2] == p.JOINT_REVOLUTE:
            indices.append(joint_index)
    return indices


def _disable_body_collision(body_id: int) -> None:
    for link_idx in range(-1, p.getNumJoints(body_id)):
        p.setCollisionFilterGroupMask(body_id, link_idx, 0, 0)


def leap_jointstate_to_leap_q(msg: JointState) -> list[float] | None:
    """Parse JointState into 16-D LEAP sim joint vector (indices 0..15)."""
    if len(msg.position) < NUM_LEAP_JOINTS:
        return None

    if msg.name and len(msg.name) >= NUM_LEAP_JOINTS:
        try:
            leap_q = [0.0] * NUM_LEAP_JOINTS
            for name, pos in zip(msg.name[:NUM_LEAP_JOINTS], msg.position[:NUM_LEAP_JOINTS]):
                leap_q[int(str(name))] = float(pos)
            return leap_q
        except (ValueError, IndexError):
            pass

    by_name = dict(
        zip(_PUBLISHER_JOINT_NAMES, msg.position[:NUM_LEAP_JOINTS])
    )
    return [float(by_name[str(i)]) for i in range(NUM_LEAP_JOINTS)]


def leap_q_to_xela_positions(leap_q: list[float]) -> list[float]:
    return [float(leap_q[i]) for i in _LEAP_INDEX_FOR_XELA]


class LeapXelaSubscriberNode(Node):
    def __init__(self) -> None:
        super().__init__("leap_xela_subscriber")

        self.declare_parameter("joint_topic", "cmd_xela")
        self.declare_parameter("use_gui", True)
        self.declare_parameter("sim_hz", 240)

        joint_topic = str(self.get_parameter("joint_topic").value)
        use_gui = bool(self.get_parameter("use_gui").value)
        self._sim_hz = float(self.get_parameter("sim_hz").value)

        urdf_dir = _urdf_dir()
        urdf_path = os.path.join(urdf_dir, "hand.urdf")
        if not os.path.isfile(urdf_path):
            raise FileNotFoundError(f"URDF not found: {urdf_path}")

        self._cid = p.connect(p.GUI if use_gui else p.DIRECT)
        if self._cid < 0:
            raise RuntimeError("Failed to connect to PyBullet.")

        p.setAdditionalSearchPath(urdf_dir)
        assets_dir = os.path.join(urdf_dir, "assets")
        if os.path.isdir(assets_dir):
            p.setAdditionalSearchPath(assets_dir)

        p.resetDebugVisualizerCamera(
            cameraDistance=0.4,
            cameraYaw=50,
            cameraPitch=-20,
            cameraTargetPosition=[0.0, 0.0, 0.05],
        )
        p.setGravity(0, 0, 0)
        p.setRealTimeSimulation(0)

        self._body_id = p.loadURDF(
            urdf_path,
            [-0.12, 0.0, 0.01],
            p.getQuaternionFromEuler([1.57, 0, -1.57]),
            useFixedBase=True,
        )
        if self._body_id < 0:
            raise RuntimeError(f"Failed to load URDF: {urdf_path}")

        _disable_body_collision(self._body_id)
        self._joint_indices = _revolute_joint_indices(self._body_id)
        if len(self._joint_indices) != NUM_LEAP_JOINTS:
            raise RuntimeError(
                f"Expected {NUM_LEAP_JOINTS} revolute joints, got {len(self._joint_indices)}"
            )

        self._latest_xela_q: list[float] | None = None
        self.create_subscription(JointState, joint_topic, self._on_joint_cmd, 10)

        sim_period = 1.0 / max(self._sim_hz, 1.0)
        self.create_timer(sim_period, self._on_sim_tick)

        names = [
            _decode_name(p.getJointInfo(self._body_id, i)[1])
            for i in self._joint_indices
        ]
        self.get_logger().info(f"Loaded {urdf_path} (body id={self._body_id})")
        for idx, name in zip(self._joint_indices, names):
            self.get_logger().info(f"  revolute joint {idx}: {name}")
        self.get_logger().info(
            f"Subscribed to JointState '{joint_topic}' (sim {self._sim_hz:.0f} Hz)."
        )

    def _on_joint_cmd(self, msg: JointState) -> None:
        leap_q = leap_jointstate_to_leap_q(msg)
        if leap_q is None:
            self.get_logger().warn(
                f"JointState has {len(msg.position)} positions; expected {NUM_LEAP_JOINTS}."
            )
            return
        self._latest_xela_q = leap_q_to_xela_positions(leap_q)

    def _apply_joint_positions(self, positions: list[float]) -> None:
        for joint_index, target in zip(self._joint_indices, positions):
            p.resetJointState(self._body_id, joint_index, target)

    def _on_sim_tick(self) -> None:
        if not p.isConnected(self._cid):
            self.get_logger().warn("PyBullet disconnected; shutting down.")
            rclpy.shutdown()
            return
        if self._latest_xela_q is None:
            return
        self._apply_joint_positions(self._latest_xela_q)
        p.stepSimulation()

    def destroy_node(self) -> bool:
        try:
            if p.isConnected(self._cid):
                p.disconnect(self._cid)
        except Exception:
            pass
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = LeapXelaSubscriberNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
