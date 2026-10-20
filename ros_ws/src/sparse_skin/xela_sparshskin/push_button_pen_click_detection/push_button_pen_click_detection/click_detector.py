#!/usr/bin/env python3
"""
Listen to the USB mic and report whether a pen click is heard.

Every WAV in ``template_dir`` (saved by click_recorder) is a template. On each
tick the most recent audio is compared with every template by sliding
spectrogram correlation (see ``audio_utils.best_match``). Windows that are not
clearly louder than the background noise floor are skipped.

A match is a click *event*, timed on the audio clock. With ``pair`` on (default)
a pen click is only reported for a press event followed by a release event
``min_gap_s``..``max_gap_s`` later, with no other event within ``quiet_s`` before
the press, between them, or after the release (see ``click_pairing``). That
rejects keyboard typing, which makes bursts of clicks. It is reported ``quiet_s``
after the release.

Publishes:
  - std_msgs/Int32 on ``output_topic`` (default /pen_click): 1 while a click is
    heard (held for ``hold_s`` after it is reported), otherwise 0; every tick
  - std_msgs/Float32 on ``<output_topic>/score``: best template similarity,
    for tuning ``threshold``

ROS parameters:
  - audio_topic (str, default ""): take the audio from this std_msgs/Float32MultiArray topic
    (``audio_publisher``) instead of opening the mic, which only one program can hold; empty
    opens the mic directly
  - device (str, default "08bb:2902"): USB id, name substring or index of the input device
    (only without audio_topic)
  - template_dir (str, default ~/.ros/pen_click_templates)
  - sample_rate (int, default 48000)
  - threshold (float, default 0.7): similarity at or above which a click is detected
  - energy_gate (float, default 3.0): window peak RMS must exceed this times the noise floor
  - hold_s (float, default 0.15): how long 1 is held after a click is reported
  - pair (bool, default true): require a press/release pair; false reports every match
  - min_gap_s, max_gap_s (float, default 0.05, 0.5): allowed press-to-release gap
  - quiet_s (float, default 0.15): silence (no other event) required around the pair
  - rate_hz (float, default 100.0): ticks per second
  - output_topic (str, default /pen_click)
"""

from __future__ import annotations

import collections
import glob
import os
import threading
import time

import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from scipy import signal
from std_msgs.msg import Float32, Float32MultiArray, Int32

from push_button_pen_click_detection import audio_utils
from push_button_pen_click_detection.click_pairing import PressReleasePairer

BLOCK_SIZE = 256
# Smallest audio chunk expected from audio_topic; the window buffer holds enough of them.
MIN_TOPIC_BLOCK = 64
RMS_FRAME_S = 0.005
NOISE_FLOOR_ALPHA = 0.02
# Matches closer than this are one event (the same click seen on several ticks, or
# a click's own rattle a few ms after it).
EVENT_MERGE_S = 0.04
# Templates longer than this probably hold more than one click.
MAX_SINGLE_CLICK_S = 0.15


