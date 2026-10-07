#!/usr/bin/env python3
"""Crop the camera feed to the region each task question needs, CropVLM style.

Runs the box stage of CropVLM (Carvalho et al., CVPRW 2026) with the grounding
model CropVLM used to make its seed boxes, Qwen2.5-VL. CropVLM's own SmolVLM
weights are not published, and the base SmolVLM cannot output boxes. Qwen is
asked CropVLM's seed prompt, "Outline the region in the image that would help
answer the following question: {task} ... 'bbox_2d' ...", and answers in pixels
of its resized input. The box is converted to percent of the camera frame and,
if ``expand`` is set, grown by CropVLM's area-percentile factors (45x for the
smallest boxes down to 1x) so small parts keep their surroundings. All tasks in
``crop.json`` are answered in one batched call per frame. Frames with an
invalid box publish the full frame.

Subscribes:
  - sensor_msgs/Image on ``/camera/color/image_raw`` (realsense_ros2_camera)
Publishes:
  - sensor_msgs/Image on ``{topic_prefix}/{object}/task_{i}``, the crop for task ``i``
  - std_msgs/String on ``{topic_prefix}/boxes``, JSON with every box and the latency
"""

from __future__ import annotations

import json
import re
import threading
import time

import rclpy
import torch
import transformers
from PIL import Image as PILImage
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String
from transformers import AutoModelForImageTextToText, AutoProcessor

from jev_event_detector.image_utils import (
    default_crop_file,
    image_msg_to_pil,
    pil_to_image_msg,
)

DEFAULT_MODEL = "Qwen/Qwen2.5-VL-3B-Instruct"
CROP_PROMPT = (
    "Outline the region in the image that would help answer the following question: "
    "{question}\nOutput the coordinates in JSON format with a 'bbox_2d' field "
    "containing [x1, y1, x2, y2]."
)
BOX = re.compile(r"\[\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\]")
# CropVLM Table 2: relative-area upper bounds and the area factor applied below them.
EXPANSION = [(0.0016, 45.0), (0.0038, 10.0), (0.0091, 4.0), (0.0351, 2.0)]


def load_tasks(crop_file: str) -> list[tuple[str, int, str]]:
    with open(crop_file) as f:
        objects = json.load(f)
    return [
        (name, index, question)
        for name, entry in objects.items()
        for index, question in enumerate(entry["Tasks"])
    ]


def parse_bbox(text: str, width: float, height: float) -> list[float] | None:
    """Return the first box in ``text`` (pixels of a ``width`` x ``height`` image) in percent."""
    match = BOX.search(text)
    if match is None:
        return None
    x1, y1, x2, y2 = (float(v) for v in match.groups())
    x1, x2 = max(0.0, x1) / width * 100, min(width, x2) / width * 100
    y1, y2 = max(0.0, y1) / height * 100, min(height, y2) / height * 100
    if x2 <= x1 or y2 <= y1:
        return None
    return [x1, y1, x2, y2]


def expand_bbox(bbox: list[float]) -> list[float]:
    """Grow a percent box about its centre by CropVLM's factor, shifted to stay in frame."""
    x1, y1, x2, y2 = bbox
    area = (x2 - x1) * (y2 - y1) / 10000
    factor = next((f for bound, f in EXPANSION if area < bound), 1.0)
    scale = factor ** 0.5
    w, h = min((x2 - x1) * scale, 100.0), min((y2 - y1) * scale, 100.0)
    left = min(max((x1 + x2) / 2 - w / 2, 0.0), 100.0 - w)
    top = min(max((y1 + y2) / 2 - h / 2, 0.0), 100.0 - h)
    return [left, top, left + w, top + h]


def crop_pct(image: PILImage.Image, bbox: list[float]) -> PILImage.Image:
    width, height = image.size
    x1, y1, x2, y2 = bbox
    left, top = int(x1 * width / 100), int(y1 * height / 100)
    right = max(round(x2 * width / 100), left + 1)
    bottom = max(round(y2 * height / 100), top + 1)
    return image.crop((left, top, right, bottom))


