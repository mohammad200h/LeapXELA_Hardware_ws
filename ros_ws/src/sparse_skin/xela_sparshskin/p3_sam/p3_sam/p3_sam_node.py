#!/usr/bin/env python3
"""
Segment the RealSense point cloud into parts with P3-SAM.

The network labels points. Each camera cloud is subsampled, given normals, and
segmented. Clouds that arrive while a segmentation is running are replaced by
the newest one.

Subscribes:
  - sensor_msgs/PointCloud2 on ``cloud_topic``
Publishes:
  - std_msgs/String on ``{topic_prefix}/parts``, JSON part ids and boxes
  - sensor_msgs/PointCloud2 on ``{topic_prefix}/cloud``, points colored by part
"""

from __future__ import annotations

import threading
import time

import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import (
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Header, String

from p3_sam.messages import cloud_points, parts_cloud, parts_string
from p3_sam.segmenter import P3SamSegmenter

CLOUD_QOS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)


class P3SamNode(Node):
    """Load P3-SAM once and segment the latest camera cloud."""

    def __init__(self) -> None:
        super().__init__("p3_sam")
        topic_prefix = self.declare_parameter("topic_prefix", "/p3_sam").value.rstrip("/")
        cloud_topic = self.declare_parameter(
            "cloud_topic", "/camera/aligned_depth_to_color/color/points"
        ).value
        self._segmenter = P3SamSegmenter(
            ckpt_path=self.declare_parameter("ckpt_path", "").value,
            upstream_root=self.declare_parameter("upstream_root", "").value,
            point_num=int(self.declare_parameter("point_num", 20000).value),
            prompt_num=int(self.declare_parameter("prompt_num", 80).value),
            prompt_bs=int(self.declare_parameter("prompt_bs", 8).value),
            seed=int(self.declare_parameter("seed", 42).value),
        )
        self._segmenter.stage_log = self.get_logger().info
        self.get_logger().info("Loading P3-SAM ...")
        self._segmenter.load()
        self.get_logger().info("P3-SAM loaded")

        self._lock = threading.Lock()
        self._pending = None
        self._segmenting = False
        self._running = True
        self._ready = threading.Event()
        self._worker = threading.Thread(target=self._loop, name="p3_sam_segment", daemon=True)
        self._parts_pub = self.create_publisher(
            String, f"{topic_prefix}/parts", QoSProfile(depth=10)
        )
        self._cloud_pub = self.create_publisher(
            PointCloud2, f"{topic_prefix}/cloud", CLOUD_QOS
        )
        self.create_subscription(
            PointCloud2,
            cloud_topic,
            self._on_cloud,
            qos_profile_sensor_data,
            callback_group=MutuallyExclusiveCallbackGroup(),
        )
        self._worker.start()
        self.get_logger().info(f"Waiting for a point cloud on '{cloud_topic}'")

    def close(self) -> None:
        """Stop the segmentation thread."""
        self._running = False
        self._ready.set()
        self._worker.join(timeout=1.0)

    def _on_cloud(self, msg: PointCloud2) -> None:
        with self._lock:
            segmenting = self._segmenting
            self._pending = msg
            self._ready.set()
        if segmenting:
            self.get_logger().info(
                "Segmentation is still running; keeping the latest cloud",
                throttle_duration_sec=5.0,
            )

    def _loop(self) -> None:
        while self._running:
            if not self._ready.wait(timeout=0.2):
                continue
            with self._lock:
                msg = self._pending
                self._pending = None
                self._ready.clear()
                self._segmenting = msg is not None
            if msg is None or not self._running:
                continue
            try:
                self._segment_and_publish(msg)
            finally:
                with self._lock:
                    self._segmenting = False

    def _segment_and_publish(self, msg: PointCloud2) -> None:
        try:
            points = cloud_points(msg)
            self.get_logger().info(
                f"Cloud with {len(points)} points from '{msg.header.frame_id}'"
            )
            started = time.perf_counter()
            result = self._segmenter.segment(points)
        except Exception as exc:  # noqa: BLE001  keep the node alive on a bad cloud
            self.get_logger().error(f"P3-SAM failed: {exc}")
            return
        latency_ms = (time.perf_counter() - started) * 1000.0
        header = Header()
        header.stamp = msg.header.stamp
        header.frame_id = msg.header.frame_id
        self._parts_pub.publish(parts_string(result, latency_ms))
        self._cloud_pub.publish(parts_cloud(result, header))
        self.get_logger().info(
            f"{result.part_count} parts, {result.point_count} points, in {latency_ms:.0f} ms"
        )


def main(args=None) -> None:
    """Start the P3-SAM node."""
    rclpy.init(args=args)
    node = P3SamNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.close()
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
