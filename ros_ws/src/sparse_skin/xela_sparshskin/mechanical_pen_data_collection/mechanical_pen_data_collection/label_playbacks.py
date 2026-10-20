#!/usr/bin/env python3
"""Label the Compose tab's Play on hand recordings as success (the pen clicked) or failure.

Each recording's microphone WAV (``<demo_dir>/compose_playbacks/<box>_<n>.wav``) is run
through the pen click detector offline (``push_button_pen_click_detection.offline_detector``,
the templates in ``--template-dir``). The run is a success when a click is heard after the
Thumb started (its ``start`` in the recording's timeline; the whole run if it has none).

Pairing is off by default: the robot holds the button ~0.65 s, longer than the detector's
``max_gap_s``, and the release is often too quiet, so a press/release pair is rarely heard;
the click detector the recordings were made with also reported every match.

The label goes next to the recording as ``<box>_<n>.label.json``:

  {"label": "success" | "failure", "clicks": [{"t", "score"}], "thumb_start",
   "live_click_t", "detector": {...}, "templates", "labelled"}

with times in s from the start of the recording (as its ``state_t``). Recordings that already
have a label are skipped unless ``--force``; labels set by hand on the Demonstration tab
(``"manual": true``) are always kept.

  ros2 run mechanical_pen_data_collection label_playbacks
  ros2 run mechanical_pen_data_collection label_playbacks --demo-dir ~/demos --force
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from datetime import datetime

import numpy as np

from mechanical_pen_data_collection.bag_data import default_bag_dir
from mechanical_pen_data_collection.playback_recording import (
    FAILURE,
    SUCCESS,
    PlaybackRecording,
    label_path,
    list_playbacks,
    load_label,
)
from push_button_pen_click_detection import audio_utils
from push_button_pen_click_detection.offline_detector import (
    DetectorSettings,
    detect_clicks,
    load_templates,
)

def default_demo_dir() -> str:
    """``<colcon workspace>/demonstrations``, as ``record_demonstration``'s default."""
    try:
        return os.path.join(os.path.dirname(default_bag_dir()), "demonstrations")
    except Exception:  # package not installed (e.g. run from source)
        return os.path.expanduser("~/demonstrations")


def thumb_start(rec: PlaybackRecording) -> float | None:
    starts = [e["t"] for e in rec.meta.get("timeline", [])
              if e.get("finger") == "th" and e.get("event") == "start"]
    return float(starts[0]) if starts else None


def label_recording(
    rec: PlaybackRecording, templates: dict[int, list], template_dir: str,
    settings: DetectorSettings,
) -> dict | None:
    """The label of ``rec`` (None if it has no audio). ``templates`` caches them per rate."""
    if not (rec.audio and os.path.exists(rec.audio)):
        return None
    x, sr = audio_utils.load_wav(rec.audio)
    if sr not in templates:
        templates[sr] = load_templates(template_dir, sr)
    clicks = [
        {"t": round(c.t + rec.audio_t0, 3), "score": round(c.score, 3)}
        for c in detect_clicks(x, sr, templates[sr], settings)
    ]
    start = thumb_start(rec)
    after = [c for c in clicks if start is None or c["t"] >= start]
    return {
        "label": SUCCESS if after else FAILURE,
        "clicks": clicks,
        "thumb_start": start,
        "live_click_t": [round(float(t), 3) for t in rec.click_t],
        "detector": asdict(settings),
        "templates": os.path.expanduser(template_dir),
        "labelled": datetime.now().isoformat(timespec="seconds"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--demo-dir", default=default_demo_dir(),
                        help="demonstrations folder (default: <workspace>/demonstrations)")
    parser.add_argument("--template-dir", default=audio_utils.DEFAULT_TEMPLATE_DIR)
    parser.add_argument("--threshold", type=float, default=DetectorSettings.threshold)
    parser.add_argument("--energy-gate", type=float, default=DetectorSettings.energy_gate)
    parser.add_argument("--pair", action="store_true",
                        help="count only press/release pairs (as click_detector's pair)")
    parser.add_argument("--force", action="store_true",
                        help="label already labelled ones again (not those labelled by hand)")
    args = parser.parse_args()

    folder = os.path.join(os.path.expanduser(args.demo_dir), "compose_playbacks")
    paths = list_playbacks(folder)
    if not paths:
        print(f"No Play on hand recordings in {folder}")
        return 1
    settings = DetectorSettings(
        threshold=args.threshold, energy_gate=args.energy_gate, pair=args.pair
    )
    templates: dict[int, list] = {}
    counts = {SUCCESS: 0, FAILURE: 0}
    for path in reversed(paths):  # oldest first
        name = os.path.splitext(os.path.basename(path))[0]
        label = load_label(path)
        if args.force and not (label or {}).get("manual"):
            label = None
        kept = label is not None
        if label is None:
            try:
                rec = PlaybackRecording.load(path)
            except Exception as e:  # noqa: BLE001 - a broken file should not stop the rest
                print(f"{name:12} could not load: {e}")
                continue
            label = label_recording(rec, templates, args.template_dir, settings)
            if label is None:
                print(f"{name:12} no audio, not labelled")
                continue
            with open(label_path(path), "w") as f:
                json.dump(label, f, indent=1)
        counts[label["label"]] += 1
        clicks = ", ".join(f"{c['t']:.2f} s ({c['score']:.2f})" for c in label.get("clicks", []))
        live = ", ".join(f"{t:.2f}" for t in label.get("live_click_t", [])) or "-"
        print(f"{name:12} {label['label']:8} clicks: {clicks or '-'}; live: {live}"
              + (" (by hand)" if label.get("manual") else " (kept)" if kept else ""))
    total = counts[SUCCESS] + counts[FAILURE]
    if total:
        print(f"{counts[SUCCESS]}/{total} success ({100.0 * counts[SUCCESS] / total:.0f} %)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