class ClickDetector(Node):
    def __init__(self) -> None:
        super().__init__("click_detector")
        device_query = self.declare_parameter("device", audio_utils.DEFAULT_DEVICE).value
        template_dir = os.path.expanduser(
            self.declare_parameter("template_dir", audio_utils.DEFAULT_TEMPLATE_DIR).value
        )
        self._sr = int(self.declare_parameter("sample_rate", audio_utils.SAMPLE_RATE).value)
        self._threshold = float(self.declare_parameter("threshold", 0.7).value)
        self._energy_gate = float(self.declare_parameter("energy_gate", 3.0).value)
        self._hold_s = float(self.declare_parameter("hold_s", 0.15).value)
        rate_hz = float(self.declare_parameter("rate_hz", 100.0).value)
        output_topic = self.declare_parameter("output_topic", "/pen_click").value
        audio_topic = self.declare_parameter("audio_topic", "").value
        self._pair = bool(self.declare_parameter("pair", True).value)
        min_gap = float(self.declare_parameter("min_gap_s", 0.05).value)
        max_gap = float(self.declare_parameter("max_gap_s", 0.5).value)
        quiet = float(self.declare_parameter("quiet_s", 0.15).value)
        if self._pair and min_gap < EVENT_MERGE_S:
            self.get_logger().warn(
                f"min_gap_s {min_gap} is below {EVENT_MERGE_S} s; closer events are merged"
            )

        self._templates = self._load_templates(template_dir)
        longest = max(n for _, n in self._templates)
        margin = int(max(0.05, 2.0 / rate_hz) * self._sr)
        self._window_n = longest + margin
        # A click is matched only once its whole template is in the window
        self._pairer = PressReleasePairer(
            min_gap, max_gap, quiet, latency=self._window_n / self._sr + 1.0 / rate_hz
        )

        self._lock = threading.Lock()
        self._blocks: collections.deque[np.ndarray] = collections.deque(
            maxlen=self._window_n // min(BLOCK_SIZE, MIN_TOPIC_BLOCK) + 2
        )
        self._samples_in = 0  # total samples received; the audio clock
        self._noise_floor: float | None = None
        self._last_event_t = -np.inf
        self._last_hit = -np.inf
        self._clicks = 0
        self._rms_frame = int(RMS_FRAME_S * self._sr)
        self._sos = audio_utils.highpass_sos(self._sr)

        self._click_pub = self.create_publisher(Int32, output_topic, 10)
        self._score_pub = self.create_publisher(Float32, output_topic.rstrip("/") + "/score", 10)

        self._stream = None
        if audio_topic:
            # sample_rate must match the audio_publisher's.
            self.create_subscription(Float32MultiArray, audio_topic, self._on_audio_msg, 100)
            source = f"{audio_topic} @ {self._sr} Hz"
        else:
            import sounddevice as sd

            device = audio_utils.find_input_device(device_query)
            self._stream = sd.InputStream(
                device=device, channels=1, samplerate=self._sr, dtype="float32",
                blocksize=BLOCK_SIZE, callback=self._on_audio,
            )
            self._stream.start()
            source = f"[{device}] {sd.query_devices(device)['name']} @ {self._sr} Hz"
        self.create_timer(1.0 / rate_hz, self._tick)
        pairing = (
            f", press/release gap {min_gap}-{max_gap} s, quiet {quiet} s" if self._pair
            else ", no press/release pairing"
        )
        self.get_logger().info(
            f"Listening on {source} with "
            f"{len(self._templates)} template(s) from {template_dir}; "
            f"publishing {output_topic} (threshold {self._threshold}{pairing})"
        )

    def _load_templates(self, template_dir: str) -> list[tuple[np.ndarray, int]]:
        paths = sorted(glob.glob(os.path.join(template_dir, "*.wav")))
        if not paths:
            raise RuntimeError(
                f"No click templates (*.wav) in {template_dir} - "
                "record one with click_recorder first"
            )
        templates = []
        for path in paths:
            x, sr = audio_utils.load_wav(path)
            x = audio_utils.clean(audio_utils.resample(x, sr, self._sr), self._sr)
            feat = audio_utils.features(x, self._sr)
            if feat.shape[1] < 2:
                self.get_logger().warn(f"Skipping {path}: too short")
                continue
            if self._pair and len(x) > MAX_SINGLE_CLICK_S * self._sr:
                self.get_logger().warn(
                    f"{path} is {len(x) / self._sr * 1000:.0f} ms: if it holds both the "
                    "press and the release it matches as one event. Pairing needs "
                    "templates of a single click (~50 ms)"
                )
            templates.append((feat, len(x)))
        if not templates:
            raise RuntimeError(f"All templates in {template_dir} are too short")
        return templates

    def _on_audio(self, indata, frames, time_info, status) -> None:
        with self._lock:
            self._blocks.append(indata[:, 0].copy())
            self._samples_in += frames

    def _on_audio_msg(self, msg: Float32MultiArray) -> None:
        samples = np.asarray(msg.data, dtype=np.float32)
        with self._lock:
            self._blocks.append(samples)
            self._samples_in += len(samples)

    def _tick(self) -> None:
        with self._lock:
            blocks = list(self._blocks)
            samples_in = self._samples_in
        x = np.concatenate(blocks)[-self._window_n:] if blocks else np.zeros(0)
        score, offset = self._score(x) if len(x) == self._window_n else (0.0, 0)

        now = time.monotonic()
        audio_now = samples_in / self._sr
        if score >= self._threshold:
            event_t = (samples_in - self._window_n + offset) / self._sr
            if event_t - self._last_event_t > EVENT_MERGE_S:
                self._last_event_t = event_t
                if self._pair:
                    self._pairer.add_event(event_t)
                else:
                    self._report(now, f"score {score:.2f}")
        if self._pair:
            for press, release in self._pairer.update(audio_now):
                self._report(now, f"press-release gap {(release - press) * 1000:.0f} ms")
        detected = now - self._last_hit <= self._hold_s

        self._click_pub.publish(Int32(data=int(detected)))
        self._score_pub.publish(Float32(data=float(score)))

    def _report(self, now: float, detail: str) -> None:
        if now - self._last_hit > self._hold_s:
            self._clicks += 1
            self.get_logger().info(f"Click #{self._clicks} ({detail})")
        self._last_hit = now

    def _score(self, x: np.ndarray) -> tuple[float, int]:
        """Best template similarity and its start, in samples from the start of ``x``."""
        hp = signal.sosfiltfilt(self._sos, x.astype(np.float64))
        rms = audio_utils.short_time_rms(hp, self._rms_frame)
        # The median ignores a short click inside the window, so it tracks the background
        background = float(np.median(rms))
        if self._noise_floor is None:
            self._noise_floor = background
        else:
            self._noise_floor += NOISE_FLOOR_ALPHA * (background - self._noise_floor)
        if rms.max() < self._energy_gate * max(self._noise_floor, 1e-6):
            return 0.0, 0

        live = audio_utils.features(x, self._sr)
        score, frame = max(audio_utils.best_match(feat, live) for feat, _ in self._templates)
        return score, frame * audio_utils.STFT_HOP

    def destroy_node(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    try:
        node = ClickDetector()
    except Exception as exc:  # noqa: BLE001 - missing templates, mic or PortAudio
        rclpy.logging.get_logger("click_detector").error(str(exc))
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
