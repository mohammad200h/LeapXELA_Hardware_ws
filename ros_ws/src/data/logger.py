#!/usr/bin/env python3
"""ROS2 data logger for timestamp-aligned tactile and joint data."""

import argparse
import csv
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import h5py
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from xela_server_ros2.msg import SensStream


NS_PER_SEC = 1_000_000_000
EXPECTED_JOINT_COUNT = 16
POINT_DIM = 11
SENSOR_TIME_TOLERANCE_SEC = 1e-6
FLUSH_EVERY_N_WRITES = 10


def float_seconds_to_nanoseconds(float_seconds: float) -> int:
    """Convert floating-point seconds to canonical integer nanoseconds."""
    return int(round(float(float_seconds) * NS_PER_SEC))


def stamp_to_nanoseconds(sec: int, nanosec: int) -> int:
    """Convert ROS stamp fields to canonical integer nanoseconds."""
    return int(sec) * NS_PER_SEC + int(nanosec)


def nanoseconds_to_seconds(timestamp_ns: int) -> float:
    """Convert integer nanoseconds to floating-point seconds."""
    return float(timestamp_ns) / NS_PER_SEC


def timestamp_key(timestamp_ns: int) -> str:
    """Return the canonical string key used in CSV output."""
    return str(int(timestamp_ns))


@dataclass
class SensorPacket:
    """Normalized tactile packet for one logical timestep."""

    timestamp_ns: int
    timestamp_sec: float
    num_sensors: int
    points: np.ndarray
    received_monotonic: float


@dataclass
class JointPacket:
    """Normalized joint packet for one logical timestep."""

    timestamp_ns: int
    timestamp_sec: float
    joints: List[float]
    received_monotonic: float


class Hdf5SensorWriter:
    """Append-only HDF5 writer for variable-size sensor point sets."""

    def __init__(self, path: Path, include_reason: bool = False):
        self.path = path
        self.file = h5py.File(path, "a")
        self.group = self.file.require_group("sensor")
        self.include_reason = include_reason
        self.write_count = 0
        self._init_datasets()

    def _init_datasets(self) -> None:
        self.timestamp_ns = self._require_dataset("timestamp_ns", shape=(0,), maxshape=(None,), dtype=np.int64)
        self.timestamp_sec = self._require_dataset("timestamp_sec", shape=(0,), maxshape=(None,), dtype=np.float64)
        self.point_start_idx = self._require_dataset("point_start_idx", shape=(0,), maxshape=(None,), dtype=np.int64)
        self.point_count = self._require_dataset("point_count", shape=(0,), maxshape=(None,), dtype=np.int64)
        self.num_sensors = self._require_dataset("num_sensors", shape=(0,), maxshape=(None,), dtype=np.int32)
        self.points = self._require_dataset(
            "points",
            shape=(0, POINT_DIM),
            maxshape=(None, POINT_DIM),
            dtype=np.float32,
        )

        self.reason = None
        if self.include_reason:
            self.reason = self._require_dataset(
                "reason",
                shape=(0,),
                maxshape=(None,),
                dtype=h5py.string_dtype(encoding="utf-8"),
            )

    def _require_dataset(self, name: str, shape: tuple, maxshape: tuple, dtype):
        if name in self.group:
            return self.group[name]
        return self.group.create_dataset(name, shape=shape, maxshape=maxshape, chunks=True, dtype=dtype)

    @staticmethod
    def _append_1d(dataset, value) -> None:
        current_size = dataset.shape[0]
        dataset.resize((current_size + 1,))
        dataset[current_size] = value

    @staticmethod
    def _append_points(dataset, value: np.ndarray) -> int:
        current_size = dataset.shape[0]
        point_count = int(value.shape[0])
        dataset.resize((current_size + point_count, dataset.shape[1]))
        if point_count > 0:
            dataset[current_size : current_size + point_count] = value
        return current_size

    def append(self, packet: SensorPacket, reason: Optional[str] = None) -> None:
        """Append one normalized tactile packet."""
        points = np.asarray(packet.points, dtype=np.float32)
        point_start_idx = self._append_points(self.points, points)
        self._append_1d(self.timestamp_ns, packet.timestamp_ns)
        self._append_1d(self.timestamp_sec, packet.timestamp_sec)
        self._append_1d(self.point_start_idx, point_start_idx)
        self._append_1d(self.point_count, points.shape[0])
        self._append_1d(self.num_sensors, packet.num_sensors)

        if self.reason is not None:
            self._append_1d(self.reason, "" if reason is None else reason)

        self.write_count += 1
        if self.write_count % FLUSH_EVERY_N_WRITES == 0:
            self.flush()

    def flush(self) -> None:
        self.file.flush()

    def close(self) -> None:
        self.file.flush()
        self.file.close()


