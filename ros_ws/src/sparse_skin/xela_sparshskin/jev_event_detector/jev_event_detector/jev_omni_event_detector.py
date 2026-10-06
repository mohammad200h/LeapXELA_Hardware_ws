#!/usr/bin/env python3
"""Detect pen events from short camera clips with the Jev-Omni model.

The node keeps a rolling window of ``num_frames`` camera frames, sampled at
``frame_rate_hz``, and asks ldov/Jev-Omni one Yes/No question per event in
``events.json`` about that clip. Unlike the Laya-vision detector, which judges
a single frame, the model sees motion across the window.

Subscribes:
  - sensor_msgs/Image on ``/camera/color/image_raw`` (realsense_ros2_camera)
Publishes:
  - std_msgs/String on ``/jev_omni_events``, JSON with the probability of each
    event, whether it passed ``threshold``, the window length and the latency
  - sensor_msgs/Image on ``/jev_omni_crop``, a grid of the frames in the window

Frames are cropped with ``zoom`` / ``center_x`` / ``center_y`` exactly as in
the Laya-vision detector.
"""

from __future__ import annotations

import collections
import inspect
import json
import math
import sys
import threading
import time
from pathlib import Path

import rclpy
import torch
import transformers
from huggingface_hub import snapshot_download
from PIL import Image as PILImage
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

MODEL_FILES = [
    "config.json", "generation_config.json", "model*.safetensors*", "processor_config.json",
    "tokenizer.json", "tokenizer_config.json", "chat_template.jinja",
    "decision_config.json", "head.pt", "jev_omni.py",
]
OPTIONS = ["Yes", "No"]
GRID_TILE_WIDTH = 320


class JevOmniClassifier:
    """Jev-Omni over a list of frames, split across the available GPUs.

    The reference loader in the model repo (``jev_omni.py``) places the whole
    24 GB model on one GPU, which does not fit a 24 GB card, so the model is
    loaded here with ``device_map`` and the repo's prompt and decision head
    are reused.
    """

    def __init__(self, model_id: str, revision: str | None, device_map: str) -> None:
        path = Path(snapshot_download(model_id, revision=revision, allow_patterns=MODEL_FILES))
        sys.path.insert(0, str(path))
        import jev_omni

        self._prompt = jev_omni._prompt
        config = transformers.AutoConfig.from_pretrained(path)
        self.model = getattr(transformers, config.architectures[0]).from_pretrained(
            path, dtype=torch.bfloat16, device_map=device_map
        ).eval()
        self.processor = transformers.AutoProcessor.from_pretrained(path)
        self.device = self.model.get_input_embeddings().weight.device

        decision = json.loads((path / "decision_config.json").read_text())
        self.head = jev_omni._Head256(decision["hidden_size"]).to(self.device).eval()
        self.head.load_state_dict(
            torch.load(path / "head.pt", map_location=self.device, weights_only=True)
        )

        self._hidden: torch.Tensor | None = None
        _, decoder = jev_omni._find_backbone(self.model)
        decoder.register_forward_hook(self._capture)
        self._extra = (
            {"logits_to_keep": 1}
            if "logits_to_keep" in inspect.signature(self.model.forward).parameters else {}
        )

    def _capture(self, _module, _args, out) -> None:
        hidden = out.last_hidden_state if hasattr(out, "last_hidden_state") else out[0]
        self._hidden = hidden[:, -1].float().to(self.device)

    @torch.inference_mode()
    def predict(self, frames: list, state: str, question: str, options: list) -> dict:
        content = [{"type": "image", "image": frame} for frame in frames]
        content.append({"type": "text", "text": self._prompt(state, question, options)})
        inputs = self.processor.apply_chat_template(
            [{"role": "user", "content": content}], add_generation_prompt=True,
            tokenize=True, return_dict=True, return_tensors="pt", enable_thinking=False,
        )
        inputs = {
            k: v.to(self.device, dtype=torch.bfloat16) if torch.is_floating_point(v)
            else v.to(self.device)
            for k, v in inputs.items()
        }
        self._hidden = None
        with torch.autocast("cuda", dtype=torch.bfloat16):
            self.model(**inputs, use_cache=False, **self._extra)
            counts = torch.tensor([len(options)], device=self.device)
            probs = self.head(self._hidden, counts)[0, : len(options)].softmax(-1)
        return dict(zip(options, probs.float().cpu().tolist()))


