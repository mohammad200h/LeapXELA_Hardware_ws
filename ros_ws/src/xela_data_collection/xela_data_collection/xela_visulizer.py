#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

from xela_server_ros2.msg import SensStream


class XelaServTopicSubscriber(Node):
    def __init__(self) -> None:
        super().__init__("xela_servtopic_subscriber")
        self._sub = self.create_subscription(
            SensStream,
            "/xServTopic",
            self._on_stream,
            10,
        )

    def _on_stream(self, msg: SensStream) -> None:
        sensor_ids = [int(s.sensor_pos) for s in msg.sensors]
        times = [float(s.time) for s in msg.sensors]
        texel_counts = [len(s.taxels) for s in msg.sensors]

        self.get_logger().info(
            f"rx /xServTopic sensors={sensor_ids} "
            f"times={times} texels={texel_counts}"
        )
        self.get_logger().info(f"\n\nsensor::18 {msg.sensors[-1]}\n\n")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = XelaServTopicSubscriber()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

