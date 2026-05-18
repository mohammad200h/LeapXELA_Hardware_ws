#!/usr/bin/env python3

import json
from pathlib import Path
from typing import List, Tuple

import h5py
import numpy as np
import rclpy
from rclpy.node import Node

from std_msgs.msg import String, Bool
from sensor_msgs.msg import JointState
from xela_point_cloud_representation.msg import Texel, HandSensors

from leap_taxel_map import (
    get_flatten_hand,
    get_sorted_1D_hand_taxels_map,
    sorted_1D_hand_taxel_name,
)


JOINT_MAP = {
    "joint_4": "if_mcp",
    "joint_5": "if_rot",
    "joint_6": "if_pip",
    "joint_7": "if_dip",

    "joint_8": "mf_mcp",
    "joint_9": "mf_rot",
    "joint_10": "mf_pip",
    "joint_11": "mf_dip",

    "joint_12": "rf_mcp",
    "joint_13": "rf_rot",
    "joint_14": "rf_pip",
    "joint_15": "rf_dip",

    "joint_0": "th_cmc",
    "joint_1": "th_axl",
    "joint_2": "th_mcp",
    "joint_3": "th_ipl",
}

FLAT_OFFSET = {
    "joint_0": 3.14159274,
    "joint_1": 1.60147595,
    "joint_2": 3.14159274,
    "joint_3": 1.68431091,

    "joint_4": 4.76909262,
    "joint_5": 3.14159274,
    "joint_6": 3.12321721,
    "joint_7": 3.13224351,

    "joint_8": 4.75687456,
    "joint_9": 3.14159274,
    "joint_10": 3.08636928,
    "joint_11": 3.14772868,

    "joint_12": 4.77683252,
    "joint_13": 3.14159274,
    "joint_14": 3.09710717,
    "joint_15": 3.12165093,
}


SIGN = {
    "joint_0": 1.0,
    "joint_1": 1.0,
    "joint_2": 1.0,
    "joint_3": -1.0,

    "joint_4": -1.0,
    "joint_5": 1.0,
    "joint_6": 1.0,
    "joint_7": -1.0,

    "joint_8": -1.0,
    "joint_9": 1.0,
    "joint_10": 1.0,
    "joint_11": -1.0,

    "joint_12": -1.0,
    "joint_13": 1.0,
    "joint_14": 1.0,
    "joint_15": -1.0,
}

def motor_rad_to_mujoco_qpos(raw_name, raw_pos):
    q_rel = float(raw_pos) - FLAT_OFFSET[raw_name]
    return SIGN[raw_name] * q_rel

def load_calibrated_from_npy(npy_path: Path):
    data = np.load(npy_path)
    return np.asarray(data, dtype=np.float32)


def _decode_h5_string_array(raw_data):
    return [
        x.decode("utf-8") if isinstance(x, bytes) else str(x)
        for x in np.asarray(raw_data).ravel()
    ]


def load_joint_states_from_h5(h5_path: Path):
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

                raw_names = _decode_h5_string_array(state["name"][()])
                raw_positions = np.asarray(state["position"][()], dtype=np.float64).ravel()

                if len(raw_positions) != len(raw_names):
                    joint_frames.append(([], []))
                    continue
                
                mapped_names = []
                mapped_positions = []

                for name, pos in zip(raw_names, raw_positions):
                    if name in JOINT_MAP:
                        mapped_names.append(JOINT_MAP[name])
                        mapped_positions.append(motor_rad_to_mujoco_qpos(name, pos))
                    else:
                        print(f"[WARN] No MuJoCo mapping for joint name: {name}")

                joint_frames.append((mapped_names, mapped_positions))

            except Exception:
                joint_frames.append(([], []))

    return joint_frames


def generate_sensor_msg(local_data, sensor_names_1d):
    local_data = np.asarray(local_data, dtype=np.float32)

    if local_data.shape[0] != len(sensor_names_1d):
        raise ValueError(
            f"Taxel count mismatch: data has {local_data.shape[0]}, "
            f"sensor map has {len(sensor_names_1d)}"
        )

    sensor_msg = HandSensors()

    for idx, sensor_name in enumerate(sensor_names_1d):
        texel = Texel()
        texel.sensor_name = sensor_name

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
    return sorted_1D_hand_taxel_name(map_, hand_hw_flat)


