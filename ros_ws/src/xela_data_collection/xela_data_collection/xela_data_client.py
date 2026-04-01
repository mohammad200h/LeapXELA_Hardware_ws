#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

from xela_server_ros2.srv import XelaSensorStream
from xela_server_ros2.msg import SensStream

import numpy as np


class XelaSimpleClient(Node):
    def __init__(self):
        super().__init__("xela_simple_client")
        self.cli = self.create_client(XelaSensorStream, "xServStream")
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info("service xServStream not available, waiting...")

        # Sub
        self.sub = self.create_subscription(SensStream, "/xServTopic", self.on_xela_sensor_stream, 10)


    def make_request(self, sensor_id: int = 0):
        req = XelaSensorStream.Request()
        # sensor == 0 means "all sensors" per server implementation
        req.sensor = sensor_id

        future = self.cli.call_async(req)
        rclpy.spin_until_future_complete(self, future)

        if future.result() is not None:
            return future.result()
        else:
            raise RuntimeError(f"Service call failed: {future.exception()}")
    
    def on_xela_sensor_stream(self, msg: SensStream):
        avialable_sensors = []
        times = []
        # for sensor in msg.sensors:
        #     avialable_sensors.append(sensor.sensor_pos)
        #     times.append(sensor.time)
        # self.get_logger().info(f"avialable_sensors {avialable_sensors}")
        # self.get_logger().info(f"times {times}")
        number_of_texels_in_sensor_1 = len(msg.sensors[0].taxels)
        self.get_logger().info(f"number_of_texels_in_sensor_1 {number_of_texels_in_sensor_1}")
        self.get_logger().info(f"number_of_forces_in_sensor_1 {len(msg.sensors[0].forces)}")

        self.get_logger().info(f"taxels::1::x {msg.sensors[0].taxels[29]}")

        


def main(args=None):
    rclpy.init(args=args)

    node = XelaSimpleClient()
    try:
        # Simple example: request all sensors (sensor=0) and print the result
        response = node.make_request(sensor_id=1)
        node.get_logger().info(f"Got {len(response.data)} sensor readings from xServStream")
        print(response)
        # Keep the node alive to receive subscription callbacks until Ctrl+C
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()


