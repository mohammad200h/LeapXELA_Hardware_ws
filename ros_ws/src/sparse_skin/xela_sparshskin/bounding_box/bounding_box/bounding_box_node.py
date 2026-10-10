#!/usr/bin/env python3
"""
Draw a SAM 3 bounding box around the pen in the RealSense color image.

Subscribes:
  - sensor_msgs/Image on ``/camera/color/image_raw``
  - sensor_msgs/Image on ``/camera/aligned_depth_to_color/image_raw``
Publishes:
  - sensor_msgs/Image on ``{topic_prefix}/image``, the annotated frame
  - vision_msgs/Detection2DArray on ``{topic_prefix}/detections``
  - std_msgs/String on ``{topic_prefix}/boxes``, JSON boxes and latency
  - sensor_msgs/Image on ``{topic_prefix}/mask``, the best instance mask
"""

from __future__ import annotations

import json
import math
import threading
import time

import numpy as np
import rclpy
from geometry_msgs.msg import Pose2D
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String

try:
    from vision_msgs.msg import (
        BoundingBox2D,
        Detection2D,
        Detection2DArray,
        ObjectHypothesisWithPose,
    )
except ImportError:  # pragma: no cover - optional on hosts without vision_msgs
    BoundingBox2D = Detection2D = Detection2DArray = ObjectHypothesisWithPose = None

from bounding_box.boxes import PenBox, draw_boxes, mask_to_box, refine_mask_with_depth
from bounding_box.image_utils import (
    depth_msg_to_mm,
    image_msg_to_rgb,
    mask_to_image_msg,
    rgb_to_image_msg,
)
from bounding_box.sam3_segmenter import Sam3Segmenter


def _stamp_seconds(header) -> float:
    return header.stamp.sec + header.stamp.nanosec * 1e-9


def _fill_hypothesis(hyp: ObjectHypothesisWithPose, class_id: str, score: float) -> None:
    hyp.hypothesis.score = score
    if hasattr(hyp.hypothesis, "class_id"):
        hyp.hypothesis.class_id = class_id
    elif hasattr(hyp.hypothesis, "id"):
        hyp.hypothesis.id = 1


