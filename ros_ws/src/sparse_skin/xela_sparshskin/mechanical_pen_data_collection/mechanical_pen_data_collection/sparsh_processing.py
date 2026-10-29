"""Sparsh-skin preprocessing of the Play on hand episodes, written for the LEQ_DV3 world model.

Follows Sparsh-skin's Xela pipeline (sparsh-multisensory-touch ``XelaSSLDataset`` /
``generate_policy_dataset.py``) on each labelled episode (``episode_start`` to ``terminal``,
confirmed, of a ``success`` / ``failure`` recording):

- a common ``np.linspace`` time grid at ``freq`` (100 Hz) over the span every stream covers;
- Xela x, y, z and the joints resampled onto it with ``CubicSpline``;
- Xela values outside [``XELA_LOW``, ``XELA_HIGH``] set to 0 (a dead taxel), and the no-contact
  baseline subtracted where x is not 0: the ``xela_baseline`` of a Baseline tab recording
  (``baseline_file``, the same for every episode), or else the recording's own;
- taxels in ``XELA_FLATTEN_ORDER`` (``taxel_fk_util.TAXEL_IDS_IN_FK_ORDER``) with their FK
  positions (m, hand base frame) from the sim joint angles;
- the global Xela mean / std (zeros as NaN) of the written episodes, kept beside them as
  ``sparsh_stats.json`` (Sparsh normalizes in the model, so the arrays are not normalized).

Each episode is written as ``episode_<recording>.npz`` in the input format of LEQ_DV3's
``data/leap/convert_episodes.py``: ``actions`` (T, 16) sim joint targets (the command held
at each step, ``LEAP_JOINT_ORDER``), ``flex_taxel_fk/forces_local`` (T, 368, 3) the
preprocessed Xela counts, ``flex_taxel_fk/positions`` (T, 368, 3), ``rewards`` (T,) (the
``rewards`` of ``processing.json``, ``episode_rewards``: ``success`` at the last step of a
success, ``fail`` at the last step of a failure, ``step`` at every other step; Process reward
sets them again on the episodes written, ``apply_rewards``), and ``metadata_json`` (``terminated_by_env``: a success, or a failure
whose ``terminal`` was marked by hand; not one Process failure added; ``baseline``: the
baseline file, or "recording"; ``rewards``: the values used). An episode already written with another baseline is rewritten.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Callable

import numpy as np
from scipy.interpolate import CubicSpline

from mechanical_pen_data_collection import taxel_fk_util as fk
from mechanical_pen_data_collection.episode_processing import (
    BY_PROCESS_FAILURE,
    DEFAULT_REWARDS,
    EPISODE_START,
    TERMINAL,
    confirmed,
    load_rewards,
)
from mechanical_pen_data_collection.playback_recording import (
    FAILURE,
    SUCCESS,
    PlaybackRecording,
    list_playbacks,
    load_label,
)

FREQ = 100.0  # Hz, Sparsh-skin's interpolating_freq
XELA_LOW, XELA_HIGH = 20000.0, 60000.0  # valid raw Xela range (outside: dead taxel, 0)
EPISODE_PREFIX = "episode_"
STATS_NAME = "sparsh_stats.json"
MANIFEST_NAME = "manifest.json"
DEFAULT_OUTPUT_NAME = "sparsh_skin"  # next to the recordings


def output_name(recording_path: str) -> str:
    return EPISODE_PREFIX + os.path.splitext(os.path.basename(recording_path))[0] + ".npz"


def episode_span(label: dict | None) -> tuple[float, float] | str:
    """(``episode_start``, ``terminal``) of a labelled episode, or why it is not one."""
    label = label or {}
    if label.get("label") not in (SUCCESS, FAILURE):
        return "not labelled success / failure"
    starts, ends = confirmed(label, EPISODE_START), confirmed(label, TERMINAL)
    if not starts:
        return f"no confirmed '{EPISODE_START}'"
    if not ends:
        return f"no confirmed '{TERMINAL}'"
    start, end = float(starts[0]["t"]), float(ends[0]["t"])
    if end <= start:
        return f"'{TERMINAL}' is not after '{EPISODE_START}'"
    return start, end


def terminated_by_env(label: dict) -> bool:
    """A success ends the task; a failure only when its ``terminal`` was marked by hand
    (Process failure's ``terminal`` is a time limit or the recording running out)."""
    if label.get("label") == SUCCESS:
        return True
    ends = confirmed(label, TERMINAL)
    return bool(ends) and BY_PROCESS_FAILURE not in (ends[0].get("params") or {})


def eligible_episodes(recordings_dir: str) -> tuple[list[str], dict[str, str]]:
    """Recordings with an episode, oldest first, and {recording: why not} for the others."""
    paths, skipped = [], {}
    for path in reversed(list_playbacks(recordings_dir)):
        span = episode_span(load_label(path))
        if isinstance(span, str):
            skipped[os.path.basename(path)] = span
        else:
            paths.append(path)
    return paths, skipped


def time_grid(start: float, end: float, freq: float) -> np.ndarray:
    """Sparsh's ``compute_interp_timestamps``: ``int((end - start) * freq)`` samples."""
    return np.linspace(start, end, int((end - start) * freq))


def _increasing(t: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Drops samples not later than every one before them (a repeated or backwards stamp;
    CubicSpline needs strictly increasing times)."""
    keep = np.concatenate([[True], t[1:] > np.maximum.accumulate(t)[:-1]])
    return t[keep], values[keep]


def preprocess_xela(
    xela_t: np.ndarray, xela: np.ndarray, baseline: np.ndarray, grid: np.ndarray
) -> np.ndarray:
    """(T, 368, 3) Xela on ``grid`` in FK order: resampled, outliers 0, baseline subtracted
    where x is not 0 (``xela`` and ``baseline`` by hardware id)."""
    t, x = _increasing(np.asarray(xela_t, np.float64), np.asarray(xela, np.float64))
    out = CubicSpline(t, x, axis=0)(grid)
    out = np.where((out < XELA_LOW) | (out > XELA_HIGH), 0.0, out)
    mask = out[..., 0] != 0
    out[mask] -= np.broadcast_to(np.asarray(baseline, np.float64), out.shape)[mask]
    return out[:, fk.TAXEL_IDS_IN_FK_ORDER].astype(np.float32)


def sim_joints(to_sim: Callable, names: list[str], q_hw: np.ndarray) -> np.ndarray:
    """(N, 16) hardware joints ``q_hw`` (columns ``names``) as sim angles in FK order."""
    sim = np.array([to_sim(names, q) for q in q_hw], dtype=np.float64).reshape(-1, 16)
    return fk.joint_angles_in_fk_order(list(to_sim.sim_names), sim).astype(np.float64)


RECORDING_BASELINE = "recording"  # an episode's ``baseline`` when it used the recording's own


def load_baseline(path: str) -> np.ndarray:
    """(368, 3) ``xela_baseline`` (by hardware id) of a Baseline tab recording."""
    with np.load(path) as data:
        if "xela_baseline" not in data.files:
            raise ValueError(f"{path} has no xela_baseline")
        baseline = np.asarray(data["xela_baseline"], np.float64)
    if baseline.shape != (fk.NUM_TAXELS, 3):
        raise ValueError(f"{path}: xela_baseline is {baseline.shape}, not ({fk.NUM_TAXELS}, 3)")
    return baseline


def episode_rewards(label: str | None, steps: int, rewards: dict[str, float]) -> np.ndarray:
    """(steps,) rewards of an episode labelled ``label``: ``rewards["success"]`` /
    ``rewards["fail"]`` at its last step (a success / anything else), ``rewards["step"]`` at
    every other one."""
    out = np.full(steps, rewards["step"], np.float32)
    if steps:
        out[-1] = rewards["success"] if label == SUCCESS else rewards["fail"]
    return out


def set_episode_rewards(path: str, rewards: dict[str, float]) -> str | None:
    """Sets the rewards of an episode file (and its metadata's ``rewards``) to ``rewards``,
    unless it has them already. Returns its label."""
    with np.load(path) as data:
        arrays = {k: data[k] for k in data.files}
    metadata = json.loads(str(arrays["metadata_json"]))
    if metadata.get("rewards") != rewards:
        arrays["rewards"] = episode_rewards(metadata.get("label"), len(arrays["rewards"]), rewards)
        metadata["rewards"] = dict(rewards)
        arrays["metadata_json"] = np.array(json.dumps(metadata))
        np.savez_compressed(path, **arrays)
    return metadata.get("label")


def apply_rewards(
    out_dir: str, rewards: dict[str, float],
    progress: Callable[[int, int], None] | None = None,
) -> dict[str, int]:
    """Process reward: sets the rewards of every episode in ``out_dir``. Returns how many of
    each label (``failed``: could not be read or written)."""
    names = sorted(n for n in os.listdir(out_dir)
                   if n.startswith(EPISODE_PREFIX) and n.endswith(".npz"))
    counts: dict[str, int] = {SUCCESS: 0, FAILURE: 0, "failed": 0}
    for i, name in enumerate(names, start=1):
        try:
            label = set_episode_rewards(os.path.join(out_dir, name), rewards)
            counts[SUCCESS if label == SUCCESS else FAILURE] += 1
        except Exception:  # noqa: BLE001 - one bad episode does not stop it
            counts["failed"] += 1
        if progress is not None:
            progress(i, len(names))
    return counts


def episode_baseline(path: str) -> str | None:
    """The ``baseline`` an episode file was written with (None: unknown)."""
    with np.load(path) as data:
        return json.loads(str(data["metadata_json"])).get("baseline")


def transform_recording(
    path: str, label: dict, to_sim: Callable, freq: float = FREQ, urdf_path=None,
    baseline: np.ndarray | None = None, baseline_file: str = "",
    rewards: dict[str, float] | None = None,
) -> dict[str, np.ndarray]:
    """The LEQ_DV3 episode arrays of a labelled recording (``episode_span`` must be one), with
    ``baseline`` (from ``baseline_file``) subtracted, or else the recording's own."""
    start, end = episode_span(label)
    rec = PlaybackRecording.load(path)
    for name in ("xela_t", "state_t", "cmd_t"):
        if len(getattr(rec, name)) < 2:
            raise ValueError(f"no {name.removesuffix('_t')} recorded")
    if baseline is None:
        if len(rec.xela_baseline) != fk.NUM_TAXELS:
            raise ValueError("no xela_baseline")
        baseline = rec.xela_baseline
    if rec.xela.shape[1] != len(baseline):
        raise ValueError(f"{rec.xela.shape[1]} taxels recorded, the baseline has {len(baseline)}")
    start = max(start, rec.xela_t[0], rec.state_t[0])
    end = min(end, rec.xela_t[-1], rec.state_t[-1])
    grid = time_grid(start, end, freq)
    if len(grid) < 2:
        raise ValueError(f"episode shorter than one step at {freq:g} Hz")

    forces = preprocess_xela(rec.xela_t, rec.xela, baseline, grid)

    state_t, q = _increasing(rec.state_t, sim_joints(to_sim, rec.joint_names, rec.position))
    joints = CubicSpline(state_t, q, axis=0)(grid)
    positions, _ = fk.get_fk_taxel_frames(joints, urdf_path, mujoco_world=False)

    # Commands are piecewise constant: the last one sent at or before each step.
    cmd = sim_joints(to_sim, rec.joint_names, rec.cmd_q)
    held = np.clip(np.searchsorted(rec.cmd_t, grid, side="right") - 1, 0, len(cmd) - 1)
    actions = cmd[held]

    rewards = dict(DEFAULT_REWARDS if rewards is None else rewards)
    metadata = {
        "terminated_by_env": terminated_by_env(label),
        "label": label.get("label"),
        "source": os.path.abspath(path),
        "t_start": round(float(grid[0]), 4),
        "t_end": round(float(grid[-1]), 4),
        "freq": freq,
        "steps": len(grid),
        "joint_order": fk.LEAP_JOINT_ORDER,
        "taxel_order": "XELA_FLATTEN_ORDER",
        "forces_local": "Sparsh-skin preprocessed Xela counts (outliers 0, baseline subtracted)",
        "baseline": os.path.abspath(baseline_file) if baseline_file else RECORDING_BASELINE,
        "rewards": rewards,
        "positions": "FK taxel positions (m), hand base frame",
        "actions": "sim joint targets (rad), last command at each step",
    }
    return {
        "actions": actions.astype(np.float32),
        "flex_taxel_fk/forces_local": forces,
        "flex_taxel_fk/positions": positions.astype(np.float32),
        "rewards": episode_rewards(label.get("label"), len(grid), rewards),
        "metadata_json": np.array(json.dumps(metadata)),
    }


class XelaStats:
    """Running global mean / std of the Xela channels, zeros as NaN
    (Sparsh's ``compute_xela_normalization`` without holding every episode)."""

    def __init__(self) -> None:
        self.n = np.zeros(3)
        self.sum = np.zeros(3)
        self.sum_sq = np.zeros(3)

    def add(self, forces: np.ndarray) -> None:
        x = np.asarray(forces, np.float64).reshape(-1, 3)
        valid = x != 0
        self.n += valid.sum(axis=0)
        self.sum += np.where(valid, x, 0.0).sum(axis=0)
        self.sum_sq += np.where(valid, x * x, 0.0).sum(axis=0)

    def mean_std(self) -> tuple[np.ndarray, np.ndarray]:
        n = np.maximum(self.n, 1)
        mean = self.sum / n
        return mean, np.sqrt(np.maximum(self.sum_sq / n - mean * mean, 0.0))


def write_episode(out_dir: str, name: str, data: dict[str, np.ndarray]) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    np.savez_compressed(path, **data)
    return path


def write_dataset(
    recordings_dir: str,
    out_dir: str,
    to_sim: Callable,
    recordings: list[str] | None = None,
    freq: float = FREQ,
    overwrite: bool = False,
    progress: Callable[[int, int, str], None] | None = None,
    baseline_file: str = "",
) -> dict:
    """Writes the episodes of ``recordings`` (file names in ``recordings_dir``; None: every
    one with an episode) to ``out_dir`` with ``sparsh_stats.json`` and ``manifest.json``, with
    the baseline of ``baseline_file`` ("": each recording's own). Episodes already there are
    kept unless ``overwrite`` or written with another baseline. ``progress(done, total,
    text)`` is called before the first and after each recording. Returns the manifest."""
    baseline = load_baseline(baseline_file) if baseline_file else None
    used = os.path.abspath(baseline_file) if baseline_file else RECORDING_BASELINE
    rewards = load_rewards(recordings_dir)
    paths, skipped = eligible_episodes(recordings_dir)
    if recordings:
        wanted = {os.path.basename(r) for r in recordings}
        skipped = {k: v for k, v in skipped.items() if k in wanted}
        paths = [p for p in paths if os.path.basename(p) in wanted]
        for missing in wanted - {os.path.basename(p) for p in paths} - set(skipped):
            skipped[missing] = "not found"
    stats = XelaStats()
    written, kept = [], []
    if progress is not None:
        progress(0, len(paths), f"{len(paths)} episodes")
    for i, path in enumerate(paths, start=1):
        name, recording = output_name(path), os.path.basename(path)
        target = os.path.join(out_dir, name)
        try:
            if os.path.exists(target) and not overwrite and episode_baseline(target) == used:
                set_episode_rewards(target, rewards)  # kept, with the rewards saved now
                with np.load(target) as data:
                    stats.add(data["flex_taxel_fk/forces_local"])
                kept.append(name)
            else:
                data = transform_recording(
                    path, load_label(path), to_sim, freq,
                    baseline=baseline, baseline_file=baseline_file, rewards=rewards,
                )
                write_episode(out_dir, name, data)
                stats.add(data["flex_taxel_fk/forces_local"])
                written.append(name)
        except Exception as e:  # noqa: BLE001 - one bad recording does not stop it
            skipped[recording] = f"failed: {e}"
        if progress is not None:
            progress(i, len(paths),
                     f"{i} / {len(paths)} {recording}: {skipped.get(recording, 'done')}")

    mean, std = stats.mean_std()
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, STATS_NAME), "w") as f:
        json.dump({"xela_mean": mean.tolist(), "xela_std": std.tolist(),
                   "values": stats.n.tolist(), "zeros_as_nan": True}, f, indent=1)
    manifest = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "recordings_dir": os.path.abspath(recordings_dir),
        "freq": freq,
        "baseline": used,
        "rewards": rewards,
        "written": written,
        "kept": kept,
        "skipped": skipped,
        "xela_mean": mean.tolist(),
        "xela_std": std.tolist(),
    }
    with open(os.path.join(out_dir, MANIFEST_NAME), "w") as f:
        json.dump(manifest, f, indent=1)
    return manifest
