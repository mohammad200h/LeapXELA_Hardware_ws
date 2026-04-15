#!/usr/bin/env python3

import argparse
import math
from pathlib import Path
import shutil
import time

from rclpy.serialization import serialize_message
from rosbag2_py import ConverterOptions, SequentialWriter, StorageOptions, TopicMetadata
from sensor_msgs.msg import JointState


JOINT_NAMES = [f"joint{i}" for i in range(1, 17)]
OPEN_POSE_DEG = [
    180.0,
    180.0,
    180.0,
    90.0,
    265.0,
    180.0,
    180.0,
    180.0,
    265.0,
    180.0,
    180.0,
    180.0,
    265.0,
    180.0,
    180.0,
    180.0,
]
FLEX_OFFSETS_DEG = [
    0.0,
    -18.0,
    -24.0,
    -12.0,
    0.0,
    -16.0,
    -22.0,
    -10.0,
    0.0,
    -14.0,
    -20.0,
    -10.0,
    0.0,
    -12.0,
    -16.0,
    -8.0,
]


def build_positions(sample_index: int, total_samples: int) -> list[float]:
    if total_samples <= 1:
        alpha = 0.0
    else:
        phase = sample_index / float(total_samples - 1)
        alpha = 0.5 - 0.5 * math.cos(phase * 2.0 * math.pi)
    return [
        float(base + alpha * offset)
        for base, offset in zip(OPEN_POSE_DEG, FLEX_OFFSETS_DEG)
    ]


def build_joint_state(sample_index: int, total_samples: int, stamp_ns: int) -> JointState:
    msg = JointState()
    msg.header.stamp.sec = int(stamp_ns // 1_000_000_000)
    msg.header.stamp.nanosec = int(stamp_ns % 1_000_000_000)
    msg.header.frame_id = "leap_hand"
    msg.name = list(JOINT_NAMES)
    msg.position = build_positions(sample_index, total_samples)
    msg.velocity = [0.0] * len(JOINT_NAMES)
    msg.effort = [0.0] * len(JOINT_NAMES)
    return msg


def create_example_bag(
    output_uri: Path,
    *,
    topic_name: str,
    sample_count: int,
    step_sec: float,
    force: bool,
) -> Path:
    if output_uri.exists():
        if not force:
            raise FileExistsError(
                f"Output bag directory already exists: {output_uri}. "
                "Use --force to replace it."
            )
        shutil.rmtree(output_uri)

    writer = SequentialWriter()
    writer.open(
        StorageOptions(uri=str(output_uri), storage_id="sqlite3"),
        ConverterOptions(input_serialization_format="cdr", output_serialization_format="cdr"),
    )
    writer.create_topic(
        TopicMetadata(
            name=topic_name,
            type="sensor_msgs/msg/JointState",
            serialization_format="cdr",
        )
    )

    step_ns = int(step_sec * 1_000_000_000)
    start_ns = time.time_ns()
    for sample_index in range(sample_count):
        stamp_ns = start_ns + sample_index * step_ns
        msg = build_joint_state(sample_index, sample_count, stamp_ns)
        writer.write(topic_name, serialize_message(msg), stamp_ns)

    return output_uri


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a small example ROS 2 bag for /cmd_xela playback."
    )
    parser.add_argument(
        "--output-uri",
        default="example_cmd_xela_bag",
        help="Output bag directory to create.",
    )
    parser.add_argument(
        "--topic-name",
        default="/cmd_xela",
        help="Topic recorded into the bag. Default matches the live LEAP command topic.",
    )
    parser.add_argument(
        "--sample-count",
        type=int,
        default=16,
        help="Number of JointState messages to record into the bag.",
    )
    parser.add_argument(
        "--step-sec",
        type=float,
        default=0.25,
        help="Time delta between bag messages in seconds.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace the output bag directory if it already exists.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.sample_count <= 0:
        raise SystemExit("--sample-count must be > 0")
    if args.step_sec <= 0.0:
        raise SystemExit("--step-sec must be > 0")

    output_uri = Path(args.output_uri).expanduser()
    bag_path = create_example_bag(
        output_uri,
        topic_name=args.topic_name,
        sample_count=args.sample_count,
        step_sec=args.step_sec,
        force=bool(args.force),
    )
    print(f"Created example bag at {bag_path}")


if __name__ == "__main__":
    main()
