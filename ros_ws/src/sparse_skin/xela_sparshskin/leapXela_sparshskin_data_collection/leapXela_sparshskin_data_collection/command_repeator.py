#!/usr/bin/env python3
"""Republish the latest JointState command at a fixed rate.

Subscribes to motion commands (default: repeator_joint_commands) and keeps
publishing the last received message to the teleop/hardware command topic
(default: oculus_teleop_joint_commands). When a new command arrives, it
replaces the held message immediately.
"""

from __future__ import annotations

import copy
from threading import Lock

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class CommandRepeator(Node):
    """Hold and republish the latest joint command."""

    def __init__(self) -> None:
        super().__init__("command_repeator")

        self.declare_parameter("input_topic", "repeator_joint_commands")
        self.declare_parameter("joint_topic", "oculus_teleop_joint_commands")
        self.declare_parameter("publish_rate_hz", 30.0)

        input_topic = self.get_parameter("input_topic").get_parameter_value().string_value
        joint_topic = self.get_parameter("joint_topic").get_parameter_value().string_value
        publish_rate_hz = self.get_parameter("publish_rate_hz").get_parameter_value().double_value
        if publish_rate_hz <= 0.0:
            publish_rate_hz = 30.0

        self._lock = Lock()
        self._last_command: JointState | None = None

        self._publisher = self.create_publisher(JointState, joint_topic, 10)
        self.create_subscription(JointState, input_topic, self._on_command, 10)
        self.create_timer(1.0 / publish_rate_hz, self._publish_last)

        self.get_logger().info(
            f"Command repeator ready (in: {input_topic}, out: {joint_topic}, "
            f"rate: {publish_rate_hz} Hz)"
        )

    def _on_command(self, msg: JointState) -> None:
        with self._lock:
            self._last_command = copy.deepcopy(msg)

    def _publish_last(self) -> None:
        with self._lock:
            if self._last_command is None:
                return
            msg = copy.deepcopy(self._last_command)

        msg.header.stamp = self.get_clock().now().to_msg()
        self._publisher.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = CommandRepeator()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
