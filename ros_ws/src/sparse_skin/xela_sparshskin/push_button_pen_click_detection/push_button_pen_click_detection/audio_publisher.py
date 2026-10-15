#!/usr/bin/env python3
"""
Stream the USB mic on a ROS topic.

The mic (an ALSA hw device) can only be opened by one program at a time, so this node owns it
and the others listen to the topic (``click_detector`` with ``audio_topic``, the record
demonstration GUI's audio recording).

Publishes:
  - std_msgs/Float32MultiArray on ``topic`` (default /audio): consecutive chunks of
    ``block_size`` mono samples in [-1, 1] at ``sample_rate`` Hz
  - std_msgs/String on ``<topic>/info`` (latched, transient local): JSON with
    ``sample_rate``, ``channels``, ``block_size`` and ``device``

ROS parameters:
  - device (str, default "08bb:2902"): USB id, name substring or index of the input device
  - sample_rate (int, default 48000)
  - block_size (int, default 480): samples per message (10 ms at 48 kHz)
  - topic (str, default /audio)
"""

from __future__ import annotations

import json
import queue
import threading

import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from std_msgs.msg import Float32MultiArray, String

from push_button_pen_click_detection import audio_utils


class AudioPublisher(Node):
    def __init__(self) -> None:
        super().__init__("audio_publisher")
        device_query = self.declare_parameter("device", audio_utils.DEFAULT_DEVICE).value
        self._sr = int(self.declare_parameter("sample_rate", audio_utils.SAMPLE_RATE).value)
        block = int(self.declare_parameter("block_size", 480).value)
        topic = self.declare_parameter("topic", "/audio").value

        self._pub = self.create_publisher(Float32MultiArray, topic, 100)
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        info_pub = self.create_publisher(String, topic.rstrip("/") + "/info", latched)

        import sounddevice as sd

        device = audio_utils.find_input_device(device_query)
        name = sd.query_devices(device)["name"]
        info_pub.publish(String(data=json.dumps({
            "sample_rate": self._sr, "channels": 1, "block_size": block, "device": name,
        })))

        # The audio callback only queues; publishing happens on its own thread so a slow
        # publish cannot make the sound card drop samples.
        self._queue: queue.Queue[np.ndarray | None] = queue.Queue()
        self._overflows = 0
        self._thread = threading.Thread(target=self._publish_loop, daemon=True)
        self._thread.start()
        self._stream = sd.InputStream(
            device=device, channels=1, samplerate=self._sr, dtype="float32",
            blocksize=block, callback=self._on_audio,
        )
        self._stream.start()
        self.get_logger().info(
            f"Streaming [{device}] {name} @ {self._sr} Hz on {topic} "
            f"({block} samples per message)"
        )

    def _on_audio(self, indata, frames, time_info, status) -> None:
        if status.input_overflow:
            self._overflows += 1
        self._queue.put(indata[:, 0].copy())

    def _publish_loop(self) -> None:
        while True:
            samples = self._queue.get()
            if samples is None or not rclpy.ok():
                return
            try:
                self._pub.publish(Float32MultiArray(data=samples.tolist()))
            except Exception:  # noqa: BLE001 - shutting down (context gone)
                if not rclpy.ok():
                    return
                raise

    def destroy_node(self) -> None:
        self._stream.stop()
        self._stream.close()
        self._queue.put(None)
        self._thread.join(timeout=1.0)
        if self._overflows:
            self.get_logger().warn(f"{self._overflows} input overflow(s): samples were dropped")
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    try:
        node = AudioPublisher()
    except Exception as exc:  # noqa: BLE001 - missing mic or PortAudio
        rclpy.logging.get_logger("audio_publisher").error(str(exc))
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
