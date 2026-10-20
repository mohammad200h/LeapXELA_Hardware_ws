"""
Pen clicks in a recorded WAV, found the way ``click_detector`` finds them live.

The recording is replayed tick by tick (``rate_hz``): each tick scores the most recent
window against every template (``audio_utils.best_match``), skips windows not louder than
``energy_gate`` x the running noise floor, merges matches closer than ``EVENT_MERGE_S`` into
one event and, with ``pair``, keeps only isolated press/release pairs (``click_pairing``).
No node needs to run:

  python3 -m push_button_pen_click_detection.offline_detector recording.wav
"""

from __future__ import annotations

import argparse
import glob
import os
from dataclasses import dataclass

import numpy as np
from scipy import signal

from push_button_pen_click_detection import audio_utils
from push_button_pen_click_detection.click_detector import (
    EVENT_MERGE_S,
    NOISE_FLOOR_ALPHA,
    RMS_FRAME_S,
)
from push_button_pen_click_detection.click_pairing import PressReleasePairer


@dataclass
class DetectorSettings:
    """``click_detector``'s parameters (same defaults as its launch file)."""

    threshold: float = 0.7
    energy_gate: float = 3.0
    pair: bool = True
    min_gap_s: float = 0.05
    max_gap_s: float = 0.5
    quiet_s: float = 0.15
    rate_hz: float = 100.0


@dataclass
class Click:
    t: float  # s from the start of the recording: the press (or the match without pairing)
    release: float | None  # s, with pairing
    score: float  # best template similarity of the press


def load_templates(template_dir: str, sr: int) -> list[tuple[np.ndarray, int]]:
    """(features, length in samples) of every WAV in ``template_dir`` at ``sr``."""
    templates = []
    for path in sorted(glob.glob(os.path.join(os.path.expanduser(template_dir), "*.wav"))):
        x, rate = audio_utils.load_wav(path)
        x = audio_utils.clean(audio_utils.resample(x, rate, sr), sr)
        feat = audio_utils.features(x, sr)
        if feat.shape[1] >= 2:
            templates.append((feat, len(x)))
    if not templates:
        raise RuntimeError(f"No usable click templates (*.wav) in {template_dir}")
    return templates


def detect_clicks(
    x: np.ndarray, sr: int, templates: list[tuple[np.ndarray, int]],
    settings: DetectorSettings | None = None,
) -> list[Click]:
    """Pen clicks in the mono samples ``x`` (at ``sr``), as ``click_detector`` reports them."""
    s = settings or DetectorSettings()
    longest = max(n for _, n in templates)
    window_n = longest + int(max(0.05, 2.0 / s.rate_hz) * sr)
    step = max(1, int(round(sr / s.rate_hz)))
    pairer = PressReleasePairer(
        s.min_gap_s, s.max_gap_s, s.quiet_s, latency=window_n / sr + 1.0 / s.rate_hz
    )
    sos = audio_utils.highpass_sos(sr)
    frame = int(RMS_FRAME_S * sr)
    noise_floor = None
    last_event = -np.inf
    scores: dict[float, float] = {}  # event time -> score
    clicks: list[Click] = []

    def report(pairs) -> None:
        for press, release in pairs:
            clicks.append(Click(t=press, release=release, score=scores.get(press, 0.0)))

    for end in range(window_n, len(x) + 1, step):
        window = x[end - window_n:end]
        rms = audio_utils.short_time_rms(
            signal.sosfiltfilt(sos, window.astype(np.float64)), frame
        )
        background = float(np.median(rms))
        noise_floor = background if noise_floor is None else (
            noise_floor + NOISE_FLOOR_ALPHA * (background - noise_floor)
        )
        if rms.max() >= s.energy_gate * max(noise_floor, 1e-6):
            live = audio_utils.features(window, sr)
            score, offset = max(audio_utils.best_match(feat, live) for feat, _ in templates)
            if score >= s.threshold:
                event_t = (end - window_n + offset * audio_utils.STFT_HOP) / sr
                if event_t - last_event > EVENT_MERGE_S:
                    last_event = event_t
                    if s.pair:
                        scores[event_t] = score
                        pairer.add_event(event_t)
                    else:
                        clicks.append(Click(t=event_t, release=None, score=score))
        if s.pair:
            report(pairer.update(end / sr))
    if s.pair:  # the recording ended: decide what is still pending
        report(pairer.update(len(x) / sr + s.max_gap_s + s.quiet_s + pairer.latency + 1.0))
    return clicks


def main() -> None:
    parser = argparse.ArgumentParser(description="Pen clicks in recorded WAV files")
    parser.add_argument("wavs", nargs="+")
    parser.add_argument("--template-dir", default=audio_utils.DEFAULT_TEMPLATE_DIR)
    parser.add_argument("--threshold", type=float, default=DetectorSettings.threshold)
    parser.add_argument("--no-pair", action="store_true")
    args = parser.parse_args()
    settings = DetectorSettings(threshold=args.threshold, pair=not args.no_pair)
    cache: dict[int, list] = {}
    for path in args.wavs:
        x, sr = audio_utils.load_wav(path)
        templates = cache.setdefault(sr, load_templates(args.template_dir, sr))
        clicks = detect_clicks(x, sr, templates, settings)
        found = ", ".join(f"{c.t:.2f} s ({c.score:.2f})" for c in clicks) or "no click"
        print(f"{path}: {found}")


if __name__ == "__main__":
    main()
