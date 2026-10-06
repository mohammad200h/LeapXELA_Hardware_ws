#!/usr/bin/env python3
"""Record the data collection topics into a rosbag2 bag.

Messages are subscribed in serialized form and written to the bag as-is, so
no post-processing happens here.

Records:
  - sensor_msgs/Image on ``/camera/color/image_raw`` (realsense_ros2_camera)
  - sensor_msgs/JointState on ``/cmd_xela`` (convert_sim_to_hardware)
  - sensor_msgs/JointState on ``/leap_state`` (leaphand_node)
  - sensor_msgs/JointState on ``/leap_state_sim`` (convert_hardware_to_sim)
  - xela_server_ros2/SensStream on ``/xServTopic`` (xela_service)
"""

from __future__ import annotations

import os
from datetime import datetime

import rclpy
import rosbag2_py
from rclpy.node import Node
from rclpy.qos import QoSProfile, qos_profile_sensor_data
from rosidl_runtime_py.utilities import get_message

from mechanical_pen_data_collection.bag_data import default_bag_dir

TOPICS = {
    "/camera/color/image_raw": "sensor_msgs/msg/Image",
    "/cmd_xela": "sensor_msgs/msg/JointState",
    "/leap_state": "sensor_msgs/msg/JointState",
    "/leap_state_sim": "sensor_msgs/msg/JointState",
    "/xServTopic": "xela_server_ros2/msg/SensStream",
}

# Best effort so the subscription matches both reliable and best-effort camera publishers.
SENSOR_DATA_TOPICS = {"/camera/color/image_raw"}


class RosbagRecorder(Node):
    """Subscribe to every topic in ``TOPICS`` and write each message to one bag."""

    def __init__(self) -> None:
        super().__init__("rosbag_recorder")

        bag_dir = self.declare_parameter("bag_dir", "").value or default_bag_dir()
        bag_name = self.declare_parameter("bag_name", "").value
        storage_id = self.declare_parameter("storage_id", "sqlite3").value

        if not bag_name:
            bag_name = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        bag_dir = os.path.expanduser(bag_dir)
        os.makedirs(bag_dir, exist_ok=True)
        self._uri = os.path.join(bag_dir, bag_name)

        self._writer = rosbag2_py.SequentialWriter()
        self._writer.open(
            rosbag2_py.StorageOptions(uri=self._uri, storage_id=storage_id),
            rosbag2_py.ConverterOptions(
                input_serialization_format="cdr", output_serialization_format="cdr"
            ),
        )

        self._counts = {topic: 0 for topic in TOPICS}
        for topic, msg_type in TOPICS.items():
            self._writer.create_topic(
                rosbag2_py.TopicMetadata(
                    name=topic, type=msg_type, serialization_format="cdr"
                )
            )
            qos = qos_profile_sensor_data if topic in SENSOR_DATA_TOPICS else QoSProfile(depth=10)
            self.create_subscription(
                get_message(msg_type),
                topic,
                lambda data, topic=topic: self._on_msg(topic, data),
                qos,
                raw=True,
            )

        self.create_timer(5.0, self._log_counts)
        self.get_logger().info(f"Recording {list(TOPICS)} to '{self._uri}'")

    def _on_msg(self, topic: str, data: bytes) -> None:
        self._writer.write(topic, data, self.get_clock().now().nanoseconds)
        self._counts[topic] += 1

    def _log_counts(self) -> None:
        summary = ", ".join(f"{topic}: {n}" for topic, n in self._counts.items())
        self.get_logger().info(f"Recorded messages - {summary}")
        silent = [topic for topic, n in self._counts.items() if n == 0]
        if silent:
            self.get_logger().warn(f"No messages received yet on {silent}")

    def close(self) -> None:
        self._writer.close()
        self.get_logger().info(f"Bag closed: '{self._uri}'")


def main(args=None):
    rclpy.init(args=args)
    node = RosbagRecorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
