#!/usr/bin/env python3

import json
from pathlib import Path

import rclpy
from rclpy.node import Node
import numpy as np
import h5py

from sensor_msgs.msg import JointState
from xela_point_cloud_representation.msg import Texel, HandSensors

from leap_taxel_map import (
    get_flatten_hand,
    get_sorted_1D_hand_taxels_map,
    sorted_1D_hand_taxel_name,
)

def load_calibrated_from_npy(npy_path: Path):
    data = np.load(npy_path)
    return np.asarray(data, dtype=np.float32)


def _decode_h5_string_array(raw_data):
    return [
        x.decode("utf-8") if isinstance(x, bytes) else str(x)
        for x in np.asarray(raw_data).ravel()
    ]


def load_joint_states_from_h5(h5_path: Path):
    """Load joint state names and positions from *h5_path*.

    The HDF5 layout is expected to contain frame groups under the top-level
    stream, and within each frame a `state` group with `name` and `position`.
    """

    if not h5_path.exists():
        raise FileNotFoundError(f"h5 file not found: {h5_path.resolve()}")

    joint_frames = []
    with h5py.File(str(h5_path), "r") as f:
        root_key = list(f.keys())[0]
        root_grp = f[root_key]

        sample_keys = sorted(
            root_grp.keys(),
            key=lambda x: (0, int(x)) if x.isdigit() else (1, x),
        )

        for sample_key in sample_keys:
            try:
                sample = root_grp[sample_key]
                if "state" not in sample:
                    joint_frames.append(([], []))
                    continue

                state = sample["state"]
                if "name" not in state or "position" not in state:
                    joint_frames.append(([], []))
                    continue

                names = _decode_h5_string_array(state["name"][()])
                positions = np.asarray(state["position"][()], dtype=np.float64).ravel()
                if len(positions) != len(names):
                    joint_frames.append(([], []))
                    continue

                joint_frames.append((names, positions.tolist()))

            except Exception as e:
                joint_frames.append(([], []))   
    return joint_frames


def generate_sensor_msg(local_data, sensor_names_1d):
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
        self.declare_parameter("h5_path", "")
        self.declare_parameter("scaled_root", "interim")

        h5_path_str = self.get_parameter("h5_path").value
        if not h5_path_str:
            raise ValueError("Please provide h5_path")
        scaled_root = self.get_parameter("scaled_root").value

        h5_path = Path(h5_path_str)

        dataset_type = h5_path.parent.name
        stem = h5_path.stem

        project_root = h5_path.parents[2]
        scaled_path = project_root / "interim" / dataset_type / f"{stem}_scaled.npy"

        self.scaled_data = load_calibrated_from_npy(scaled_path)
        self.joint_frames = load_joint_states_from_h5(h5_path)

        self.frame_idx = 0

        self.sensor_publisher_ = self.create_publisher(
            HandSensors,
            "sensor_values",
            10,
        )
        self.joint_publisher_ = self.create_publisher(
            JointState,
            "xela_joint_publisher",
            10,
        )

        self.sensor_names_1d = taxel_1d_sensor_names()
        self.timer = self.create_timer(0.01, self.publish_sensor_values)
    
    def publish_sensor_values(self):
        if self.scaled_data.shape[0] == 0:
            return
        frame_data = self.scaled_data[self.frame_idx]

        hand_sensors_msg = generate_sensor_msg(frame_data, self.sensor_names_1d)
        self.sensor_publisher_.publish(hand_sensors_msg)

        if self.joint_frames:
            joint_names, joint_positions = self.joint_frames[self.frame_idx % len(self.joint_frames)]
            joint_msg = JointState()
            joint_msg.header.stamp = self.get_clock().now().to_msg()
            joint_msg.name = list(joint_names)
            joint_msg.position = [float(x) for x in joint_positions]
            self.joint_publisher_.publish(joint_msg)

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
