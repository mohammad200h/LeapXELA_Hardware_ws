#!/usr/bin/env python3
"""
Try pretrained sound models (no training) on pen clicks and keyboard sounds.

  - CLAP (laion/larger_clap_general): zero-shot, scores the audio against text
    descriptions (``--labels``)
  - AST (MIT/ast-finetuned-audioset-10-10-0.4593): the top AudioSet classes out of 527

For example:
  # WAV files (e.g. your templates)
  python3 tools/try_pretrained_models.py ~/.ros/pen_click_templates/*.wav
  # Live from the mic: a line per loud sound, until Ctrl+C
  python3 tools/try_pretrained_models.py --live
  # Live while click_detector's launch runs (it holds the mic): read its /audio topic
  python3 tools/try_pretrained_models.py --live --topic /audio
  # The same as a ROS node: ros2 launch push_button_pen_click_detection launch_sound_classifier.py
  # Only CLAP, with your own descriptions
  python3 tools/try_pretrained_models.py --live --model clap --labels "pen click" "typing"

The models are downloaded on first use (~600 MB CLAP, ~350 MB AST) to ~/.cache/huggingface.
Only one program can open the mic: while audio_publisher runs, use ``--topic /audio``.
"""

from __future__ import annotations

import argparse
import queue
import sys

import numpy as np

from push_button_pen_click_detection import audio_utils, pretrained_models
from push_button_pen_click_detection.pretrained_models import Ast, Clap, DEFAULT_LABELS


def describe(models: dict, x: np.ndarray, sr: int) -> str:
    lines = []
    for name, model in models.items():
        result = model(audio_utils.resample(x, sr, model.sr))
        lines.append(
            f"  {name:4} " + "  ".join(f"{label}: {p:.2f}" for label, p in result[:4])
        )
    return "\n".join(lines)


def run_files(models: dict, paths: list[str]) -> None:
    for path in paths:
        x, sr = audio_utils.load_wav(path)
        print(f"{path} ({len(x) / sr * 1000:.0f} ms)\n{describe(models, x, sr)}")


def _mic_source(device_query: str, sr: int, put) -> tuple[object, str]:
    import sounddevice as sd

    device = audio_utils.find_input_device(device_query)
    stream = sd.InputStream(device=device, channels=1, samplerate=sr, dtype="float32",
                            blocksize=int(0.01 * sr), callback=lambda d, *_: put(d[:, 0].copy()))
    stream.start()
    return stream, f"[{device}] {sd.query_devices(device)['name']}"


def _topic_source(topic: str, put) -> tuple[object, str]:
    import threading

    import rclpy
    from std_msgs.msg import Float32MultiArray

    from rclpy.signals import SignalHandlerOptions

    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)  # keep Ctrl+C for us
    node = rclpy.create_node("try_pretrained_models")
    node.create_subscription(
        Float32MultiArray, topic, lambda m: put(np.asarray(m.data, np.float32)), 100
    )
    threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()
    return node, f"{topic} (needs audio_publisher at {audio_utils.SAMPLE_RATE} Hz)"


def run_live(models: dict, device_query: str, topic: str, window_s: float, gate: float) -> None:
    sr = audio_utils.SAMPLE_RATE
    incoming: queue.Queue[np.ndarray] = queue.Queue()
    if topic:
        _source, name = _topic_source(topic, incoming.put)
    else:
        _source, name = _mic_source(device_query, sr, incoming.put)

    hop = int(pretrained_models.HOP_S * sr)
    pending = np.zeros(0, np.float32)

    def next_chunk() -> np.ndarray:
        nonlocal pending
        while len(pending) < hop:
            pending = np.concatenate([pending, incoming.get()])
        chunk, pending = pending[:hop], pending[hop:]
        return chunk

    print(f"Listening on {name}; Ctrl+C to stop", flush=True)
    for level, window in pretrained_models.loud_windows(next_chunk, sr, window_s, gate):
        print(f"sound (level {level:.0f}x floor)")
        print(describe(models, window, sr), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("wavs", nargs="*", help="WAV files to classify")
    parser.add_argument("--live", action="store_true", help="classify sounds from the mic")
    parser.add_argument("--model", choices=["clap", "ast", "both"], default="both")
    parser.add_argument("--labels", nargs="+", default=DEFAULT_LABELS,
                        help="CLAP text descriptions to choose between")
    parser.add_argument("--device", default=audio_utils.DEFAULT_DEVICE,
                        help="mic: USB id, name substring or index")
    parser.add_argument("--topic", default="",
                        help="live: read audio_publisher's topic (e.g. /audio) instead of the mic")
    parser.add_argument("--window", type=float, default=1.0,
                        help="live: seconds of audio classified around each sound")
    parser.add_argument("--gate", type=float, default=4.0,
                        help="live: loudness over the noise floor that counts as a sound")
    args = parser.parse_args()
    if not args.wavs and not args.live:
        parser.error("give WAV files or --live")

    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    models = {}
    if args.model in ("clap", "both"):
        models["CLAP"] = Clap(args.labels, device)
    if args.model in ("ast", "both"):
        models["AST"] = Ast(device)
    try:
        if args.wavs:
            run_files(models, args.wavs)
        if args.live:
            run_live(models, args.device, args.topic, args.window, args.gate)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
