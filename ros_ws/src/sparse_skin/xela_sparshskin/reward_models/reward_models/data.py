"""The Sparsh-skin episodes as clips for the reward models.

A Play on hand recording (record_demonstration's ``compose_playbacks/<box>_<n>.npz``) is used
when it is an episode as ``sparsh_processing`` takes them (``eligible_episodes``: labelled
success / failure, with a confirmed ``episode_start`` and a later ``terminal``) and has its
Sparsh-skin episode (``<recordings_dir>/sparsh_skin/<rate>hz/episode_<recording>.npz``, the
episode rate's folder (``episode_hz``, the Processing tab's Rate), written by the
Process tab's Sparsh-skin transform) within that span (the transform trims it to what every
stream covers). The clip is that episode on its own
time grid (``time_grid``: ``steps`` samples at ``freq``, 100 Hz, from ``episode_start`` to
``terminal``), taken every ``round(freq / step_hz)`` steps (the last step, ``terminal``, always
kept), with:

- ``obs`` (N, 368, 6) float32: per taxel, ``flex_taxel_fk/forces_local`` (Xela x, y, z: dead
  taxels 0, the Baseline tab's no-contact baseline subtracted) then
  ``flex_taxel_fk/positions`` (FK taxel position, m, hand base frame), in FK order. Not
  normalised here: the networks z-score them per channel (``ObsStats``);
- ``actions`` (N, 16) float32: the episode's ``actions`` (sim joint targets), used only as the
  Coupled Local Global local model's dynamics input.

The ``modality`` (``MODALITIES``) picks what ``obs`` holds:

- ``sparsh`` (default): the taxel state above, (N, 368, 6);
- ``proprio``: the hand's own joint state, (N, ``PROPRIO_DIM``): per joint (``LEAP_JOINT_ORDER``)
  sin q, cos q (wrap-safe, see the th_ipl encoder), dq and effort, read from the recording's
  ``leap_state`` stream (``state_t``, ``position``, ``velocity``, ``effort``, ~10 Hz). Each step
  takes the newest sample at or before its time (``drop``), never an interpolation.

Every clip also has ``proprio`` and ``thumb_onset``: the first step at which a thumb joint has
moved more than ``THUMB_ONSET_RAD`` from where it started (wrap-safe), -1 when it never does.
It splits an episode into subtasks for REDS (grip, then thumb press); it is found in every
current episode, while the thumb taxels' force rise is not (successful clicks press lightly).

The label is the recording's current one (``<box>_<n>.label.json``).
"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

import numpy as np

from mechanical_pen_data_collection.playback_recording import FAILURE, SUCCESS, load_label
from mechanical_pen_data_collection.sparsh_processing import (
    DEFAULT_OUTPUT_NAME as SPARSH_FOLDER,
    FREQ,
    rate_dir,
    STATS_NAME,
    eligible_episodes,
    episode_span,
    output_name,
)

N_TAXELS = 368
N_JOINTS = 16
OBS_CHANNELS = 6  # forces_local x, y, z, positions x, y, z
SPARSH = "sparsh"
PROPRIO = "proprio"
MODALITIES = (SPARSH, PROPRIO)
PROPRIO_DIM = 4 * N_JOINTS  # sin q, cos q, dq, effort
# sparsh_processing's joint order (the episodes' ``joint_order``), the proprio channels' order.
LEAP_JOINT_ORDER = (
    "if_mcp", "if_rot", "if_pip", "if_dip", "mf_mcp", "mf_rot", "mf_pip", "mf_dip",
    "rf_mcp", "rf_rot", "rf_pip", "rf_dip", "th_cmc", "th_axl", "th_mcp", "th_ipl",
)
THUMB_ONSET_RAD = 0.05  # a thumb joint this far from its start: the press has begun
THUMB_ONSET_ENTRY_SAMPLES = 5  # the start: the mean of the first joint samples
FORCES_KEY = "flex_taxel_fk/forces_local"
POSITIONS_KEY = "flex_taxel_fk/positions"
SPAN_TOLERANCE_S = 0.02  # the episode may reach this far outside the label's span
RUNS_FOLDER = "reward_models"  # <recordings_dir>/reward_models/<method>
LOAD_THREADS = 8

Progress = Callable[[int, int, str], None]  # (done, total, text)


@dataclass
class Clip:
    path: str  # the recording
    name: str
    label: str  # SUCCESS / FAILURE
    t: np.ndarray  # (N,) s, recording time
    obs: np.ndarray  # (N, 368, 6) float32 (sparsh) or (N, PROPRIO_DIM) float32 (proprio)
    actions: np.ndarray  # (N, 16) float32
    episode_hz: float = 100.0  # the Sparsh-skin episode's step rate (Processing tab's Rate)
    clip_hz: float = 100.0  # the rate its steps were taken at (episode_hz / stride)
    modality: str = SPARSH
    proprio: np.ndarray | None = None  # (N, PROPRIO_DIM) float32
    thumb_onset: int = -1  # first step of the thumb press, -1 if none

    @property
    def success(self) -> bool:
        return self.label == SUCCESS

    def __len__(self) -> int:
        return len(self.t)


@dataclass
class ObsStats:
    """Per-channel mean / std of ``obs``: the forces' from ``sparsh_stats.json`` (as LEQ_DV3's
    ``forces_norm``), the positions' from the training clips."""

    mean: np.ndarray  # (6,)
    std: np.ndarray  # (6,)

    def as_lists(self) -> tuple[list[float], list[float]]:
        return [float(v) for v in self.mean], [float(v) for v in self.std]