class CropVlm(Node):
    """Predict a box per task on the latest camera frame and publish the crops."""

    def __init__(self) -> None:
        super().__init__("crop_vlm")

        image_topic = self.declare_parameter("image_topic", "/camera/color/image_raw").value
        crop_file = self.declare_parameter("crop_file", "").value or default_crop_file()
        model_path = self.declare_parameter("model_path", DEFAULT_MODEL).value
        max_pixels = self.declare_parameter("max_pixels", 1280 * 28 * 28).value
        device = self.declare_parameter("device", "").value
        rate_hz = self.declare_parameter("rate_hz", 1.0).value
        topic_prefix = self.declare_parameter("topic_prefix", "/crop_vlm").value.rstrip("/")
        self._expand = self.declare_parameter("expand", True).value
        self._max_new_tokens = self.declare_parameter("max_new_tokens", 64).value

        self._tasks = load_tasks(crop_file)
        self.get_logger().info(f"Loaded {len(self._tasks)} tasks from '{crop_file}'")

        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        dtype = torch.bfloat16 if self._device.startswith("cuda") else torch.float32
        self.get_logger().info(f"Loading model '{model_path}' on {self._device} ...")
        self._processor = AutoProcessor.from_pretrained(model_path, max_pixels=max_pixels)
        self._processor.tokenizer.padding_side = "left"
        self._model = AutoModelForImageTextToText.from_pretrained(
            model_path, dtype=dtype, attn_implementation="sdpa"
        ).to(self._device).eval()
        self._patch_size = self._processor.image_processor.patch_size
        self._prompts = [
            self._processor.apply_chat_template(
                [{
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": CROP_PROMPT.format(question=question)},
                    ],
                }],
                add_generation_prompt=True,
            )
            for _, _, question in self._tasks
        ]
        self.get_logger().info("Model loaded")

        self._lock = threading.Lock()
        self._latest: Image | None = None
        self._frames_received = 0
        self._frames_processed = 0
        self._boxes_total = 0
        self._boxes_valid = 0
        self._latencies: list[float] = []

        self._boxes_pub = self.create_publisher(
            String, f"{topic_prefix}/boxes", QoSProfile(depth=10)
        )
        self._crop_pubs = [
            self.create_publisher(
                Image, f"{topic_prefix}/{name}/task_{index}", qos_profile_sensor_data
            )
            for name, index, _ in self._tasks
        ]
        self.create_subscription(Image, image_topic, self._on_image, qos_profile_sensor_data)
        self.create_timer(
            1.0 / rate_hz, self._on_timer, callback_group=MutuallyExclusiveCallbackGroup()
        )
        self.create_timer(5.0, self._log_stats)
        self.get_logger().info(
            f"Listening on '{image_topic}', publishing crops under '{topic_prefix}' at {rate_hz} Hz"
        )

    def _on_image(self, msg: Image) -> None:
        with self._lock:
            self._latest = msg
            self._frames_received += 1

    def _predict_boxes(self, image: PILImage.Image) -> tuple[list[str], float, float]:
        """Return the raw answer per task and the size of the image Qwen actually saw."""
        inputs = self._processor(
            text=self._prompts,
            images=[image] * len(self._prompts),
            padding=True,
            return_tensors="pt",
        ).to(self._device)
        with torch.no_grad():
            generated = self._model.generate(
                **inputs, max_new_tokens=self._max_new_tokens, do_sample=False
            )
        new_tokens = generated[:, inputs["input_ids"].shape[1]:]
        raws = self._processor.batch_decode(new_tokens, skip_special_tokens=True)
        _, grid_h, grid_w = inputs["image_grid_thw"][0].tolist()
        return [r.strip() for r in raws], grid_w * self._patch_size, grid_h * self._patch_size

    def _on_timer(self) -> None:
        with self._lock:
            msg, self._latest = self._latest, None
        if msg is None:
            return

        image = image_msg_to_pil(msg)
        start = time.monotonic()
        raws, seen_w, seen_h = self._predict_boxes(image)
        latency_ms = (time.monotonic() - start) * 1000.0

        crops = []
        for (name, index, question), pub, raw in zip(self._tasks, self._crop_pubs, raws):
            bbox = parse_bbox(raw, seen_w, seen_h)
            self._boxes_total += 1
            if bbox is None:
                self.get_logger().warn(
                    f"Invalid box for '{name}' task {index}: {raw!r}, publishing full frame",
                    throttle_duration_sec=5.0,
                )
                crop = image
            else:
                self._boxes_valid += 1
                if self._expand:
                    bbox = expand_bbox(bbox)
                crop = crop_pct(image, bbox)
            if pub.get_subscription_count() > 0:
                pub.publish(pil_to_image_msg(crop, msg.header))
            crops.append({
                "object": name,
                "task": index,
                "question": question,
                "raw": raw,
                "bbox_pct": [round(v, 2) for v in bbox] if bbox else None,
                "valid": bbox is not None,
            })

        stamp = msg.header.stamp
        self._boxes_pub.publish(String(data=json.dumps({
            "stamp": stamp.sec + stamp.nanosec * 1e-9,
            "frame_id": msg.header.frame_id,
            "latency_ms": round(latency_ms, 1),
            "crops": crops,
        })))
        self._frames_processed += 1
        self._latencies.append(latency_ms)

    def _log_stats(self) -> None:
        if self._frames_received == 0:
            self.get_logger().warn("No camera frames received yet")
            return
        mean_latency = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        valid = self._boxes_valid / self._boxes_total if self._boxes_total else 0.0
        self.get_logger().info(
            f"Frames received: {self._frames_received}, processed: {self._frames_processed}, "
            f"mean latency: {mean_latency:.0f} ms, valid boxes: {valid:.0%} "
            f"({self._boxes_valid}/{self._boxes_total})"
        )
        self._latencies.clear()


def main(args=None):
    transformers.logging.set_verbosity_error()
    rclpy.init(args=args)
    node = CropVlm()
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
