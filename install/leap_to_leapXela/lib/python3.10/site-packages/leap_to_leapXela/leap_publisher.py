#!/usr/bin/env python3
"""ROS 2 publisher: LEAP right-hand URDF in PyBullet with joint sliders.

Loads ``leap_description`` ``hand.urdf``, creates one PyBullet GUI slider per
revolute joint, updates the simulated hand as sliders move, and publishes joint
angles on ``leap_joint`` as ``sensor_msgs/JointState`` (joint names from URDF).
"""

from __future__ import annotations

import os

import pybullet as p
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


def _decode_name(name) -> str:
    return name.decode("utf-8") if isinstance(name, bytes) else str(name)


def _leap_description_urdf_dir() -> str:
    """Resolve leap_description/urdf (installed share or source tree)."""
    try:
        from ament_index_python.packages import get_package_share_directory

        share = get_package_share_directory("leap_description")
        urdf_dir = os.path.join(share, "urdf")
        if os.path.isfile(os.path.join(urdf_dir, "hand.urdf")):
            return urdf_dir
    except Exception:
        pass

    here = os.path.dirname(os.path.abspath(__file__))
    src_urdf = os.path.normpath(
        os.path.join(here, "..", "..", "leap_description", "urdf")
    )
    if os.path.isfile(os.path.join(src_urdf, "hand.urdf")):
        return src_urdf

    raise FileNotFoundError(
        "hand.urdf not found. Build/install leap_description or run from the workspace."
    )


def _setup_pybullet_search_paths(urdf_dir: str) -> None:
    p.setAdditionalSearchPath(urdf_dir)
    assets_dir = os.path.join(urdf_dir, "assets")
    if os.path.isdir(assets_dir):
        p.setAdditionalSearchPath(assets_dir)


def _slider_joints(body_id: int) -> list[tuple[int, str, float, float]]:
    """(joint_index, name, lower, upper) for revolute joints."""
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


class LeapPublisherNode(Node):
    def __init__(self) -> None:
        super().__init__("leap_publisher")

        self.declare_parameter("joint_topic", "leap_joint")
        self.declare_parameter("use_gui", True)
        self.declare_parameter("urdf_path", "")
        # Integer defaults so CLI overrides like -p publish_hz:=100 type-check.
        self.declare_parameter("sim_hz", 240)
        self.declare_parameter("publish_hz", 50)

        joint_topic = str(self.get_parameter("joint_topic").value)
        use_gui = bool(self.get_parameter("use_gui").value)
        urdf_path_param = str(self.get_parameter("urdf_path").value).strip()
        self._sim_hz = float(self.get_parameter("sim_hz").value)
        self._publish_hz = float(self.get_parameter("publish_hz").value)

        urdf_dir = _leap_description_urdf_dir()
        urdf_path = (
            os.path.abspath(urdf_path_param)
            if urdf_path_param
            else os.path.join(urdf_dir, "hand.urdf")
        )
        if not os.path.isfile(urdf_path):
            raise FileNotFoundError(f"URDF not found: {urdf_path}")
        urdf_dir = os.path.dirname(urdf_path)

        cid = p.connect(p.GUI if use_gui else p.DIRECT)
        if cid < 0:
            raise RuntimeError("Failed to connect to PyBullet.")

        self._cid = cid
        _setup_pybullet_search_paths(urdf_dir)
        p.resetDebugVisualizerCamera(
            cameraDistance=0.35,
            cameraYaw=55,
            cameraPitch=-25,
            cameraTargetPosition=[0.0, 0.0, 0.05],
        )
        p.setGravity(0, 0, 0)
        p.setRealTimeSimulation(0)

        self._body_id = p.loadURDF(
            urdf_path,
            basePosition=[-0.1, 0.01, 0.03],
            baseOrientation=p.getQuaternionFromEuler([1.57, 0, 3.14]),
            useFixedBase=True,
        )
        if self._body_id < 0:
            raise RuntimeError(f"Failed to load URDF: {urdf_path}")

        self._revolute = _slider_joints(self._body_id)
        self._joint_indices: list[int] = []
        self._joint_names: list[str] = []
        self._slider_ids: list[int] = []

        for joint_index, name, lower, upper in self._revolute:
            initial = 0.0 if lower <= 0.0 <= upper else 0.5 * (lower + upper)
            p.resetJointState(self._body_id, joint_index, initial)
            self._joint_indices.append(joint_index)
            self._joint_names.append(name)
            if use_gui:
                self._slider_ids.append(
                    p.addUserDebugParameter(name, lower, upper, initial)
                )

        self._pub = self.create_publisher(JointState, joint_topic, 10)
        self._joint_msg = JointState()
        self._joint_msg.name = list(self._joint_names)

        sim_period = 1.0 / max(self._sim_hz, 1.0)
        self.create_timer(sim_period, self._on_sim_tick)

        self._publish_on_sim_tick = (
            self._publish_hz <= 0.0
            or abs(self._publish_hz - self._sim_hz) < 1e-6
        )
        if self._publish_hz > 0.0 and not self._publish_on_sim_tick:
            self.create_timer(1.0 / self._publish_hz, self._publish_joint_state)

        self.get_logger().info(
            f"Loaded {urdf_path} (body id={self._body_id}, "
            f"{len(self._revolute)} revolute joints, gui={use_gui})"
        )
        for joint_index, name, lower, upper in self._revolute:
            self.get_logger().info(
                f"  joint {joint_index} ({name}): [{lower:.3f}, {upper:.3f}] rad"
            )
        self.get_logger().info(
            f"Publishing JointState on '{joint_topic}' "
            f"(sim {self._sim_hz:.0f} Hz, publish {self._publish_hz:.0f} Hz)."
        )

    def _read_joint_positions(self) -> list[float]:
        if self._slider_ids:
            return [
                float(p.readUserDebugParameter(slider_id))
                for slider_id in self._slider_ids
            ]
        return [
            float(p.getJointState(self._body_id, joint_index)[0])
            for joint_index in self._joint_indices
        ]

    def _apply_joint_positions(self, positions: list[float]) -> None:
        for joint_index, target in zip(self._joint_indices, positions):
            p.resetJointState(self._body_id, joint_index, target)

    def _publish_joint_state(self) -> None:
        self._joint_msg.header.stamp = self.get_clock().now().to_msg()
        self._joint_msg.position = self._read_joint_positions()
        self._pub.publish(self._joint_msg)

    def _on_sim_tick(self) -> None:
        if not p.isConnected(self._cid):
            self.get_logger().warn("PyBullet disconnected; shutting down.")
            rclpy.shutdown()
            return

        positions = self._read_joint_positions()
        self._apply_joint_positions(positions)
        p.stepSimulation()

        if self._publish_on_sim_tick:
            self._joint_msg.header.stamp = self.get_clock().now().to_msg()
            self._joint_msg.position = positions
            self._pub.publish(self._joint_msg)

    def destroy_node(self) -> bool:
        try:
            if p.isConnected(self._cid):
                p.disconnect(self._cid)
        except Exception:
            pass
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = LeapPublisherNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
