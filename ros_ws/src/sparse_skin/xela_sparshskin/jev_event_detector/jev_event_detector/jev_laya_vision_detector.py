#!/usr/bin/env python3
"""Detect pen events in the camera feed with the Laya-vision model.

Every event in ``events.json`` becomes a yes/no (``noul``) question that
thaitea/laya-vision answers about the latest camera frame.

Subscribes:
  - sensor_msgs/Image on ``/camera/color/image_raw`` (realsense_ros2_camera)
Publishes:
  - std_msgs/String on ``/jev_events``, JSON with the probability of each
    event, whether it passed ``threshold``, and the inference latency
  - sensor_msgs/Image on ``/jev_crop``, the zoomed region the model sees

``zoom`` crops the frame before inference: 1.0 keeps the full frame, 2.0 keeps
half the width and height. The crop keeps the camera's aspect ratio, is centred
on (``center_x``, ``center_y``) given as fractions of the frame, and is shifted
to stay inside the image.
"""

from __future__ import annotations

import json
import threading
import time

import laya
import rclpy
import transformers
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String

from jev_event_detector.image_utils import (
    default_events_file,
    image_msg_to_pil,
    load_events,
    pil_to_image_msg,
    zoom_crop,
)


def load_questions(events_file: str) -> dict:
    return {
        name: {
            "type": "noul",
            "instructions": f"{event['description']}. Is this happening in the image?",
        }
        for name, event in load_events(events_file).items()
    }


class JevLayaVisionDetector(Node):
    """Run Laya-vision on the latest camera frame at a fixed rate and publish event odds."""

    def __init__(self) -> None:
        super().__init__("jev_laya_vision_detector")

        image_topic = self.declare_parameter("image_topic", "/camera/color/image_raw").value
        events_topic = self.declare_parameter("events_topic", "/jev_events").value
        events_file = self.declare_parameter("events_file", "").value or default_events_file()
        model_id = self.declare_parameter("model_id", "thaitea/laya-vision").value
        model_revision = self.declare_parameter("model_revision", "").value
        device = self.declare_parameter("device", "").value
        rate_hz = self.declare_parameter("rate_hz", 5.0).value
        self._threshold = self.declare_parameter("threshold", 0.5).value
        self._zoom = self.declare_parameter("zoom", 1.0).value
        self._center_x = self.declare_parameter("center_x", 0.5).value
        self._center_y = self.declare_parameter("center_y", 0.5).value
        crop_topic = self.declare_parameter("crop_topic", "/jev_crop").value

        self._questions = load_questions(events_file)
        self.get_logger().info(f"Loaded events {list(self._questions)} from '{events_file}'")

        self.get_logger().info(f"Loading model '{model_id}' ...")
        self._agent = laya.load_vlm(
            model_id, device=device or None, revision=model_revision or None
        )
        self.get_logger().info(f"Model loaded on {self._agent.device}")

        self._lock = threading.Lock()
        self._latest: Image | None = None
        self._fired = {name: False for name in self._questions}
        self._latest_p: dict[str, float] = {}
        self._frames_received = 0
        self._frames_processed = 0
        self._latencies: list[float] = []

        self._pub = self.create_publisher(String, events_topic, QoSProfile(depth=10))
        self._crop_pub = self.create_publisher(Image, crop_topic, qos_profile_sensor_data)
        self.create_subscription(Image, image_topic, self._on_image, qos_profile_sensor_data)
        self.create_timer(
            1.0 / rate_hz, self._on_timer, callback_group=MutuallyExclusiveCallbackGroup()
        )
        self.create_timer(5.0, self._log_stats)
        self.get_logger().info(
            f"Listening on '{image_topic}', publishing on '{events_topic}' at {rate_hz} Hz, "
            f"zoom {self._zoom} at ({self._center_x}, {self._center_y}), crop on '{crop_topic}'"
        )

    def _on_image(self, msg: Image) -> None:
        with self._lock:
            self._latest = msg
            self._frames_received += 1

    def _on_timer(self) -> None:
        with self._lock:
            msg, self._latest = self._latest, None
        if msg is None:
            return

        image = zoom_crop(image_msg_to_pil(msg), self._zoom, self._center_x, self._center_y)
        if self._crop_pub.get_subscription_count() > 0:
            self._crop_pub.publish(pil_to_image_msg(image, msg.header))
        start = time.monotonic()
        answers = self._agent.predict({"image": image}, self._questions)["answers"]
        latency_ms = (time.monotonic() - start) * 1000.0

        events = {}
        for name in self._questions:
            p = float(answers[name]["noul"])
            fired = p >= self._threshold
            if fired and not self._fired[name]:
                self.get_logger().info(f"Event '{name}' fired (p={p:.2f})")
            self._fired[name] = fired
            self._latest_p[name] = p
            events[name] = {"p": p, "fired": fired}

        stamp = msg.header.stamp
        self._pub.publish(String(data=json.dumps({
            "stamp": stamp.sec + stamp.nanosec * 1e-9,
            "frame_id": msg.header.frame_id,
            "events": events,
            "fired": [name for name, e in events.items() if e["fired"]],
            "latency_ms": round(latency_ms, 1),
        })))
        self._frames_processed += 1
        self._latencies.append(latency_ms)

    def _log_stats(self) -> None:
        if self._frames_received == 0:
            self.get_logger().warn("No camera frames received yet")
            return
        mean_latency = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        width = max(len(name) for name in self._questions)
        lines = [
            f"Frames received: {self._frames_received}, processed: {self._frames_processed}, "
            f"skipped: {self._frames_received - self._frames_processed}, "
            f"mean latency: {mean_latency:.0f} ms",
        ]
        for name in self._questions:
            p = self._latest_p.get(name)
            if p is None:
                lines.append(f"  {name:<{width}}  -")
            else:
                marker = "FIRED" if self._fired[name] else ""
                lines.append(f"  {name:<{width}}  p={p:.2f}  {marker}".rstrip())
        self.get_logger().info("\n".join(lines))
        self._latencies.clear()


def main(args=None):
    transformers.logging.set_verbosity_error()
    rclpy.init(args=args)
    node = JevLayaVisionDetector()
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
