"""Episode lengths of the Play on hand recordings, and Process failure.

An episode runs from a recording's ``episode_start`` event to its ``terminal`` one (events
still to be confirmed do not count). The truncation length (s) is how long an episode may run
before it is truncated; it is kept with the recordings in ``processing.json``. Process failure
marks ``terminal`` and ``truncated`` at ``episode_start`` + the truncation length on every
failed recording without a ``terminal`` (and moves those it marked before, when the length
changed); a recording that ends earlier gets ``terminal`` and ``fail`` at its last timestep.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from mechanical_pen_data_collection.click_processing import TO_BE_CONFIRMED
from mechanical_pen_data_collection.playback_recording import load_label, update_label

EPISODE_START = "episode_start"
TERMINAL = "terminal"
TRUNCATED = "truncated"
FAIL = "fail"
# The events Process failure adds (truncated at the length, or failed at the recording's end),
# and the param saying it added them (the length used, s).
TRUNCATED_EVENTS = (TERMINAL, TRUNCATED)
ENDED_EVENTS = (TERMINAL, FAIL)
FAILURE_END_EVENTS = (TERMINAL, TRUNCATED, FAIL)
BY_PROCESS_FAILURE = "process_failure"
SETTINGS_NAME = "processing.json"
TRUNCATION_KEY = "truncation_s"
# Rewards of an episode (Processing tab's Process reward): ``success`` / ``fail`` at its last
# step (a success / a failure), ``step`` at every other step.
REWARDS_KEY = "rewards"
DEFAULT_REWARDS = {"success": 1.0, "fail": 0.0, "step": 0.0}


def settings_path(recordings_dir: str) -> str:
    return os.path.join(recordings_dir, SETTINGS_NAME)


def load_truncation(recordings_dir: str) -> float | None:
    """The saved truncation length (s), or None."""
    try:
        with open(settings_path(recordings_dir)) as f:
            value = json.load(f).get(TRUNCATION_KEY)
    except (OSError, ValueError, AttributeError):
        return None
    return float(value) if value is not None else None


def save_truncation(recordings_dir: str, length: float) -> None:
    path = settings_path(recordings_dir)
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    data[TRUNCATION_KEY] = round(float(length), 3)
    os.makedirs(recordings_dir, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=1)


def load_rewards(recordings_dir: str) -> dict[str, float]:
    """The saved rewards (``DEFAULT_REWARDS`` for those not saved)."""
    try:
        with open(settings_path(recordings_dir)) as f:
            saved = json.load(f).get(REWARDS_KEY) or {}
    except (OSError, ValueError, AttributeError):
        saved = {}
    return {k: float(saved.get(k, v)) for k, v in DEFAULT_REWARDS.items()}


def save_rewards(recordings_dir: str, rewards: dict[str, float]) -> None:
    path = settings_path(recordings_dir)
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    data[REWARDS_KEY] = {k: float(rewards[k]) for k in DEFAULT_REWARDS}
    os.makedirs(recordings_dir, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=1)


def confirmed(label: dict, name: str) -> list[dict]:
    return [
        e for e in (label or {}).get("events", [])
        if e.get("name") == name and not (e.get("params") or {}).get(TO_BE_CONFIRMED)
    ]


def episode_length(label: dict | None) -> float | None:
    """``terminal`` - ``episode_start`` (s) of a label file (their first ones), or None."""
    starts, ends = confirmed(label, EPISODE_START), confirmed(label, TERMINAL)
    if not starts or not ends:
        return None
    return float(ends[0]["t"]) - float(starts[0]["t"])


@dataclass
class EpisodeStats:
    lengths: list[tuple[str, float]]  # (recording, s) of the processed successful episodes
    longest: tuple[str, float] | None
    failures: int  # failed recordings
    failures_done: int  # of them with a ``terminal``


def episode_stats(labelled: list[tuple[str, dict]], success: str, failure: str) -> EpisodeStats:
    """The episodes of the labelled recordings ((path, label file) pairs)."""
    lengths = []
    for path, label in labelled:
        length = episode_length(label) if label.get("label") == success else None
        if length is not None:
            lengths.append((path, length))
    failed = [label for _, label in labelled if label.get("label") == failure]
    return EpisodeStats(
        lengths=lengths,
        longest=max(lengths, key=lambda p: p[1]) if lengths else None,
        failures=len(failed),
        failures_done=sum(bool(confirmed(label, TERMINAL)) for label in failed),
    )


def recording_end(path: str) -> float:
    """The last recorded time (s) of a Play on hand recording (only its time arrays are
    read)."""
    with np.load(path, allow_pickle=False) as data:
        ends = [float(data[k][-1]) for k in ("state_t", "cmd_t", "xela_t", "video_t")
                if k in data.files and len(data[k])]
    return max(ends) if ends else 0.0


def _by_process_failure(event: dict) -> bool:
    return BY_PROCESS_FAILURE in (event.get("params") or {})


def failure_target(label: dict, length: float) -> bool:
    """Whether Process failure marks a failed recording: no ``terminal`` yet, or the ones it
    marked were at another truncation length."""
    ends = [e for e in label.get("events", []) if e.get("name") in FAILURE_END_EVENTS]
    if not any(e.get("name") == TERMINAL for e in ends):
        return True
    return all(_by_process_failure(e) for e in ends) and any(
        abs(e["params"][BY_PROCESS_FAILURE] - length) > 1e-3 for e in ends
    )


def truncate_failure(path: str, length: float, types: dict) -> str:
    """Marks ``terminal`` and ``truncated`` at ``episode_start`` + ``length`` on a failed
    recording, or ``terminal`` and ``fail`` at its last timestep if it ends earlier (replacing
    those Process failure marked before; ``types``: events.json type by event name); returns
    "truncated", "ended" or "no start"."""
    label = load_label(path) or {}
    starts = confirmed(label, EPISODE_START)
    if not starts:
        return "no start"
    t = round(float(starts[0]["t"]) + length, 3)
    end = round(recording_end(path), 3)
    outcome, names = ("truncated", TRUNCATED_EVENTS) if t <= end else ("ended", ENDED_EVENTS)
    t = min(t, end)
    events = [
        e for e in label.get("events", [])
        if not (e.get("name") in FAILURE_END_EVENTS and _by_process_failure(e))
    ]
    for name in names:
        events.append({
            "t": t, "name": name, "type": types.get(name, ""),
            "added": datetime.now().timestamp(), "end": None,
            "params": {BY_PROCESS_FAILURE: round(float(length), 3)},
        })
    update_label(path, events=events)
    return outcome
