#!/usr/bin/env python3

import csv
from pathlib import Path

import numpy as np
import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from sensor_msgs.msg import JointState
from leap_globals import (
    COMMAND_QUEUE_DEPTH,
    COMMAND_TOPIC,
    POSITION_NODE_DEFAULT_CSV_FILENAME,
    POSITION_NODE_DEFAULT_CSV_PATH,
    POSITION_NODE_DEFAULT_INTERPOLATION_STEPS,
    POSITION_NODE_DEFAULT_PUBLISH_PERIOD_SEC,
    POSITION_NODE_DEFAULT_SAMPLE_STRIDE,
    POSITION_NODE_DEFAULT_SOURCE_UNITS,
)


class PositionNode(Node):
    def __init__(self):
        super().__init__("position_node")

        self.declare_parameter("csv_path", POSITION_NODE_DEFAULT_CSV_PATH)
        self.declare_parameter("source_units", POSITION_NODE_DEFAULT_SOURCE_UNITS)
        self.declare_parameter("sample_stride", POSITION_NODE_DEFAULT_SAMPLE_STRIDE)
        self.declare_parameter("interpolation_steps", POSITION_NODE_DEFAULT_INTERPOLATION_STEPS)
        self.declare_parameter("publish_period_sec", POSITION_NODE_DEFAULT_PUBLISH_PERIOD_SEC)

        self.pub = self.create_publisher(JointState, COMMAND_TOPIC, COMMAND_QUEUE_DEPTH)

        csv_path = self._resolve_csv_path(str(self.get_parameter("csv_path").value).strip())
        source_units = str(self.get_parameter("source_units").value).strip().lower()
        sample_stride = max(1, int(self.get_parameter("sample_stride").value))
        interpolation_steps = max(1, int(self.get_parameter("interpolation_steps").value))
        publish_period_sec = float(self.get_parameter("publish_period_sec").value)
        if publish_period_sec <= 0.0:
            raise ValueError("publish_period_sec must be > 0.")

        self.joint_positions_deg = self.load_csv(csv_path, source_units=source_units)
        self.command_sequence = self.build_command_sequence(
            self.joint_positions_deg,
            sample_stride=sample_stride,
            interpolation_steps=interpolation_steps,
        )

        self._next_index = 0
        self._started = False
        self._timer = self.create_timer(publish_period_sec, self._on_timer)

        self.get_logger().info(
            f"Loaded {len(self.joint_positions_deg)} source poses from {csv_path} "
            f"and built {len(self.command_sequence)} replay commands."
        )

    def _resolve_csv_path(self, configured_path: str) -> Path:
        if configured_path:
            path = Path(configured_path).expanduser()
            if not path.exists():
                raise FileNotFoundError(f"Configured CSV path does not exist: {path}")
            return path

        installed_path = (
            Path(get_package_share_directory("leap_hand")) / "config" / POSITION_NODE_DEFAULT_CSV_FILENAME
        )
        if installed_path.exists():
            return installed_path

        source_path = Path(__file__).resolve().with_name(POSITION_NODE_DEFAULT_CSV_FILENAME)
        if source_path.exists():
            return source_path

        raise FileNotFoundError(
            f"Could not find {POSITION_NODE_DEFAULT_CSV_FILENAME} in the installed package or source tree."
        )

    def load_csv(self, path: Path, *, source_units: str) -> list[np.ndarray]:
        with path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            if len(header) != 16:
                raise ValueError(
                    f"Expected 16 joint columns in CSV header, found {len(header)}."
                )

            data = []
            for row_index, row in enumerate(reader, start=2):
                if len(row) != 16:
                    raise ValueError(
                        f"Expected 16 columns at CSV row {row_index}, found {len(row)}."
                    )
                pose = np.array([float(x) for x in row], dtype=float)
                if source_units == "radians":
                    pose = np.degrees(pose)
                elif source_units != "degrees":
                    raise ValueError(
                        f"Unsupported source_units '{source_units}'. Use 'radians' or 'degrees'."
                    )
                data.append(pose)

        if not data:
            raise ValueError(f"CSV file contained no data rows: {path}")

        return data

    def build_command_sequence(
        self,
        joint_positions_deg: list[np.ndarray],
        *,
        sample_stride: int,
        interpolation_steps: int,
    ) -> list[np.ndarray]:
        sampled = joint_positions_deg[::sample_stride]
        if len(sampled) < 2:
            sampled = joint_positions_deg
        if len(sampled) < 2:
            return [joint_positions_deg[0]]

        command_sequence = [sampled[0]]
        for i in range(len(sampled) - 1):
            start = sampled[i]
            end = sampled[i + 1]
            for j in range(1, interpolation_steps + 1):
                alpha = j / float(interpolation_steps)
                interp = start + (end - start) * alpha
                command_sequence.append(interp)
        return command_sequence

    def _on_timer(self) -> None:
        if self.count_subscribers(COMMAND_TOPIC) <= 0:
            if self._started:
                self.get_logger().warn(
                    f"Lost all subscribers on {COMMAND_TOPIC} while replaying; waiting to resume."
                )
                self._started = False
            return

        if not self._started:
            self._started = True
            self.get_logger().info(f"{COMMAND_TOPIC} subscriber detected. Starting replay.")

        if self._next_index >= len(self.command_sequence):
            self.get_logger().info("Replay complete. Holding final pose.")
            self._timer.cancel()
            return

        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.position = [float(x) for x in self.command_sequence[self._next_index]]
        self.pub.publish(msg)
        self._next_index += 1


def main(args=None):
    rclpy.init(args=args)
    position_node = PositionNode()
    try:
        rclpy.spin(position_node)
    finally:
        position_node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