def runs_root(recordings_dir: str) -> str:
    return os.path.join(recordings_dir, RUNS_FOLDER)


def sparsh_dir(recordings_dir: str, episode_hz: float = FREQ) -> str:
    """The folder of the Sparsh-skin episodes processed at ``episode_hz``."""
    return rate_dir(recordings_dir, episode_hz)


def sparsh_episode_path(recording: str, episode_hz: float = FREQ) -> str:
    return os.path.join(sparsh_dir(os.path.dirname(recording), episode_hz),
                        output_name(recording))


def force_stats(recordings_dir: str, episode_hz: float = FREQ) -> tuple[np.ndarray, np.ndarray]:
    """``xela_mean`` / ``xela_std`` (3,) of the ``episode_hz`` Sparsh-skin episodes of
    ``recordings_dir``."""
    path = os.path.join(sparsh_dir(recordings_dir, episode_hz), STATS_NAME)
    try:
        with open(path) as f:
            stats = json.load(f)
    except (OSError, ValueError) as e:
        raise FileNotFoundError(
            f"no Sparsh-skin stats ({path}): run the Process tab's Sparsh-skin transform"
        ) from e
    return (np.asarray(stats["xela_mean"], np.float32),
            np.maximum(np.asarray(stats["xela_std"], np.float32), 1e-6))


def obs_dim(modality: str) -> int:
    """The flattened size of one step's ``obs``."""
    return N_TAXELS * OBS_CHANNELS if modality == SPARSH else PROPRIO_DIM


def obs_stats(recordings_dir: str, clips: list[Clip], episode_hz: float = FREQ) -> ObsStats:
    """Sparsh: forces from ``sparsh_stats.json``, positions over every step of ``clips``.
    Proprio: every channel over every step of ``clips``."""
    if clips and clips[0].modality == PROPRIO:
        x = np.concatenate([c.obs for c in clips])
        return ObsStats(x.mean(0).astype(np.float32),
                        np.maximum(x.std(0), 1e-6).astype(np.float32))
    f_mean, f_std = force_stats(recordings_dir, episode_hz)
    pos = np.concatenate([c.obs[..., 3:].reshape(-1, 3) for c in clips])
    return ObsStats(np.concatenate([f_mean, pos.mean(0)]).astype(np.float32),
                    np.concatenate([f_std, np.maximum(pos.std(0), 1e-6)]).astype(np.float32))


def step_indices(steps: int, freq: float, step_hz: float) -> np.ndarray:
    """Every ``round(freq / step_hz)``-th step, and the last one."""
    stride = max(1, int(round(freq / step_hz))) if step_hz > 0 else 1
    idx = np.arange(0, steps, stride)
    return idx if idx[-1] == steps - 1 else np.append(idx, steps - 1)


def _wrapped(angle: np.ndarray) -> np.ndarray:
    return np.angle(np.exp(1j * angle))


def load_proprio(recording: str, t: np.ndarray) -> tuple[np.ndarray, float]:
    """The recording's joint state at the times ``t``: (``proprio`` (N, PROPRIO_DIM), the time
    the thumb starts to move (inf if never)). A step takes the newest ``leap_state`` sample at
    or before it (the first one before the stream starts)."""
    with np.load(recording, allow_pickle=False) as rec:
        names = [str(n) for n in rec["joint_names"]]
        state_t = np.asarray(rec["state_t"], float)
        q = np.asarray(rec["position"], float)
        dq = np.asarray(rec["velocity"], float)
        effort = np.asarray(rec["effort"], float)
    if len(state_t) == 0:
        raise ValueError("recording has no joint states")
    missing = [n for n in LEAP_JOINT_ORDER if n not in names]
    if missing:
        raise ValueError(f"recording's joints lack {missing}")
    cols = [names.index(n) for n in LEAP_JOINT_ORDER]
    order = np.argsort(state_t, kind="stable")
    state_t, q, dq, effort = state_t[order], q[order][:, cols], dq[order][:, cols], effort[order][:, cols]
    k = np.clip(np.searchsorted(state_t, t, side="right") - 1, 0, len(state_t) - 1)
    proprio = np.concatenate([np.sin(q[k]), np.cos(q[k]), dq[k], effort[k]], -1)
    # Thumb press onset, over the samples inside the episode.
    inside = (state_t >= t[0]) & (state_t <= t[-1])
    thumb = [LEAP_JOINT_ORDER.index(n) for n in LEAP_JOINT_ORDER if n.startswith("th_")]
    onset = float("inf")
    if inside.sum() > THUMB_ONSET_ENTRY_SAMPLES:
        tq, tt = q[inside][:, thumb], state_t[inside]
        entry = tq[:THUMB_ONSET_ENTRY_SAMPLES]
        ref = np.angle(np.exp(1j * entry).mean(0))
        moved = np.abs(_wrapped(tq - ref)).max(1) > THUMB_ONSET_RAD
        if moved.any():
            onset = float(tt[np.argmax(moved)])
    return proprio.astype(np.float32), onset


