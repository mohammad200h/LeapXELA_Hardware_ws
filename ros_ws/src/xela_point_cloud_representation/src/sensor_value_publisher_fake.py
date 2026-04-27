#!/usr/bin/env python3

import json

import rclpy
from rclpy.node import Node
from perlin_noise import PerlinNoise
import numpy as np
from ament_index_python.packages import get_package_share_directory

from xela_point_cloud_representation.msg import Sensor, Texel

def generate_perlin_noise(dim = (4,6)):
    """
    Generate a 2D Perlin noise field with shape (height, width).

    The `perlin_noise` library expects coordinates (float or iterable of floats),
    so we sample a regular grid in [0, 1]x[0, 1].
    """
    height, width = dim
    noise = PerlinNoise(octaves=6, seed=42)
    field = np.zeros((height, width), dtype=float)
    for y in range(height):
        for x in range(width):
            field[y, x] = noise([x / max(1, width - 1), y / max(1, height - 1)])
    return field


def generate_sensor_msg_for_uspa46(sensor_joints, sensor_name):
    sensor_msg = Sensor()
    sensor_msg.name = sensor_name
    sensor_locations = sensor_joints[sensor_name]
    noise = generate_perlin_noise(dim=(4,6))
    for y in range(4):
        for x in range(6):
            texel = Texel()
            texel.loc = str(x)+"_"+str(y)
            texel.x = 0
            texel.y = 0
            texel.z = noise[y, x]
            texel.joint_x = sensor_locations[str(x)+"_"+str(y)]["x"]
            texel.joint_y = sensor_locations[str(x)+"_"+str(y)]["y"]
            texel.joint_z = sensor_locations[str(x)+"_"+str(y)]["z"]
            sensor_msg.texels.append(texel)
    return sensor_msg

def generate_sensor_msg_for_uspa44(sensor_joints, sensor_name):
    sensor_msg = Sensor()
    sensor_msg.name = sensor_name
    sensor_locations = sensor_joints[sensor_name]
    noise = generate_perlin_noise(dim=(4,6))
    for y in range(4):
        for x in range(4):
            texel = Texel()
            texel.loc = str(x)+"_"+str(y)
            texel.x = 0
            texel.y = 0
            texel.z = noise[y, x]
            texel.joint_x = sensor_locations[str(x)+"_"+str(y)]["x"]
            texel.joint_y = sensor_locations[str(x)+"_"+str(y)]["y"]
            texel.joint_z = sensor_locations[str(x)+"_"+str(y)]["z"]
            sensor_msg.texels.append(texel)
    return sensor_msg

class SensorValuePublisherFake(Node):
    def __init__(self) -> None:
        super().__init__("sensor_value_publisher_fake")
        self.declare_parameter("sensor_joints_path", "")
        self.sensor_joints = self.load_sensor_joints()

        self.publisher_ = self.create_publisher(Sensor, "fake_sensor_values", 10)

        self.timer = self.create_timer(1.0, self.publish_sensor_values)

    def load_sensor_joints(self):
        sensor_joints_path = self.get_parameter("sensor_joints_path").get_parameter_value().string_value
        if not sensor_joints_path:
            sensor_joints_path = (
                get_package_share_directory("xela_description")
                + "/mjcf/sensor_joints.json"
            )

        with open(sensor_joints_path, "r") as f:
            return json.load(f)

    def publish_sensor_values(self):
        sensor_msg = generate_sensor_msg_for_uspa46(self.sensor_joints, "if_bs_uspa46")
        self.publisher_.publish(sensor_msg)
        sensor_msg = generate_sensor_msg_for_uspa44(self.sensor_joints, "if_bs_uspa44")
        # TODO add reset of the sensors
        self.publisher_.publish(sensor_msg)
def main(args=None) -> None:
    rclpy.init(args=args)
    node = SensorValuePublisherFake()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
