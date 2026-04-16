from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class HandPosePublisher(Node):
    def __init__(self) -> None:
        super().__init__('HandPosePublisher')

        self.declare_parameter('topic', '/chatter')
        self.declare_parameter('publish_rate_hz', 10.0)

        topic = str(self.get_parameter('topic').value)
        publish_rate_hz = float(self.get_parameter('publish_rate_hz').value)
        if publish_rate_hz <= 0.0:
            publish_rate_hz = 10.0

        self._pub = self.create_publisher(String, topic, 10)
        self._counter = 0

        self.create_timer(1.0 / publish_rate_hz, self._on_timer)
        self.get_logger().info(f'Publishing std_msgs/String on {topic}')

    def _on_timer(self) -> None:
        msg = String()
        msg.data = f'hello world {self._counter}'
        self._counter += 1
        self._pub.publish(msg)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = SimplePublisher()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