class SensorValuePublisher(Node):
    def __init__(self) -> None:
        super().__init__("sensor_value_publisher")
        self.recorder_ready = False

        self.declare_parameter(
            "dataset_root",
            str(
                Path(__file__).resolve().parent
                / "pointcloud_calibration"
                / "ML_dataset"
            ),
        )
        self.declare_parameter("scaled_root", "interim")
        self.declare_parameter("publish_period", 0.01)

        self.dataset_root = Path(self.get_parameter("dataset_root").value)
        self.scaled_root = str(self.get_parameter("scaled_root").value)
        self.publish_period = float(self.get_parameter("publish_period").value)

        if not self.dataset_root.exists():
            raise FileNotFoundError(
                f"dataset_root not found: {self.dataset_root.resolve()}"
            )

        # dataset_root: pointcloud_calibration/ML_dataset
        # project_root: pointcloud_calibration
        self.project_root = self.dataset_root.parent

        # Expected:
        # pointcloud_calibration/ML_dataset/contour/<dataset_type>/*.h5
        self.h5_files = sorted(self.dataset_root.rglob("*.h5"))

        if len(self.h5_files) == 0:
            raise FileNotFoundError(
                f"No .h5 files found under: {self.dataset_root / 'contour'}"
            )

        self.sensor_names_1d = taxel_1d_sensor_names()

        self.skipped_files: List[Tuple[str, str]] = []
        self.current_file_idx = 0
        self.frame_idx = 0

        self.current_h5_path = None
        self.scaled_data = None
        self.joint_frames = []

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

        self.current_file_pub_ = self.create_publisher(
            String,
            "current_h5_file",
            10,
        )

        self.ready_sub = self.create_subscription(
            Bool,
            "recorder_ready",
            self.on_recorder_ready,
            1,
        )

        self.get_logger().info(
            f"Found {len(self.h5_files)} h5 files under {self.dataset_root / 'contour'}"
        )

        # if not self.load_next_valid_file():
        #     self.log_skipped_files()
        #     raise RuntimeError("No valid h5/scaled npy pairs found.")

        self.timer = None
        self.get_logger().info("Waiting for recorder_ready...")

        # self.timer = self.create_timer(
        #     self.publish_period,
        #     self.publish_sensor_values,
        # )

    def on_recorder_ready(self, msg: Bool):
        if not msg.data or self.recorder_ready:
            return
    
        self.recorder_ready = True
    
        self.get_logger().info("Recorder ready. Loading first file.")
    
        if not self.load_next_valid_file():
            self.log_skipped_files()
            raise RuntimeError("No valid h5/scaled npy pairs found.")
    
        self.get_logger().info("Starting publishing.")
    
        self.timer = self.create_timer(
            self.publish_period,
            self.publish_sensor_values,
        )
    
    def scaled_path_for_h5(self, h5_path: Path) -> Path:
        # h5:
        # pointcloud_calibration/ML_dataset/contour/<dataset_type>/<stem>.h5
        #
        # scaled:
        # pointcloud_calibration/interim/contour/<dataset_type>/<stem>_scaled.npy

        relative = h5_path.relative_to(self.dataset_root)
        scaled_relative = relative.with_name(f"{h5_path.stem}_scaled.npy")

        return self.project_root / self.scaled_root / scaled_relative

    def load_next_valid_file(self) -> bool:
        while self.current_file_idx < len(self.h5_files):
            h5_path = self.h5_files[self.current_file_idx]
            scaled_path = self.scaled_path_for_h5(h5_path)

            try:
                if not scaled_path.exists():
                    raise FileNotFoundError(
                        f"scaled npy not found: {scaled_path.resolve()}"
                    )

                scaled_data = load_calibrated_from_npy(scaled_path)

                if scaled_data.ndim != 3 or scaled_data.shape[2] != 3:
                    raise ValueError(
                        f"Expected scaled data shape (frames, taxels, 3), "
                        f"got {scaled_data.shape}"
                    )

                if scaled_data.shape[0] == 0:
                    raise ValueError("scaled data has 0 frames")

                if scaled_data.shape[1] != len(self.sensor_names_1d):
                    raise ValueError(
                        f"Taxel count mismatch: scaled data has "
                        f"{scaled_data.shape[1]}, sensor map has "
                        f"{len(self.sensor_names_1d)}"
                    )

                joint_frames = load_joint_states_from_h5(h5_path)

                self.current_h5_path = h5_path
                self.scaled_data = scaled_data
                self.joint_frames = joint_frames
                self.frame_idx = 0

                msg = String()
                msg.data = str(self.current_h5_path)
                self.current_file_pub_.publish(msg)

                self.get_logger().info(
                    f"Loaded file {self.current_file_idx + 1}/"
                    f"{len(self.h5_files)}: {h5_path.name}, "
                    f"frames={self.scaled_data.shape[0]}, "
                    f"taxels={self.scaled_data.shape[1]}"
                )

                return True

            except Exception as e:
                self.skipped_files.append((str(h5_path), str(e)))
                self.get_logger().warn(
                    f"Skipping file: {h5_path.name}. Reason: {e}"
                )
                self.current_file_idx += 1

        return False

    def publish_sensor_values(self):
        if self.scaled_data is None or self.scaled_data.shape[0] == 0:
            return

        frame_data = self.scaled_data[self.frame_idx]

        try:
            hand_sensors_msg = generate_sensor_msg(
                frame_data,
                self.sensor_names_1d,
            )
        except Exception as e:
            self.skipped_files.append(
                (
                    str(self.current_h5_path),
                    f"Failed at frame {self.frame_idx}: {e}",
                )
            )
            self.get_logger().warn(
                f"Skipping remaining frames of {self.current_h5_path.name}: {e}"
            )

            self.current_file_idx += 1
            if not self.load_next_valid_file():
                self.finish()
            return

        self.sensor_publisher_.publish(hand_sensors_msg)

        if self.joint_frames:
            joint_names, joint_positions = self.joint_frames[
                self.frame_idx % len(self.joint_frames)
            ]

            joint_msg = JointState()
            joint_msg.header.stamp = self.get_clock().now().to_msg()
            joint_msg.name = list(joint_names)
            joint_msg.position = [float(x) for x in joint_positions]

            self.joint_publisher_.publish(joint_msg)

        self.frame_idx += 1

        if self.frame_idx >= self.scaled_data.shape[0]:
            self.get_logger().info(
                f"Finished file: {self.current_h5_path.name}"
            )

            self.current_file_idx += 1

            if not self.load_next_valid_file():
                self.finish()

    def log_skipped_files(self):
        if not self.skipped_files:
            self.get_logger().info("No files were skipped.")
            return

        self.get_logger().warn(
            f"Skipped {len(self.skipped_files)} files:"
        )

        for path, reason in self.skipped_files:
            self.get_logger().warn(f"  {path} | {reason}")

    def finish(self):
        self.get_logger().info("Finished publishing all valid files.")
        self.log_skipped_files()
        rclpy.shutdown()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SensorValuePublisher()

    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()