class BoundingBoxNode(Node):
    """Run SAM 3 on the latest camera frame and publish a tight pen box."""

    def __init__(self) -> None:
        super().__init__("bounding_box")

        image_topic = self.declare_parameter("image_topic", "/camera/color/image_raw").value
        depth_topic = self.declare_parameter(
            "depth_topic", "/camera/aligned_depth_to_color/image_raw"
        ).value
        topic_prefix = self.declare_parameter("topic_prefix", "/bounding_box").value.rstrip("/")
        self._prompt = self.declare_parameter("prompt", "pen").value
        self._use_depth = self.declare_parameter("use_depth", True).value
        self._publish_mask = self.declare_parameter("publish_mask", True).value
        self._min_depth = self.declare_parameter("min_depth", 0.15).value
        self._max_depth = self.declare_parameter("max_depth", 1.5).value
        rate_hz = self.declare_parameter("rate_hz", 3.0).value
        conf = self.declare_parameter("conf", 0.25).value
        model = self.declare_parameter("model", "sam3.pt").value
        device = self.declare_parameter("device", "").value

        self.get_logger().info(f"Loading SAM 3 from '{model}' ...")
        self._segmenter = Sam3Segmenter(model=model, conf=conf, device=device)
        self.get_logger().info("SAM 3 loaded")

        self._lock = threading.Lock()
        self._latest_color: Image | None = None
        self._latest_depth: Image | None = None
        self._frames_received = 0
        self._frames_processed = 0
        self._detections_total = 0
        self._latencies: list[float] = []

        self._image_pub = self.create_publisher(
            Image, f"{topic_prefix}/image", qos_profile_sensor_data
        )
        self._mask_pub = self.create_publisher(
            Image, f"{topic_prefix}/mask", qos_profile_sensor_data
        )
        self._det_pub = None
        if Detection2DArray is not None:
            self._det_pub = self.create_publisher(
                Detection2DArray, f"{topic_prefix}/detections", QoSProfile(depth=10)
            )
        else:
            self.get_logger().warn(
                "vision_msgs is not installed; /detections will not be published. "
                "JSON boxes still go out on /boxes."
            )
        self._boxes_pub = self.create_publisher(
            String, f"{topic_prefix}/boxes", QoSProfile(depth=10)
        )
        self.create_subscription(Image, image_topic, self._on_color, qos_profile_sensor_data)
        if self._use_depth:
            self.create_subscription(Image, depth_topic, self._on_depth, qos_profile_sensor_data)
        self.create_timer(
            1.0 / max(rate_hz, 0.1),
            self._on_timer,
            callback_group=MutuallyExclusiveCallbackGroup(),
        )
        self.create_timer(5.0, self._log_stats)
        self.get_logger().info(
            f"Listening on '{image_topic}' prompt='{self._prompt}' at {rate_hz} Hz"
        )

    def _on_color(self, msg: Image) -> None:
        with self._lock:
            self._latest_color = msg
            self._frames_received += 1

    def _on_depth(self, msg: Image) -> None:
        with self._lock:
            self._latest_depth = msg

    def _take_latest(self) -> tuple[Image | None, Image | None]:
        with self._lock:
            color, self._latest_color = self._latest_color, None
            depth = self._latest_depth
        return color, depth

    def _boxes_from_segments(self, rgb: np.ndarray, depth_mm: np.ndarray | None) -> list[PenBox]:
        segments = self._segmenter.segment(rgb, self._prompt)
        boxes: list[PenBox] = []
        for index, segment in enumerate(segments):
            mask = segment.mask
            refined = False
            if depth_mm is not None:
                mask, refined = refine_mask_with_depth(
                    mask, depth_mm, self._min_depth, self._max_depth
                )
            box = mask_to_box(mask, segment.score, best=index == 0)
            if box is None:
                continue
            box.depth_refined = refined
            boxes.append(box)
        return boxes

    def _detection_msg(self, box: PenBox, header):
        det = Detection2D()
        det.header = header
        det.bbox = BoundingBox2D(
            center=Pose2D(
                x=box.center[0],
                y=box.center[1],
                theta=math.radians(box.angle_deg),
            ),
            size_x=box.size[0],
            size_y=box.size[1],
        )
        hyp = ObjectHypothesisWithPose()
        _fill_hypothesis(hyp, self._prompt, box.score)
        det.results.append(hyp)
        if hasattr(det, "id"):
            det.id = "best" if box.best else "pen"
        return det

    def _boxes_json(self, boxes: list[PenBox], header, latency_ms: float) -> str:
        return json.dumps({
            "stamp": _stamp_seconds(header),
            "frame_id": header.frame_id,
            "latency_ms": round(latency_ms, 1),
            "prompt": self._prompt,
            "detections": [
                {
                    "score": round(box.score, 4),
                    "best": box.best,
                    "depth_refined": box.depth_refined,
                    "xyxy": list(box.xyxy),
                    "rotated": {
                        "cx": round(box.center[0], 2),
                        "cy": round(box.center[1], 2),
                        "width": round(box.size[0], 2),
                        "height": round(box.size[1], 2),
                        "angle_deg": round(box.angle_deg, 2),
                        "corners": np.round(box.corners, 1).tolist(),
                    },
                }
                for box in boxes
            ],
        })

    def _on_timer(self) -> None:
        color_msg, depth_msg = self._take_latest()
        if color_msg is None:
            return

        rgb = image_msg_to_rgb(color_msg)
        depth_mm = None
        if self._use_depth and depth_msg is not None:
            dt = abs(_stamp_seconds(color_msg.header) - _stamp_seconds(depth_msg.header))
            if dt <= 0.15:
                try:
                    depth_mm = depth_msg_to_mm(depth_msg)
                except ValueError as exc:
                    self.get_logger().warn(str(exc), throttle_duration_sec=5.0)

        start = time.monotonic()
        boxes = self._boxes_from_segments(rgb, depth_mm)
        latency_ms = (time.monotonic() - start) * 1000.0

        annotated = draw_boxes(rgb, boxes)
        self._image_pub.publish(rgb_to_image_msg(annotated, color_msg.header))
        if self._publish_mask:
            mask = boxes[0].mask if boxes else np.zeros(rgb.shape[:2], dtype=np.uint8)
            self._mask_pub.publish(mask_to_image_msg(mask, color_msg.header))

        if self._det_pub is not None:
            detections = Detection2DArray(header=color_msg.header)
            detections.detections = [
                self._detection_msg(box, color_msg.header) for box in boxes
            ]
            self._det_pub.publish(detections)
        self._boxes_pub.publish(String(data=self._boxes_json(boxes, color_msg.header, latency_ms)))

        self._frames_processed += 1
        self._detections_total += len(boxes)
        self._latencies.append(latency_ms)

    def _log_stats(self) -> None:
        if self._frames_received == 0:
            self.get_logger().warn("No camera frames received yet")
            return
        mean_latency = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        self.get_logger().info(
            f"Frames received: {self._frames_received}, processed: {self._frames_processed}, "
            f"mean latency: {mean_latency:.0f} ms, detections: {self._detections_total}"
        )
        self._latencies.clear()
        self._detections_total = 0


def main(args=None):
    """Spin the bounding box node."""
    rclpy.init(args=args)
    node = BoundingBoxNode()
    try:
        rclpy.spin(node, executor=MultiThreadedExecutor())
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
