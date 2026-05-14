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


def _load_leap_xela_id():
    """Load LEAP_XELA_ID from the xela_data_collection sibling package.

    Tries the ROS Python path first (post-colcon-build), then falls back to
    loading the source file directly so this works without a full overlay.
    """
    import importlib.util
    import sys

    # Try the installed ROS path first.
    try:
        from xela_data_collection.leapXelaMap import LEAP_XELA_ID
        return LEAP_XELA_ID
    except ImportError:
        pass

    src_path = (
        Path(__file__).resolve().parents[3]
        / "lib"
        / "xela_data_collection"
        / "xela_data_collection"
        / "leapXelaMap.py"
    )
    spec = importlib.util.spec_from_file_location("leapXelaMap", src_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot find leapXelaMap at {src_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod.LEAP_XELA_ID


def _build_taxel_index(id_map):
    """Return (rows, cols, taxel_ids) arrays for the 368 active taxels."""
    id_arr = np.array(id_map, dtype=float)
    mask = id_arr != 6e6
    rows, cols = np.where(mask)
    taxel_ids = id_arr[mask].astype(int)
    return rows, cols, taxel_ids


def load_calibrated_from_h5(h5_path: Path, calib_dir: Path) -> np.ndarray:
    """Load every sample from *h5_path* and return calibrated taxel data.

    Returns
    -------
    np.ndarray
        Shape (N, 368, 3), float64.  Each value is the calibrated force
        displacement in sensor units after subtracting the resting offset
        and applying the asymmetric per-axis scale factor.
    """
    import h5py

    offset = np.load(str(calib_dir / "taxel_offset.npy"))      # (368, 3)
    scale_pos = np.load(str(calib_dir / "taxel_scale_pos.npy"))  # (368, 3)
    scale_neg = np.load(str(calib_dir / "taxel_scale_neg.npy"))  # (368, 3)

    rows, cols, taxel_ids = _build_taxel_index(_load_leap_xela_id())

    if not h5_path.exists():
        raise FileNotFoundError(f"h5 file not found: {h5_path.resolve()}")
        
    frames = []
    with h5py.File(str(h5_path), "r") as f:
        root_key = list(f.keys())[0]
        root_grp = f[root_key]
        for sample_key in sorted(root_grp.keys()):
            raw_data = root_grp[sample_key]["raw_image"][()]  # (26, 31, 3)
            # Non-squeeze EPs store int32 values mislabelled as float32 ("32FC3"),
            # so the bytes must be reinterpreted.  Squeeze stores genuine int32
            # ("32SC3") and can be used directly.
            if raw_data.dtype == np.float32:
                raw_i32 = raw_data.view(np.int32)
            else:
                raw_i32 = raw_data

            # Extract readings at active taxel positions then reorder by taxel id
            raw_at_positions = raw_i32[rows, cols, :]        # (368, 3) in mask order
            taxel_raw = np.zeros((368, 3), dtype=np.int32)
            taxel_raw[taxel_ids] = raw_at_positions          # indexed by taxel id

            delta = taxel_raw.astype(np.float64) - offset
            calibrated = np.where(delta >= 0, delta * scale_pos, delta * scale_neg)
            frames.append(calibrated)

    return np.stack(frames, axis=0)  # (N, 368, 3)


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

        self.declare_parameter("h5_path", "")
        self.declare_parameter(
            "calib_dir",
            str(Path(__file__).resolve().parents[4] / "data" / "pointcloud_calibration"),
        )

        h5_path_str = self.get_parameter("h5_path").get_parameter_value().string_value
        calib_dir = Path(
            self.get_parameter("calib_dir").get_parameter_value().string_value
        )

        if h5_path_str:
            self.get_logger().info(f"Loading calibrated data from h5: {h5_path_str}")
            self.scaled_data = load_calibrated_from_h5(Path(h5_path_str), calib_dir)
        else:
            self.get_logger().info("No h5_path given; loading pre-scaled npy fallback.")
            self.scaled_data = np.load(
                "./xela_point_cloud_representation/scaled_taxel_data/scaled_data_01.npy"
            )

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