def load_clip(
    recording: str, step_hz: float, label: dict | None = None, episode_hz: float = FREQ,
    modality: str = SPARSH,
) -> Clip:
    """The ``episode_hz`` Sparsh-skin episode of ``recording`` as a Clip, its ``obs`` from
    ``modality``; raises ValueError when it has none (or one for another span) or is not an
    episode."""
    if modality not in MODALITIES:
        raise ValueError(f"unknown modality {modality!r} (one of {MODALITIES})")
    label = load_label(recording) if label is None else label
    span = episode_span(label)
    if isinstance(span, str):
        raise ValueError(span)
    path = sparsh_episode_path(recording, episode_hz)
    if not os.path.isfile(path):
        raise ValueError(
            f"no {episode_hz:g} Hz Sparsh-skin episode (run the Process tab's Sparsh-skin "
            f"transform at {episode_hz:g} Hz)"
        )
    with np.load(path, allow_pickle=False) as ep:
        meta = json.loads(str(ep["metadata_json"]))
        start, end = float(meta["t_start"]), float(meta["t_end"])
        # The transform trims the label's span to what every stream covers, so the episode
        # lies inside it; one reaching outside was written for an older label.
        if start < span[0] - SPAN_TOLERANCE_S or end > span[1] + SPAN_TOLERANCE_S:
            raise ValueError(
                f"Sparsh-skin episode spans {start:.3f}-{end:.3f} s but the label's episode is "
                f"{span[0]:.3f}-{span[1]:.3f} s (run the transform again)"
            )
        steps = len(ep["rewards"])
        if steps < 2:
            raise ValueError("Sparsh-skin episode has fewer than 2 steps")
        episode_hz = float(meta.get("freq", 100.0))
        idx = step_indices(steps, episode_hz, step_hz)
        obs = (np.concatenate([ep[FORCES_KEY][idx], ep[POSITIONS_KEY][idx]], -1)
               if modality == SPARSH else None)
        actions = np.asarray(ep["actions"][idx], np.float32)
    t = np.linspace(start, end, steps)[idx]  # sparsh_processing.time_grid
    proprio, onset_t = load_proprio(recording, t)
    after = np.nonzero(t >= onset_t)[0]
    return Clip(
        path=recording,
        name=os.path.splitext(os.path.basename(recording))[0],
        label=label["label"],
        t=t,
        obs=obs.astype(np.float32) if modality == SPARSH else proprio,
        actions=actions,
        episode_hz=episode_hz,
        clip_hz=episode_hz / max(1, int(round(episode_hz / step_hz))) if step_hz > 0
        else episode_hz,
        modality=modality,
        proprio=proprio,
        thumb_onset=int(after[0]) if len(after) else -1,
    )


def load_clips(
    recordings_dir: str, step_hz: float, progress: Progress | None = None,
    cancelled: Callable[[], bool] | None = None, episode_hz: float = FREQ,
    modality: str = SPARSH,
) -> tuple[list[Clip], dict[str, str]]:
    """The clips of every eligible recording, oldest first, and {recording: why not} for the
    others. Reads in ``LOAD_THREADS`` threads; stops early (returning what it has) once
    ``cancelled()``."""
    paths, skipped = eligible_episodes(recordings_dir)
    clips: dict[str, Clip] = {}
    done = 0

    def one(path: str) -> tuple[str, Clip | str]:
        if cancelled is not None and cancelled():
            return path, "cancelled"
        try:
            return path, load_clip(path, step_hz, episode_hz=episode_hz, modality=modality)
        except ValueError as e:
            return path, str(e)
        except Exception as e:  # noqa: BLE001 - a bad episode is skipped, not fatal
            return path, f"failed: {e}"

    with ThreadPoolExecutor(LOAD_THREADS) as pool:
        for path, clip in pool.map(one, paths):
            done += 1
            if isinstance(clip, Clip):
                clips[path] = clip
            else:
                skipped[os.path.basename(path)] = clip
            if progress is not None:
                progress(done, len(paths), f"loaded {output_name(path)}")
    return [clips[p] for p in paths if p in clips], skipped


def split_clips(clips: list[Clip], val_fraction: float, seed: int) -> tuple[list[Clip], list[Clip]]:
    """Recording-level train / validation split, stratified by label (as LEQ_DV3's
    ``split_demos``: deterministic for a seed, at least one validation clip per label)."""
    rng = np.random.default_rng(seed)
    train, val = [], []
    for label in (SUCCESS, FAILURE):
        group = [c for c in clips if c.label == label]
        if val_fraction <= 0 or len(group) < 2:
            train += group
            continue
        perm = rng.permutation(len(group))
        n_val = max(1, int(round(len(group) * val_fraction)))
        val += [group[i] for i in perm[:n_val]]
        train += [group[i] for i in perm[n_val:]]
    return train, val
