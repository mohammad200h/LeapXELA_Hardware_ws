#!/usr/bin/env python3
"""
Classify each loud sound on the audio topic with a pretrained model (no training).

The model is chosen on the command line, and the node is named after it:
  ros2 run push_button_pen_click_detection sound_classifier --model clap  # sound_classifier_clap
  ros2 run push_button_pen_click_detection sound_classifier --model ast   # sound_classifier_ast

Needs ``audio_publisher`` running (it holds the mic). For each sound louder than
``gate`` x the noise floor, ``window_s`` seconds around it are classified (see
``pretrained_models``).

Publishes (under the node's name, e.g. /sound_classifier_clap/...):
  - ``~/labels`` std_msgs/String: JSON ``{"model", "level", "labels": [[label, p], ...]}``
    per sound, most likely first
  - ``~/detected`` std_msgs/Int32 per sound: 1 if ``target_label`` is the top label with
    probability >= ``threshold``, else 0

ROS parameters:
  - audio_topic (str, default /audio): std_msgs/Float32MultiArray from audio_publisher
  - sample_rate (int, default 48000): must match audio_publisher's
  - labels (str[], CLAP only): text descriptions to choose between
  - target_label (str, default: the first CLAP label / "Clicking" for AST)
  - threshold (float, default 0.5)
  - gate (float, default 4.0): loudness over the noise floor that counts as a sound
  - window_s (float, default 1.0): seconds of audio classified per sound
  - torch_device (str, default "cuda" if available, else "cpu")
"""

from __future__ import annotations

import argparse
import json
import queue
import sys
import threading

import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.utilities import remove_ros_args
from std_msgs.msg import Float32MultiArray, Int32, String

from push_button_pen_click_detection import audio_utils, pretrained_models

AST_TARGET = "Clicking"


class SoundClassifier(Node):
    def __init__(self, model: str) -> None:
        super().__init__(f"sound_classifier_{model}")
        self._model_name = model
        audio_topic = self.declare_parameter("audio_topic", "/audio").value
        self._sr = int(self.declare_parameter("sample_rate", audio_utils.SAMPLE_RATE).value)
        labels = list(
            self.declare_parameter("labels", pretrained_models.DEFAULT_LABELS).value
        )
        default_target = labels[0] if model == "clap" else AST_TARGET
        self._target = self.declare_parameter("target_label", default_target).value
        self._threshold = float(self.declare_parameter("threshold", 0.5).value)
        self._gate = float(self.declare_parameter("gate", 4.0).value)
        self._window_s = float(self.declare_parameter("window_s", 1.0).value)
        torch_device = self.declare_parameter("torch_device", "").value
        torch_device = torch_device or pretrained_models.default_torch_device()

        self.get_logger().info(f"Loading {model} on {torch_device}...")
        self._model = pretrained_models.create(model, labels, torch_device)

        self._labels_pub = self.create_publisher(String, "~/labels", 10)
        self._detected_pub = self.create_publisher(Int32, "~/detected", 10)
        # The model can take longer than a message; classify on a worker thread
        self._incoming: queue.Queue[np.ndarray] = queue.Queue()
        self.create_subscription(Float32MultiArray, audio_topic, self._on_audio, 100)
        threading.Thread(target=self._run, daemon=True).start()
        self.get_logger().info(
            f"Classifying sounds on {audio_topic} @ {self._sr} Hz; target '{self._target}' "
            f"(threshold {self._threshold}), publishing {self.get_fully_qualified_name()}"
            "/labels and /detected"
        )

    def _on_audio(self, msg: Float32MultiArray) -> None:
        self._incoming.put(np.asarray(msg.data, dtype=np.float32))

    def _run(self) -> None:
        hop = int(pretrained_models.HOP_S * self._sr)
        pending = np.zeros(0, np.float32)

        def next_chunk() -> np.ndarray:
            nonlocal pending
            while len(pending) < hop:
                pending = np.concatenate([pending, self._incoming.get()])
            chunk, pending = pending[:hop], pending[hop:]
            return chunk

        sounds = pretrained_models.loud_windows(next_chunk, self._sr, self._window_s, self._gate)
        for level, window in sounds:
            if not rclpy.ok():
                return
            result = self._model(audio_utils.resample(window, self._sr, self._model.sr))
            top_label, top_p = result[0]
            detected = top_label == self._target and top_p >= self._threshold
            self._labels_pub.publish(String(data=json.dumps({
                "model": self._model_name,
                "level": round(level, 1),
                "labels": [[label, round(p, 3)] for label, p in result],
            })))
            self._detected_pub.publish(Int32(data=int(detected)))
            summary = ", ".join(f"{label}: {p:.2f}" for label, p in result[:3])
            self.get_logger().info(
                f"{'DETECTED ' if detected else ''}sound {level:.0f}x floor -> {summary}"
            )


def main(args=None):
    rclpy.init(args=args)
    parser = argparse.ArgumentParser(description="Classify sounds with a pretrained model")
    parser.add_argument("--model", choices=pretrained_models.MODELS, default="clap")
    cli = parser.parse_args(remove_ros_args(sys.argv if args is None else args)[1:])
    try:
        node = SoundClassifier(cli.model)
    except Exception as exc:  # noqa: BLE001 - model download / torch errors
        rclpy.logging.get_logger(f"sound_classifier_{cli.model}").error(str(exc))
        rclpy.shutdown()
        raise SystemExit(1)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
