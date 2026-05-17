#!/usr/bin/env python3

from pathlib import Path
from typing import Optional

import numpy as np

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from std_msgs.msg import String


class HandTouchPointCloudRecorder(Node):
    def __init__(self) -> None:
        super().__init__("hand_touch_point_cloud_recorder")

        self.pc_sub = self.create_subscription(
            PointCloud2,
            "hand_touch_point_cloud",
            self._on_point_cloud,
            10,
        )

        self.file_sub = self.create_subscription(
            String,
            "current_h5_file",
            self._on_current_file,
            10,
        )

        self.dump_root = Path("pointcloud_dump")
        self.dump_root.mkdir(parents=True, exist_ok=True)

        self.current_h5_path: Optional[Path] = None
        self.current_output_path: Optional[Path] = None
        self._dump_frames = []

        self._last_log_time_ns = 0

        self.get_logger().info("Point cloud recorder started.")

    def _output_path_from_h5(self, h5_path: Path) -> Path:
        parts = h5_path.parts

        if "ML_dataset" in parts:
            idx = parts.index("ML_dataset")
            relative = Path(*parts[idx + 1:])
        else:
            relative = Path(h5_path.name)

        output_relative = relative.with_name(f"{h5_path.stem}_point_cloud.npy")

        return self.dump_root / output_relative

    def _on_current_file(self, msg: String) -> None:
        new_h5_path = Path(msg.data)

        if self.current_h5_path is not None and new_h5_path != self.current_h5_path:
            self._save_current_file()

        self.current_h5_path = new_h5_path
        self.current_output_path = self._output_path_from_h5(new_h5_path)
        self.current_output_path.parent.mkdir(parents=True, exist_ok=True)

        self._dump_frames = []

        self.get_logger().info(
            f"Recording point clouds for: {self.current_h5_path.name}"
        )
        self.get_logger().info(
            f"Output path: {self.current_output_path}"
        )

    def _on_point_cloud(self, msg: PointCloud2) -> None:
        pts = point_cloud2.read_points(
            msg,
            field_names=("x", "y", "z"),
            skip_nans=True,
        )

        xyz = np.fromiter(
            (coord for point in pts for coord in point),
            dtype=np.float32,
        ).reshape(-1, 3)

        self._dump_frames.append(xyz.copy())

        now_ns = self.get_clock().now().nanoseconds
        if now_ns - self._last_log_time_ns > int(1.0e9):
            self._last_log_time_ns = now_ns

            if xyz.size == 0:
                self.get_logger().warn("Received empty point cloud.")
            else:
                self.get_logger().info(
                    f"Received {xyz.shape[0]} points. "
                    f"Buffered frames={len(self._dump_frames)}"
                )

    def _save_current_file(self) -> None:
        if self.current_output_path is None:
            self.get_logger().warn("No output path set. Skipping save.")
            return

        if len(self._dump_frames) == 0:
            self.get_logger().warn(
                f"No frames recorded for {self.current_h5_path}. Skipping save."
            )
            return

        np.save(
            self.current_output_path,
            np.array(self._dump_frames, dtype=object),
            allow_pickle=True,
        )

        self.get_logger().info(
            f"Saved {len(self._dump_frames)} frames to {self.current_output_path}"
        )

    def destroy_node(self) -> bool:
        self._save_current_file()
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)

    node = HandTouchPointCloudRecorder()

    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()