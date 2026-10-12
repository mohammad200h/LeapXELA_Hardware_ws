#!/usr/bin/env python3
"""Show the annotated SAM 3 frame and mask in an OpenCV window."""

from __future__ import annotations

import json
import os
import threading

import cv2
import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String

from bounding_box_sam.image_utils import image_msg_to_rgb

MASK_TINT = (113, 204, 46)
MAX_WINDOW_WIDTH = 1600


def _status_line(payload: dict) -> str:
    detections = payload.get("detections") or []
    best = next((item for item in detections if item.get("best")), None)
    score = f"{best['score']:.2f}" if best else "-"
    latency = payload.get("latency_ms", "-")
    prompt = payload.get("prompt", "")
    return f"{prompt}  n={len(detections)}  best={score}  {latency} ms"


def compose_view(
    rgb: np.ndarray,
    mask: np.ndarray | None,
    status: str,
) -> np.ndarray:
    """Build a BGR window image from the annotated frame and optional mask."""
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    if mask is not None and mask.shape[:2] == bgr.shape[:2]:
        tint = np.zeros_like(bgr)
        tint[mask > 0] = MASK_TINT
        overlay = cv2.addWeighted(bgr, 0.55, tint, 0.45, 0.0)
        frame = np.hstack((bgr, overlay))
    else:
        frame = bgr

    if status:
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 36), (0, 0, 0), thickness=-1)
        cv2.putText(
            frame,
            status,
            (12, 26),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    width = frame.shape[1]
    if width > MAX_WINDOW_WIDTH:
        scale = MAX_WINDOW_WIDTH / width
        frame = cv2.resize(
            frame,
            (MAX_WINDOW_WIDTH, max(1, int(frame.shape[0] * scale))),
            interpolation=cv2.INTER_AREA,
        )
    return frame


class ViewerNode(Node):
    """Display ``{topic_prefix}/image`` beside a mask overlay."""

    def __init__(self) -> None:
        super().__init__("bounding_box_sam_viewer")
        topic_prefix = self.declare_parameter("topic_prefix", "/bounding_box_sam").value.rstrip("/")
        self._show_mask = bool(self.declare_parameter("show_mask", True).value)
        self._window = self.declare_parameter("window_name", "bounding_box_sam").value

        self._lock = threading.Lock()
        self._rgb: np.ndarray | None = None
        self._mask: np.ndarray | None = None
        self._status = "waiting for detections"
        self._window_open = False

        image_topic = f"{topic_prefix}/image"
        self.create_subscription(Image, image_topic, self._on_image, qos_profile_sensor_data)
        if self._show_mask:
            self.create_subscription(
                Image, f"{topic_prefix}/mask", self._on_mask, qos_profile_sensor_data
            )
        self.create_subscription(String, f"{topic_prefix}/boxes", self._on_boxes, 10)
        self.get_logger().info(f"Viewing '{image_topic}' in window '{self._window}'")

    def _on_image(self, msg: Image) -> None:
        try:
            rgb = image_msg_to_rgb(msg)
        except ValueError as exc:
            self.get_logger().warn(str(exc), throttle_duration_sec=5.0)
            return
        with self._lock:
            self._rgb = rgb

    def _on_mask(self, msg: Image) -> None:
        try:
            mask = image_msg_to_rgb(msg)[:, :, 0]
        except ValueError as exc:
            self.get_logger().warn(str(exc), throttle_duration_sec=5.0)
            return
        with self._lock:
            self._mask = mask

    def _on_boxes(self, msg: String) -> None:
        try:
            status = _status_line(json.loads(msg.data))
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            self.get_logger().warn(f"Could not read boxes JSON: {exc}", throttle_duration_sec=5.0)
            return
        with self._lock:
            self._status = status

    def render(self) -> bool:
        """Draw the latest frame. Return False when the window is closed."""
        with self._lock:
            rgb = None if self._rgb is None else self._rgb.copy()
            mask = None if self._mask is None else self._mask.copy()
            status = self._status
        if rgb is None:
            return True

        if not self._window_open:
            if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
                raise RuntimeError(
                    "No DISPLAY or WAYLAND_DISPLAY is set, so the viewer cannot open a window."
                )
            cv2.namedWindow(self._window, cv2.WINDOW_NORMAL)
            self._window_open = True

        frame = compose_view(rgb, mask if self._show_mask else None, status)
        cv2.imshow(self._window, frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            return False
        if cv2.getWindowProperty(self._window, cv2.WND_PROP_VISIBLE) < 1:
            return False
        return True

    def close(self) -> None:
        """Destroy the OpenCV window."""
        if self._window_open:
            cv2.destroyWindow(self._window)
            cv2.waitKey(1)
            self._window_open = False


def main(args=None):
    """Spin the viewer on the main thread so OpenCV can refresh the window."""
    rclpy.init(args=args)
    node = ViewerNode()
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.01)
            if not node.render():
                break
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
