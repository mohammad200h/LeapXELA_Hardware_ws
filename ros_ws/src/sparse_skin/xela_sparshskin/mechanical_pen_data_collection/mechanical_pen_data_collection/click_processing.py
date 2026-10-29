"""Find the Thumb's pen click in Play on hand recordings from clicks marked by hand.

The Processing tab's Process click: every ``Thumb_is_clicking_the_pen`` event marked on a
recording (and confirmed) cuts its span out of that recording's microphone WAV as a click
sample, ``MAX_SAMPLES`` at most (``pick_marks``: each sample costs about the same search time
again). The pen click detector (``detect``: click_detector's ``~/detect`` service, without
press / release pairing) is given those samples and searches each successful recording that
has no such event yet, between the Thumb's ``start`` and ``finished`` / ``stopped`` (its timeline). A
run usually holds two click-like sounds, the click and another one ~4-5 s later as the Thumb
lets go, which can match a little better: the click is the earliest detection scoring
within ``SCORE_MARGIN`` of the best one. It is added as a ``Thumb_is_clicking_the_pen`` event
(as long as the marked ones' median), with ``params["to_be_confirmed"]`` set, and with
``terminal`` and ``success`` at its end (``with_end_events``; to be confirmed with it,
``params["with"]``), and what was found is saved in the label file as ``process_click``; recordings with ``process_click`` are
not searched again.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Callable

import numpy as np

from mechanical_pen_data_collection.playback_recording import load_label, update_label
from push_button_pen_click_detection import audio_utils

CLICK_EVENT = "Thumb_is_clicking_the_pen"
TO_BE_CONFIRMED = "to_be_confirmed"
# Events added at the end of a click event (once per recording), and the param naming the
# event they were added with.
CLICK_END_EVENTS = ("terminal", "success")
WITH = "with"
# The click is the earliest detection scoring at least the best one's score minus this.
SCORE_MARGIN = 0.1
# The most marked clicks used as samples: each is compared at every loud moment of the audio,
# so the search takes about as much longer per sample.
MAX_SAMPLES = 10
# The rate the samples and the searched audio are sent at.
SAMPLE_RATE = audio_utils.SAMPLE_RATE

# (click samples, audio to search, their rate) -> [(s from the start of the audio, score)]
Detect = Callable[[list[np.ndarray], np.ndarray, int], list[tuple[float, float]]]


def _recording_info(path: str) -> tuple[str, float, dict]:
    """(WAV path, audio_t0, meta) of a Play on hand recording; only the small entries are
    read."""
    with np.load(path, allow_pickle=False) as data:
        return str(data["audio"]), float(data["audio_t0"]), json.loads(str(data["meta"]))


def _thumb_span(meta: dict) -> tuple[float, float | None]:
    """Recording times (s) the Thumb started and finished / stopped (None: the end)."""
    timeline = [e for e in meta.get("timeline", []) if e.get("finger") == "th"]
    start = next((e["t"] for e in timeline if e["event"] == "start"), 0.0)
    end = next((e["t"] for e in timeline if e["event"] in ("finished", "stopped")), None)
    return float(start), end


def click_events(label: dict | None, confirmed: bool = True) -> list[dict]:
    """The ``Thumb_is_clicking_the_pen`` events of a label file (only those not to be
    confirmed, with ``confirmed``)."""
    return [
        e for e in (label or {}).get("events", [])
        if e.get("name") == CLICK_EVENT and e.get("end") is not None
        and not (confirmed and (e.get("params") or {}).get(TO_BE_CONFIRMED))
    ]


def marked_clicks(paths: list[str]) -> list[tuple[str, float, float]]:
    """(recording, start, end) of every confirmed click event of ``paths``."""
    return [
        (path, e["t"], e["end"])
        for path in paths for e in click_events(load_label(path))
    ]


def with_end_events(
    events: list[dict], click: dict, types: dict, params: dict | None = None
) -> list[dict]:
    """``events`` (dicts as saved) plus ``CLICK_END_EVENTS`` at the end of the click event
    ``click``, those the recording has none of yet; ``types`` maps event names to their
    events.json type, ``params`` is given to each."""
    out = list(events)
    for name in CLICK_END_EVENTS:
        if not any(e.get("name") == name for e in out):
            out.append({
                "t": click["end"], "name": name, "type": types.get(name, ""),
                "added": datetime.now().timestamp(), "end": None,
                "params": {WITH: CLICK_EVENT, **(params or {})},
            })
    return out


def pick_marks(
    marks: list[tuple[str, float, float]], n: int = MAX_SAMPLES
) -> list[tuple[str, float, float]]:
    """At most ``n`` of ``marks``, spread evenly over them (in the order of their recordings,
    so different sessions are used)."""
    if len(marks) <= n:
        return list(marks)
    return [marks[i] for i in np.linspace(0, len(marks) - 1, n).round().astype(int)]


def click_samples(marks: list[tuple[str, float, float]], sr: int) -> list[np.ndarray]:
    """The audio (at ``sr``) of the marked spans, the detector's click samples."""
    samples = []
    for path, start, end in marks:
        wav, t0, _ = _recording_info(path)
        x, rate = audio_utils.load_wav(wav)
        clip = x[max(int((start - t0) * rate), 0):max(int((end - t0) * rate), 0)]
        if len(clip):
            samples.append(audio_utils.resample(clip, rate, sr))
    return samples


