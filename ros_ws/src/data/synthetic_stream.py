#!/usr/bin/env python3
"""Publish synthetic tactile and joint streams for testing logger.py."""

import argparse
import math
import time
from typing import Iterable, Optional

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from xela_server_ros2.msg import Forces, SensStream, SensorFull, Taxel


NS_PER_SEC = 1_000_000_000
DEFAULT_SENSOR_TOPIC = "/xServTopic"
DEFAULT_JOINT_TOPIC = "/leap_joint_states"
DEFAULT_JOINT_COUNT = 16


def float_seconds_to_nanoseconds(float_seconds: float) -> int:
    """Convert float seconds to the logger's canonical nanoseconds."""
    return int(round(float(float_seconds) * NS_PER_SEC))


class SyntheticStreamPublisher(Node):
    """Publish matched synthetic sensor and joint packets."""

    def __init__(self, args: argparse.Namespace):
        super().__init__("synthetic_stream_publisher")
        self.args = args
        self.sequence = 0
        self.start_time = time.time()

        self.sensor_pub = self.create_publisher(SensStream, args.sensor_topic, 10)
        self.joint_pub = self.create_publisher(JointState, args.joint_topic, 10)
        self.timer = self.create_timer(1.0 / args.rate_hz, self._on_timer)

        self.get_logger().info(
            f"Publishing synthetic sensor data on {args.sensor_topic} and joint data on {args.joint_topic}"
        )

    def _on_timer(self) -> None:
        self.sequence += 1

        elapsed_sec = time.time() - self.start_time
        if self.args.duration_sec > 0.0 and elapsed_sec >= self.args.duration_sec:
            self.get_logger().info("Synthetic stream duration reached, stopping node")
            raise KeyboardInterrupt

        source_time_sec = time.time()
        source_time_ns = float_seconds_to_nanoseconds(source_time_sec)

        publish_sensor = not self._should_drop(self.args.drop_sensor_every)
        publish_joint = not self._should_drop(self.args.drop_joint_every)

        if publish_sensor:
            self.sensor_pub.publish(self._build_sensor_message(source_time_sec))
        if publish_joint:
            self.joint_pub.publish(self._build_joint_message(source_time_ns))

    def _should_drop(self, drop_every: int) -> bool:
        return drop_every > 0 and self.sequence % drop_every == 0

    def _build_sensor_message(self, source_time_sec: float) -> SensStream:
        msg = SensStream()
        msg.sensors = []

        for sensor_offset in range(self.args.sensor_count):
            sensor = SensorFull()
            sensor.message = self.sequence
            sensor.time = source_time_sec
            sensor.model = self.args.sensor_model
            sensor.sensor_pos = sensor_offset + 1
            sensor.taxels = []
            sensor.forces = []

            for taxel_index in range(self.args.taxels_per_sensor):
                phase = self.sequence * 0.1 + sensor_offset * 0.5 + taxel_index * 0.2

                taxel = Taxel()
                taxel.x = int(32000 + 6000 * math.sin(phase))
                taxel.y = int(32000 + 5000 * math.cos(phase * 0.9))
                taxel.z = int(32000 + 4000 * math.sin(phase * 1.1))
                sensor.taxels.append(taxel)

                if self.args.include_forces:
                    force = Forces()
                    force.x = float(2.0 * math.sin(phase))
                    force.y = float(2.0 * math.cos(phase))
                    force.z = float(4.0 + 0.5 * math.sin(phase * 1.2))
                    sensor.forces.append(force)

            msg.sensors.append(sensor)

        return msg

    def _build_joint_message(self, source_time_ns: int) -> JointState:
        msg = JointState()
        msg.header.stamp.sec = source_time_ns // NS_PER_SEC
        msg.header.stamp.nanosec = source_time_ns % NS_PER_SEC
        msg.position = [
            float(0.4 * math.sin(self.sequence * 0.08 + joint_index * 0.15))
            for joint_index in range(DEFAULT_JOINT_COUNT)
        ]
        msg.name = [f"joint_{joint_index}" for joint_index in range(DEFAULT_JOINT_COUNT)]
        return msg


def build_arg_parser() -> argparse.ArgumentParser:
    """Create CLI options for the synthetic stream generator."""
    parser = argparse.ArgumentParser(
        description="Publish synthetic /xServTopic and /leap_joint_states messages for logger testing."
    )
    parser.add_argument("--sensor-topic", default=DEFAULT_SENSOR_TOPIC, help="Synthetic tactile topic")
    parser.add_argument("--joint-topic", default=DEFAULT_JOINT_TOPIC, help="Synthetic joint topic")
    parser.add_argument("--rate-hz", type=float, default=10.0, help="Publish rate in Hz")
    parser.add_argument("--duration-sec", type=float, default=0.0, help="Total publish duration, 0 means run forever")
    parser.add_argument("--sensor-count", type=int, default=4, help="Number of sensors per SensStream message")
    parser.add_argument("--taxels-per-sensor", type=int, default=16, help="Taxels per sensor")
    parser.add_argument("--sensor-model", default="synthetic", help="Model string to place into SensorFull.model")
    parser.add_argument(
        "--include-forces",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Publish synthetic Forces values alongside Taxels",
    )
    parser.add_argument(
        "--drop-sensor-every",
        type=int,
        default=0,
        help="If > 0, skip every Nth sensor message to test unmatched joint handling",
    )
    parser.add_argument(
        "--drop-joint-every",
        type=int,
        default=0,
        help="If > 0, skip every Nth joint message to test unmatched sensor handling",
    )
    return parser


def main(args: Optional[Iterable[str]] = None) -> None:
    """Run the synthetic stream publisher."""
    parser = build_arg_parser()
    parsed_args = parser.parse_args(args=args)

    rclpy.init(args=None)
    node = SyntheticStreamPublisher(parsed_args)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Stopping synthetic stream publisher")
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