def frame_grid(frames: list) -> PILImage.Image:
    columns = min(len(frames), 4)
    rows = math.ceil(len(frames) / columns)
    tile_h = round(GRID_TILE_WIDTH * frames[0].height / frames[0].width)
    grid = PILImage.new("RGB", (columns * GRID_TILE_WIDTH, rows * tile_h))
    for i, frame in enumerate(frames):
        tile = frame.resize((GRID_TILE_WIDTH, tile_h))
        grid.paste(tile, ((i % columns) * GRID_TILE_WIDTH, (i // columns) * tile_h))
    return grid


class JevOmniEventDetector(Node):
    """Run Jev-Omni on a rolling window of camera frames and publish event odds."""

    def __init__(self) -> None:
        super().__init__("jev_omni_event_detector")

        image_topic = self.declare_parameter("image_topic", "/camera/color/image_raw").value
        events_topic = self.declare_parameter("events_topic", "/jev_omni_events").value
        crop_topic = self.declare_parameter("crop_topic", "/jev_omni_crop").value
        events_file = self.declare_parameter("events_file", "").value or default_events_file()
        model_id = self.declare_parameter("model_id", "ldov/Jev-Omni").value
        model_revision = self.declare_parameter("model_revision", "").value
        device_map = self.declare_parameter("device_map", "auto").value
        self._num_frames = self.declare_parameter("num_frames", 8).value
        frame_rate_hz = self.declare_parameter("frame_rate_hz", 4.0).value
        rate_hz = self.declare_parameter("rate_hz", 1.0).value
        self._threshold = self.declare_parameter("threshold", 0.5).value
        self._zoom = self.declare_parameter("zoom", 1.0).value
        self._center_x = self.declare_parameter("center_x", 0.5).value
        self._center_y = self.declare_parameter("center_y", 0.5).value

        if not 1 <= self._num_frames <= 16:
            raise ValueError("num_frames must be between 1 and 16 (Jev-Omni's video limit)")
        self._frame_period = 1.0 / frame_rate_hz

        self._questions = {
            name: f'Is the following true in this video: "{event["description"]}"?'
            for name, event in load_events(events_file).items()
        }
        self.get_logger().info(f"Loaded events {list(self._questions)} from '{events_file}'")

        self.get_logger().info(f"Loading model '{model_id}' (about 24 GB) ...")
        self._classifier = JevOmniClassifier(model_id, model_revision or None, device_map)
        devices = sorted({str(p.device) for p in self._classifier.model.parameters()})
        self.get_logger().info(f"Model loaded on {', '.join(devices)}")

        self._lock = threading.Lock()
        self._window: collections.deque = collections.deque(maxlen=self._num_frames)
        self._last_sample = 0.0
        self._fired = {name: False for name in self._questions}
        self._latest_p: dict[str, float] = {}
        self._frames_received = 0
        self._windows_processed = 0
        self._latencies: list[float] = []

        self._pub = self.create_publisher(String, events_topic, QoSProfile(depth=10))
        self._crop_pub = self.create_publisher(Image, crop_topic, qos_profile_sensor_data)
        self.create_subscription(Image, image_topic, self._on_image, qos_profile_sensor_data)
        self.create_timer(
            1.0 / rate_hz, self._on_timer, callback_group=MutuallyExclusiveCallbackGroup()
        )
        self.create_timer(10.0, self._log_stats)
        self.get_logger().info(
            f"Listening on '{image_topic}', publishing on '{events_topic}' at up to "
            f"{rate_hz} Hz; window of {self._num_frames} frames at {frame_rate_hz} Hz "
            f"({self._num_frames * self._frame_period:.1f} s), zoom {self._zoom} at "
            f"({self._center_x}, {self._center_y}), frame grid on '{crop_topic}'"
        )

    def _on_image(self, msg: Image) -> None:
        self._frames_received += 1
        now = time.monotonic()
        if now - self._last_sample < self._frame_period:
            return
        self._last_sample = now
        frame = zoom_crop(image_msg_to_pil(msg), self._zoom, self._center_x, self._center_y)
        with self._lock:
            self._window.append((now, frame, msg.header))

    def _on_timer(self) -> None:
        with self._lock:
            window = list(self._window)
        if len(window) < self._num_frames:
            return

        frames = [frame for _, frame, _ in window]
        header = window[-1][2]
        span_s = window[-1][0] - window[0][0]
        if self._crop_pub.get_subscription_count() > 0:
            self._crop_pub.publish(pil_to_image_msg(frame_grid(frames), header))

        state = (
            f"These are {len(frames)} video frames in time order, covering the last "
            f"{span_s:.1f} seconds of a camera watching a robot hand and a pen."
        )
        start = time.monotonic()
        events = {}
        for name, question in self._questions.items():
            p = self._classifier.predict(frames, state, question, OPTIONS)["Yes"]
            fired = p >= self._threshold
            if fired and not self._fired[name]:
                self.get_logger().info(f"Event '{name}' fired (p={p:.2f})")
            self._fired[name] = fired
            self._latest_p[name] = p
            events[name] = {"p": p, "fired": fired}
        latency_ms = (time.monotonic() - start) * 1000.0

        stamp = header.stamp
        self._pub.publish(String(data=json.dumps({
            "stamp": stamp.sec + stamp.nanosec * 1e-9,
            "frame_id": header.frame_id,
            "num_frames": len(frames),
            "window_s": round(span_s, 2),
            "events": events,
            "fired": [name for name, e in events.items() if e["fired"]],
            "latency_ms": round(latency_ms, 1),
        })))
        self._windows_processed += 1
        self._latencies.append(latency_ms)

    def _log_stats(self) -> None:
        if self._frames_received == 0:
            self.get_logger().warn("No camera frames received yet")
            return
        mean_latency = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        width = max(len(name) for name in self._questions)
        lines = [
            f"Frames received: {self._frames_received}, windows processed: "
            f"{self._windows_processed}, mean latency: {mean_latency:.0f} ms",
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
    node = JevOmniEventDetector()
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