def find_click(
    path: str, samples: list[np.ndarray], sr: int, detect: Detect
) -> tuple[dict | None, list[dict]]:
    """The click found in a recording ({"t", "score"} in recording time, None if none) and
    every detection while the Thumb played."""
    wav, t0, meta = _recording_info(path)
    x, rate = audio_utils.load_wav(wav)
    x = audio_utils.resample(x, rate, sr)
    start, end = _thumb_span(meta)
    a = max(int((start - t0) * sr), 0)
    b = len(x) if end is None else min(max(int((end - t0) * sr), a), len(x))
    found = [
        {"t": round(t + a / sr + t0, 3), "score": round(score, 3)}
        for t, score in detect(samples, x[a:b], sr)
    ]
    if not found:
        return None, []
    best = max(c["score"] for c in found)
    return next(c for c in found if c["score"] >= best - SCORE_MARGIN), found


def process_recording(
    path: str, samples: list[np.ndarray], sr: int, detect: Detect, duration: float,
    types: dict, detector: dict,
) -> dict:
    """Searches ``path`` and saves what was found (``process_click``, with ``detector``
    describing it) in its label file, with the click as a to-be-confirmed
    ``Thumb_is_clicking_the_pen`` event of ``duration`` s and the ``CLICK_END_EVENTS`` at its
    end (``types``: events.json type by event name); returns ``process_click``."""
    click, found = find_click(path, samples, sr, detect)
    result = {
        "found": click is not None,
        "t": click["t"] if click else None,
        "score": click["score"] if click else None,
        "detections": found,
        "samples": len(samples),
        "detector": detector,
        "score_margin": SCORE_MARGIN,
        "processed": datetime.now().isoformat(timespec="seconds"),
    }
    label = load_label(path) or {}
    events = list(label.get("events", []))
    if click is not None and not click_events(label, confirmed=False):  # none marked meanwhile
        event = {
            "t": click["t"], "name": CLICK_EVENT, "type": types.get(CLICK_EVENT, ""),
            "added": datetime.now().timestamp(), "end": round(click["t"] + duration, 3),
            "params": {TO_BE_CONFIRMED: True, "score": click["score"]},
        }
        events = with_end_events(events + [event], event, types, {TO_BE_CONFIRMED: True})
    update_label(path, events=events, process_click=result)
    return result


def to_process(paths: list[str], success: str) -> list[str]:
    """The recordings Process click searches: labelled ``success``, with no click event and
    not searched before (``process_click``)."""
    out = []
    for path in paths:
        label = load_label(path) or {}
        if (label.get("label") == success and not click_events(label, confirmed=False)
                and "process_click" not in label):
            out.append(path)
    return out


def marked_duration(marks: list[tuple[str, float, float]]) -> float:
    return float(np.median([end - start for _, start, end in marks]))
