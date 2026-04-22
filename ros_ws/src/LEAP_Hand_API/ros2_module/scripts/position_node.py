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
        self.declare_parameter("save_trajectory_artifacts", True)
        self.declare_parameter("trajectory_output_dir", "trajectory_outputs")
        self.declare_parameter("trajectory_csv_filename", "joint_trajectory.csv")
        self.declare_parameter("trajectory_plot_filename", "joint_trajectory.png")

        self.pub = self.create_publisher(JointState, COMMAND_TOPIC, COMMAND_QUEUE_DEPTH)

        csv_path = self._resolve_csv_path(str(self.get_parameter("csv_path").value).strip())
        source_units = str(self.get_parameter("source_units").value).strip().lower()
        sample_stride = max(1, int(self.get_parameter("sample_stride").value))
        interpolation_steps = max(1, int(self.get_parameter("interpolation_steps").value))
        publish_period_sec = float(self.get_parameter("publish_period_sec").value)
        if publish_period_sec <= 0.0:
            raise ValueError("publish_period_sec must be > 0.")
        save_trajectory_artifacts = bool(
            self.get_parameter("save_trajectory_artifacts").value
        )
        trajectory_output_dir = str(
            self.get_parameter("trajectory_output_dir").value
        ).strip()
        trajectory_csv_filename = str(
            self.get_parameter("trajectory_csv_filename").value
        ).strip()
        trajectory_plot_filename = str(
            self.get_parameter("trajectory_plot_filename").value
        ).strip()

        self.joint_names, self.joint_positions_deg = self.load_csv(
            csv_path, source_units=source_units
        )
        self.command_sequence = self.build_command_sequence(
            self.joint_positions_deg,
            sample_stride=sample_stride,
            interpolation_steps=interpolation_steps,
        )
        self.command_sequence_array = np.asarray(self.command_sequence, dtype=float)
        self.trajectory_time_sec = self.build_time_vector(
            len(self.command_sequence), publish_period_sec
        )

        if save_trajectory_artifacts:
            self.save_trajectory_artifacts(
                trajectory_output_dir,
                trajectory_csv_filename,
                trajectory_plot_filename,
                self.trajectory_time_sec,
                self.command_sequence_array,
                self.joint_names,
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

    def load_csv(self, path: Path, *, source_units: str) -> tuple[list[str], list[np.ndarray]]:
        with path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            if len(header) != 16:
                raise ValueError(
                    f"Expected 16 joint columns in CSV header, found {len(header)}."
                )
            joint_names = [
                name.strip() if name.strip() else f"joint_{idx + 1}"
                for idx, name in enumerate(header)
            ]

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

        return joint_names, data

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
            p0 = sampled[max(i - 1, 0)]
            p1 = sampled[i]
            p2 = sampled[i + 1]
            p3 = sampled[min(i + 2, len(sampled) - 1)]

            for j in range(1, interpolation_steps + 1):
                t = j / float(interpolation_steps)
                t2 = t * t
                t3 = t2 * t

                interp = 0.5 * (
                    (2.0 * p1)
                    + (-p0 + p2) * t
                    + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
                    + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
                )

                command_sequence.append(interp)

        return command_sequence

    def build_time_vector(self, command_count: int, publish_period_sec: float) -> np.ndarray:
        return np.arange(command_count, dtype=float) * publish_period_sec

    def save_trajectory_artifacts(
        self,
        output_dir: str,
        csv_filename: str,
        plot_filename: str,
        time_sec: np.ndarray,
        trajectory_deg: np.ndarray,
        joint_names: list[str],
    ) -> None:
        output_path = Path(output_dir).expanduser()
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.get_logger().error(
                f"Failed to create planned trajectory output directory {output_path}: {e}"
            )
            return

        csv_path = output_path / csv_filename
        plot_path = output_path / plot_filename

        try:
            self.save_trajectory_csv(csv_path, time_sec, trajectory_deg, joint_names)
            self.get_logger().info(f"Saved planned trajectory CSV to {csv_path}")
        except Exception as e:
            self.get_logger().error(f"Failed to save planned trajectory CSV: {e}")

        try:
            self.save_trajectory_plot(plot_path, time_sec, trajectory_deg, joint_names)
            self.get_logger().info(f"Saved planned trajectory plot to {plot_path}")
        except Exception as e:
            self.get_logger().error(f"Failed to save planned trajectory plot: {e}")

    def save_trajectory_csv(
        self,
        output_path: Path,
        time_sec: np.ndarray,
        trajectory_deg: np.ndarray,
        joint_names: list[str],
    ) -> None:
        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["time_sec", *joint_names])
            for t, pose in zip(time_sec, trajectory_deg):
                writer.writerow([float(t), *[float(x) for x in pose]])

    def save_trajectory_plot(
        self,
        output_path: Path,
        time_sec: np.ndarray,
        trajectory_deg: np.ndarray,
        joint_names: list[str],
    ) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(4, 4, figsize=(16, 10), sharex=True)
        axes_flat = axes.flatten()

        for joint_idx, ax in enumerate(axes_flat):
            ax.plot(time_sec, trajectory_deg[:, joint_idx], linewidth=1.2)
            ax.set_title(joint_names[joint_idx], fontsize=9)
            ax.set_ylabel("deg", fontsize=8)
            ax.grid(True, alpha=0.3)

        for ax in axes_flat[-4:]:
            ax.set_xlabel("time (s)", fontsize=8)

        fig.suptitle("Planned LEAP Joint Trajectory", fontsize=14)
        fig.tight_layout(rect=(0, 0, 1, 0.97))
        fig.savefig(output_path, dpi=150)
        plt.close(fig)

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