class JointCsvWriter:
    """Append-only CSV writer for aligned joint rows."""

    def __init__(self, path: Path, include_reason: bool = False):
        self.path = path
        self.include_reason = include_reason
        self.fieldnames = [
            "timestamp_key",
            "timestamp_ns",
            "timestamp_sec",
            *[f"joint_{index}" for index in range(EXPECTED_JOINT_COUNT)],
        ]
        if include_reason:
            self.fieldnames.append("reason")

        self.file = path.open("a", newline="")
        self.writer = csv.DictWriter(self.file, fieldnames=self.fieldnames)
        if path.stat().st_size == 0:
            self.writer.writeheader()
            self.file.flush()
        self.write_count = 0

    def append(self, packet: JointPacket, reason: Optional[str] = None) -> None:
        """Append one normalized joint packet."""
        row = {
            "timestamp_key": timestamp_key(packet.timestamp_ns),
            "timestamp_ns": packet.timestamp_ns,
            "timestamp_sec": packet.timestamp_sec,
        }
        for index, value in enumerate(packet.joints):
            row[f"joint_{index}"] = value
        if self.include_reason:
            row["reason"] = "" if reason is None else reason
        self.writer.writerow(row)

        self.write_count += 1
        if self.write_count % FLUSH_EVERY_N_WRITES == 0:
            self.flush()

    def flush(self) -> None:
        self.file.flush()

    def close(self) -> None:
        self.file.flush()
        self.file.close()


