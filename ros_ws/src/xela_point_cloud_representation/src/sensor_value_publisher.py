#!/usr/bin/env python3

import json
from pathlib import Path

import rclpy
from rclpy.node import Node
import numpy as np

from xela_point_cloud_representation.msg import Texel, HandSensors

from leap_taxel_map import (
    get_flatten_hand,
    get_sorted_1D_hand_taxels_map,
    sorted_1D_hand_taxel_name,
)

def generate_sensor_msg_from_local_array(local_data, sensor_names_1d):
    """
    local_data shape: (368, 3)
    local_data[idx] = [x, y, z]
    """

    local_data = np.asarray(local_data, dtype=np.float32)
    sensor_msg = HandSensors()
    for idx, sensor_name in enumerate(sensor_names_1d):
        texel = Texel()
        texel.sensor_name = sensor_name

        # Publish xyz
        texel.x = float(local_data[idx, 0])
        texel.y = float(local_data[idx, 1])
        texel.z = float(local_data[idx, 2])

        texel.taxel_id = idx
        texel.joint_x = sensor_name + "_slide_x"
        texel.joint_y = sensor_name + "_slide_y"
        texel.joint_z = sensor_name + "_slide_z"

        sensor_msg.texels.append(texel)

    return sensor_msg

def taxel_1d_sensor_names():
    map_path = Path(__file__).resolve().parent / "leap_sensor_taxel_map.json"
    with open(map_path, "r") as f:
        map_dict = json.load(f)

    hand_hw_flat, hand_sim_flat = get_flatten_hand(map_dict)
    map_ = get_sorted_1D_hand_taxels_map(hand_hw_flat, hand_sim_flat)
    sorted_sim = sorted_1D_hand_taxel_name(map_, hand_hw_flat)
    
    return sorted_sim

class SensorValuePublisher(Node):
    def __init__(self) -> None:
        super().__init__("sensor_value_publisher")

        self.scaled_data = np.load("scaled_taxel_data/scaled_data_01.npy")

        if self.scaled_data.shape[1:] != (368, 3):
            raise ValueError(
                f"Expected scaled_data shape (N, 368, 3), got {self.scaled_data.shape}"
            )

        self.frame_idx = 0

        self.publisher_ = self.create_publisher(
            HandSensors,
            "sensor_values",
            10
        )

        self.sensor_names_1d = taxel_1d_sensor_names()
        self.timer = self.create_timer(0.01, self.publish_sensor_values)

    def publish_sensor_values(self):
        frame_data = self.scaled_data[self.frame_idx]

        hand_sensors_msg = generate_sensor_msg_from_local_array(frame_data, self.sensor_names_1d)

        self.publisher_.publish(hand_sensors_msg)

        self.frame_idx = (self.frame_idx + 1) % self.scaled_data.shape[0]

def main(args=None) -> None:
    rclpy.init(args=args)
    node = SensorValuePublisher()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
