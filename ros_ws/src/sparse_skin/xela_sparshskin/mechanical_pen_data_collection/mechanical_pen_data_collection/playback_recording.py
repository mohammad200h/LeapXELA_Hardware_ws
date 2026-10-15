"""Recordings of the Edit tab's Play: what was sent to the hand and what the hand did.

Each Play of a take ``<take>`` is saved as ``<playback_dir>/<take>_<n>.npz`` (``n`` = 1, 2, ...
the next free index), with every time relative to the start of the Play:

- ``cmd_t`` / ``cmd_q`` (M, 16) / ``cmd_local``: the hand command of every command step and the
  take time it was for (``cmd_q`` is what Replay sends again);
- ``state_t`` / ``position`` / ``velocity`` / ``effort`` (N, 16): ``leap_state`` (NaN where a
  message had no velocity / effort);
- ``xela_t`` / ``xela`` (L, T, 3): raw Xela readings, with ``xela_baseline`` (T, 3) the live
  no-contact baseline at Play;
- ``click_t``: rising edges of the click detector;
- ``video`` / ``video_t``: the camera recording (path, "" if none) and its frame times (the
  Compose tab's Play on hand records one);
- ``audio`` / ``audio_t0`` / ``audio_rate``: the microphone recording (16-bit mono WAV path, ""
  if none), the time of its first sample and its sample rate (Play on hand records one);
- ``meta``: JSON (source take, how it ended, the take time span, ``replay_of`` for a Replay...).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

import numpy as np


def _empty(*shape: int, dtype=np.float64) -> np.ndarray:
    return np.empty(shape, dtype=dtype)


@dataclass
class PlaybackRecording:
    path: str
    take: str  # path of the take that was played
    finger: str
    joint_names: list[str]  # hand joint names (columns of the (., 16) arrays)
    cols: list[int]  # columns of ``finger``
    cmd_t: np.ndarray = field(default_factory=lambda: _empty(0))
    cmd_q: np.ndarray = field(default_factory=lambda: _empty(0, 16))
    cmd_local: np.ndarray = field(default_factory=lambda: _empty(0))
    state_t: np.ndarray = field(default_factory=lambda: _empty(0))
    position: np.ndarray = field(default_factory=lambda: _empty(0, 16))
    velocity: np.ndarray = field(default_factory=lambda: _empty(0, 16))
    effort: np.ndarray = field(default_factory=lambda: _empty(0, 16))
    xela_t: np.ndarray = field(default_factory=lambda: _empty(0))
    xela: np.ndarray = field(default_factory=lambda: _empty(0, 0, 3, dtype=np.float32))
    xela_baseline: np.ndarray = field(default_factory=lambda: _empty(0, 3))
    click_t: np.ndarray = field(default_factory=lambda: _empty(0))
    video: str = ""  # camera recording of the Play ("" if none)
    video_t: np.ndarray = field(default_factory=lambda: _empty(0))  # its frame times
    audio: str = ""  # microphone recording of the Play (WAV, "" if none)
    audio_t0: float = 0.0  # time of its first sample
    audio_rate: int = 0  # its sample rate (Hz)
    meta: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return os.path.splitext(os.path.basename(self.path))[0]

    @property
    def duration(self) -> float:
        return float(self.cmd_t[-1] - self.cmd_t[0]) if len(self.cmd_t) > 1 else 0.0

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        np.savez_compressed(
            self.path,
            take=self.take,
            finger=self.finger,
            joint_names=np.array(self.joint_names),
            cols=np.asarray(self.cols, dtype=int),
            cmd_t=self.cmd_t,
            cmd_q=self.cmd_q,
            cmd_local=self.cmd_local,
            state_t=self.state_t,
            position=self.position,
            velocity=self.velocity,
            effort=self.effort,
            xela_t=self.xela_t,
            xela=self.xela,
            xela_baseline=self.xela_baseline,
            click_t=self.click_t,
            video=self.video,
            video_t=self.video_t,
            audio=self.audio,
            audio_t0=self.audio_t0,
            audio_rate=self.audio_rate,
            meta=json.dumps(self.meta),
        )

    @classmethod
    def load(cls, path: str) -> PlaybackRecording:
        with np.load(path, allow_pickle=False) as data:
            arrays = {
                name: data[name] for name in (
                    "cmd_t", "cmd_q", "cmd_local", "state_t", "position", "velocity", "effort",
                    "xela_t", "xela", "xela_baseline", "click_t", "video_t",
                ) if name in data.files
            }
            return cls(
                path=path,
                take=str(data["take"]),
                finger=str(data["finger"]),
                joint_names=[str(n) for n in data["joint_names"]],
                cols=[int(c) for c in data["cols"]],
                video=str(data["video"]) if "video" in data.files else "",
                audio=str(data["audio"]) if "audio" in data.files else "",
                audio_t0=float(data["audio_t0"]) if "audio_t0" in data.files else 0.0,
                audio_rate=int(data["audio_rate"]) if "audio_rate" in data.files else 0,
                meta=json.loads(str(data["meta"])) if "meta" in data.files else {},
                **arrays,
            )


def list_playbacks(directory: str, take_name: str | None = None) -> list[str]:
    """Playback paths in ``directory`` (only those of ``take_name`` if given), newest first."""
    if not os.path.isdir(directory):
        return []
    pattern = re.compile(rf"^{re.escape(take_name)}_\d+\.npz$") if take_name else None
    paths = [
        os.path.join(directory, f) for f in os.listdir(directory)
        if f.endswith(".npz") and (pattern is None or pattern.match(f))
    ]
    return sorted(paths, key=os.path.getmtime, reverse=True)


def next_playback_path(directory: str, take_name: str) -> str:
    """``<directory>/<take_name>_<n>.npz`` with the lowest index ``n`` >= 1 not used yet."""
    n = 1
    while os.path.exists(os.path.join(directory, f"{take_name}_{n}.npz")):
        n += 1
    return os.path.join(directory, f"{take_name}_{n}.npz")