class DataLogger(Node):
    """Log matched tactile and joint data into aligned output files."""

    def __init__(self, args: argparse.Namespace):
        super().__init__("data_logger")
        self.args = args
        self.output_dir = Path(args.output_dir).expanduser().resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.pending_sensors: Dict[int, SensorPacket] = {}
        self.pending_joints: Dict[int, JointPacket] = {}

        self.sensor_writer = Hdf5SensorWriter(self.output_dir / "sensor_log.h5", include_reason=False)
        self.joint_writer = JointCsvWriter(self.output_dir / "joint_log.csv", include_reason=False)

        self.unmatched_sensor_writer = None
        self.unmatched_joint_writer = None
        if self.args.write_unmatched:
            self.unmatched_sensor_writer = Hdf5SensorWriter(
                self.output_dir / "unmatched_sensor.h5",
                include_reason=True,
            )
            self.unmatched_joint_writer = JointCsvWriter(
                self.output_dir / "unmatched_joint.csv",
                include_reason=True,
            )

        self.create_subscription(SensStream, self.args.sensor_topic, self._on_sensor_message, 10)
        self.create_subscription(JointState, self.args.joint_topic, self._on_joint_message, 10)
        self.stale_timer = self.create_timer(0.5, self.flush_stale_unmatched)

        self.get_logger().info(
            f"Logging sensors from {self.args.sensor_topic} and joints from {self.args.joint_topic} "
            f"into {self.output_dir}"
        )

    def _on_sensor_message(self, msg: SensStream) -> None:
        """Normalize a sensor packet, buffer it, and try to write a matched pair."""
        packet = self._normalize_sensor_message(msg)
        if packet is None:
            return

        existing = self.pending_sensors.get(packet.timestamp_ns)
        if existing is not None:
            self.get_logger().warning(
                f"Replacing pending sensor packet for timestamp {packet.timestamp_ns}"
            )
        self.pending_sensors[packet.timestamp_ns] = packet
        self.write_matched_pair(packet.timestamp_ns)
        self.flush_stale_unmatched()

    def _on_joint_message(self, msg: JointState) -> None:
        """Normalize a joint packet, buffer it, and try to write a matched pair."""
        packet = self._normalize_joint_message(msg)
        if packet is None:
            return

        existing = self.pending_joints.get(packet.timestamp_ns)
        if existing is not None:
            self.get_logger().warning(
                f"Replacing pending joint packet for timestamp {packet.timestamp_ns}"
            )
        self.pending_joints[packet.timestamp_ns] = packet
        self.write_matched_pair(packet.timestamp_ns)
        self.flush_stale_unmatched()

    def _normalize_sensor_message(self, msg: SensStream) -> Optional[SensorPacket]:
        """Convert a `SensStream` message into a normalized packet."""
        if not msg.sensors:
            self.get_logger().warning("Received /xServTopic message with no sensors")
            return None

        sensor_times = [float(sensor.time) for sensor in msg.sensors]
        source_time_sec = sensor_times[0]
        max_deviation = max(abs(sensor_time - source_time_sec) for sensor_time in sensor_times)
        if max_deviation > SENSOR_TIME_TOLERANCE_SEC:
            self.get_logger().warning(
                "SensorFull.time values differ within one SensStream packet; "
                f"max deviation={max_deviation:.9f}s. Using the first timestamp."
            )

        ordered_sensors = sorted(msg.sensors, key=lambda sensor: int(sensor.sensor_pos))
        points: List[List[float]] = []

        for sensor_index, sensor in enumerate(ordered_sensors):
            sensor_id = int(sensor.sensor_pos)
            taxels = sensor.taxels
            forces = sensor.forces if self.args.include_forces else []

            for taxel_index, taxel in enumerate(taxels):
                force_x = math.nan
                force_y = math.nan
                force_z = math.nan
                if taxel_index < len(forces):
                    force_x = float(forces[taxel_index].x)
                    force_y = float(forces[taxel_index].y)
                    force_z = float(forces[taxel_index].z)

                points.append(
                    [
                        float(sensor_index),
                        float(taxel_index),
                        0.0,
                        float(taxel.x),
                        float(taxel.y),
                        float(taxel.z),
                        force_x,
                        force_y,
                        force_z,
                        float(sensor_id),
                        float(taxel_index),
                    ]
                )

        packet_time_ns = float_seconds_to_nanoseconds(source_time_sec)
        return SensorPacket(
            timestamp_ns=packet_time_ns,
            timestamp_sec=source_time_sec,
            num_sensors=len(ordered_sensors),
            points=np.asarray(points, dtype=np.float32),
            received_monotonic=time.monotonic(),
        )

    def _normalize_joint_message(self, msg: JointState) -> Optional[JointPacket]:
        """Convert a `JointState` message into a normalized packet."""
        joints = list(msg.position)
        if len(joints) != EXPECTED_JOINT_COUNT:
            self.get_logger().warning(
                f"Expected {EXPECTED_JOINT_COUNT} joints on {self.args.joint_topic}, got {len(joints)}"
            )
            return None

        stamp = msg.header.stamp
        packet_time_ns = stamp_to_nanoseconds(stamp.sec, stamp.nanosec)
        return JointPacket(
            timestamp_ns=packet_time_ns,
            timestamp_sec=nanoseconds_to_seconds(packet_time_ns),
            joints=[float(value) for value in joints],
            received_monotonic=time.monotonic(),
        )

    def write_matched_pair(self, key: int) -> bool:
        """Write a matched sensor/joint pair through one shared code path."""
        sensor_packet = self.pending_sensors.get(key)
        joint_packet = self.pending_joints.get(key)
        if sensor_packet is None or joint_packet is None:
            return False

        self.sensor_writer.append(sensor_packet)
        self.joint_writer.append(joint_packet)

        del self.pending_sensors[key]
        del self.pending_joints[key]
        return True

    def flush_stale_unmatched(self) -> None:
        """Move stale buffered packets to unmatched outputs if enabled."""
        if not self.args.write_unmatched:
            return

        cutoff = time.monotonic() - self.args.max_pending_age_sec
        self._flush_stale_buffer(
            pending=self.pending_sensors,
            cutoff=cutoff,
            flush_fn=self._write_unmatched_sensor,
        )
        self._flush_stale_buffer(
            pending=self.pending_joints,
            cutoff=cutoff,
            flush_fn=self._write_unmatched_joint,
        )

    def _flush_stale_buffer(self, pending: Dict[int, object], cutoff: float, flush_fn) -> None:
        stale_keys = [key for key, packet in pending.items() if packet.received_monotonic <= cutoff]
        for key in sorted(stale_keys):
            flush_fn(key, "timeout")

    def _write_unmatched_sensor(self, key: int, reason: str) -> None:
        packet = self.pending_sensors.pop(key, None)
        if packet is None:
            return
        self.unmatched_sensor_writer.append(packet, reason=reason)

    def _write_unmatched_joint(self, key: int, reason: str) -> None:
        packet = self.pending_joints.pop(key, None)
        if packet is None:
            return
        self.unmatched_joint_writer.append(packet, reason=reason)

    def flush_remaining(self) -> None:
        """Flush remaining matched and unmatched entries during shutdown."""
        matched_keys = sorted(set(self.pending_sensors).intersection(self.pending_joints))
        for key in matched_keys:
            self.write_matched_pair(key)

        if self.args.write_unmatched:
            for key in sorted(list(self.pending_sensors.keys())):
                self._write_unmatched_sensor(key, "shutdown_unmatched")
            for key in sorted(list(self.pending_joints.keys())):
                self._write_unmatched_joint(key, "shutdown_unmatched")
        else:
            if self.pending_sensors:
                self.get_logger().warning(
                    f"Dropping {len(self.pending_sensors)} unmatched sensor packets because --no-write-unmatched was set"
                )
            if self.pending_joints:
                self.get_logger().warning(
                    f"Dropping {len(self.pending_joints)} unmatched joint packets because --no-write-unmatched was set"
                )
            self.pending_sensors.clear()
            self.pending_joints.clear()

    def close_outputs(self) -> None:
        """Flush and close all file writers."""
        self.sensor_writer.close()
        self.joint_writer.close()
        if self.unmatched_sensor_writer is not None:
            self.unmatched_sensor_writer.close()
        if self.unmatched_joint_writer is not None:
            self.unmatched_joint_writer.close()


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for the logger."""
    parser = argparse.ArgumentParser(
        description="Log timestamp-aligned XELA tactile data and Leap hand joint states."
    )
    parser.add_argument("--output-dir", default=".", help="Directory for sensor and joint log files")
    parser.add_argument("--sensor-topic", default="/xServTopic", help="Tactile sensor topic")
    parser.add_argument("--joint-topic", default="/leap_joint_states", help="LeapNode joint topic")
    parser.add_argument(
        "--max-pending-age-sec",
        type=float,
        default=2.0,
        help="How long unmatched packets stay buffered before being written as unmatched",
    )
    parser.add_argument(
        "--write-unmatched",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write stale and shutdown-unmatched packets to separate files",
    )
    parser.add_argument(
        "--include-forces",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include per-taxel force values when present; otherwise write NaN force columns",
    )
    return parser


def main(args: Optional[Iterable[str]] = None) -> None:
    """Run the ROS2 logger node."""
    parser = build_arg_parser()
    parsed_args = parser.parse_args(args=args)

    rclpy.init(args=None)
    node = DataLogger(parsed_args)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Keyboard interrupt received, shutting down logger")
    finally:
        try:
            node.flush_remaining()
            node.close_outputs()
        finally:
            node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()


if __name__ == "__main__":
    main()
