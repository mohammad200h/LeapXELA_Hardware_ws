#!/usr/bin/env python3
"""ROS 2 publisher: subscribe to NI-DAQ force sensor WebSocket and publish on topic nano17."""

from __future__ import annotations

import asyncio
import json
import threading

import rclpy
from geometry_msgs.msg import WrenchStamped
from rclpy.node import Node
from websockets import connect


class ForcePublisherNode(Node):
    def __init__(self) -> None:
        super().__init__('force_publisher')

        self.declare_parameter('host', '192.168.2.59')
        self.declare_parameter('port', 8765)
        self.declare_parameter('topic', 'nano17')
        self.declare_parameter('frame_id', 'nano17')

        host = self.get_parameter('host').get_parameter_value().string_value
        port = self.get_parameter('port').get_parameter_value().integer_value
        topic = self.get_parameter('topic').get_parameter_value().string_value
        self._frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        self._uri = f'ws://{host}:{port}'

        self._publisher = self.create_publisher(WrenchStamped, topic, 10)
        self._publish_lock = threading.Lock()
        self.get_logger().info(f'Publishing force data on /{topic} from {self._uri}')

    def publish_sample(self, timestamp_s: float, fx: float, fy: float, fz: float, tx: float, ty: float, tz: float) -> None:
        msg = WrenchStamped()
        msg.header.stamp.sec = int(timestamp_s)
        msg.header.stamp.nanosec = int(round((timestamp_s - msg.header.stamp.sec) * 1e9))
        msg.header.frame_id = self._frame_id
        msg.wrench.force.x = fx
        msg.wrench.force.y = fy
        msg.wrench.force.z = fz
        msg.wrench.torque.x = tx
        msg.wrench.torque.y = ty
        msg.wrench.torque.z = tz

        with self._publish_lock:
            self._publisher.publish(msg)

    async def websocket_loop(self) -> None:
        while rclpy.ok():
            try:
                self.get_logger().info(f'Connecting to {self._uri} ...')
                async with connect(self._uri) as websocket:
                    self.get_logger().info(f'Connected to {self._uri}')
                    async for message in websocket:
                        if not rclpy.ok():
                            return

                        data = json.loads(message)
                        for timestamp_s, fx, fy, fz, tx, ty, tz in zip(
                            data['timestamp_s'],
                            data['Fx'],
                            data['Fy'],
                            data['Fz'],
                            data['Tx'],
                            data['Ty'],
                            data['Tz'],
                        ):
                            self.publish_sample(timestamp_s, fx, fy, fz, tx, ty, tz)
            except asyncio.CancelledError:
                return
            except Exception as exc:
                self.get_logger().warn(
                    f'WebSocket disconnected: {exc}. Reconnecting in 2s ...'
                )
                await asyncio.sleep(2.0)


def _run_websocket(node: ForcePublisherNode) -> None:
    asyncio.run(node.websocket_loop())


def main() -> None:
    rclpy.init()
    node = ForcePublisherNode()
    ws_thread = threading.Thread(target=_run_websocket, args=(node,), daemon=True)
    ws_thread.start()

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()
        ws_thread.join(timeout=1.0)


if __name__ == '__main__':
    main()
