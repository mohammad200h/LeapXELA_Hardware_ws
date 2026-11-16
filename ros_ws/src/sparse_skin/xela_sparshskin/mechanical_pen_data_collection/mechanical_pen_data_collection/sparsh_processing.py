"""Sparsh-skin preprocessing of the Play on hand episodes, written for the LEQ_DV3 world model.

Follows Sparsh-skin's Xela pipeline (sparsh-multisensory-touch ``XelaSSLDataset`` /
``generate_policy_dataset.py``) on each labelled episode (``episode_start`` to ``terminal``,
confirmed, of a ``success`` / ``failure`` recording):

- a common ``np.linspace`` time grid at ``freq`` (100 Hz by default, ``FREQ_CHOICES`` on the
  Processing tab) over the span every stream covers;
- Xela x, y, z and the joints resampled onto it (``resample``): interpolated with
  ``CubicSpline`` when the stream is recorded slower than ``freq`` (or about as fast), or, when
  it is recorded faster (by more than ``DROP_MARGIN``), its extra samples dropped: each step
  takes the recorded sample nearest to it (``resample_mode``); the commands are held (the last
  one sent at or before each step: repeated when slower than ``freq``, dropped when faster);
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
sets them again on the episodes written, ``apply_rewards``; the same values also as
``rewards/manual``; Process reward with reward models ticked adds ``rewards/<source>`` for each
and puts the primary one in ``rewards``, ``set_reward_sources``), and ``metadata_json`` (``terminated_by_env``: a success, or a failure
whose ``terminal`` was marked by hand; not one Process failure added; ``baseline``: the
baseline file, or "recording"; ``rewards``: the values used; ``resampling``: each stream's
recorded rate and how it was resampled). An episode already written with another baseline or
step rate is rewritten.
"""

from __future__ import annotations

import json
import os
import re
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
# Step rates offered on the Processing tab (Hz).
FREQ_CHOICES = (100.0, 50.0, 30.0, 25.0, 20.0, 15.0, 10.0, 5.0)
# A stream is decimated (samples dropped) only when recorded more than this many times faster
# than the step rate; otherwise it is interpolated (Xela, ~101 Hz, is interpolated at 100 Hz).
DROP_MARGIN = 1.05
INTERPOLATE, DROP = "interpolate", "drop"
HOLD_REPEAT, HOLD_DROP = "hold (repeat)", "hold (drop)"
# The recorded streams: (key, its time array, text). ``positions`` are FK of the joints.
STREAMS = (
    ("xela", "xela_t", "Xela forces"),
    ("joints", "state_t", "joints (leap_state) -> FK taxel positions"),
    ("actions", "cmd_t", "commands (actions)"),
)
XELA_LOW, XELA_HIGH = 20000.0, 60000.0  # valid raw Xela range (outside: dead taxel, 0)
EPISODE_PREFIX = "episode_"
STATS_NAME = "sparsh_stats.json"
MANIFEST_NAME = "manifest.json"
DEFAULT_OUTPUT_NAME = "sparsh_skin"  # next to the recordings, a folder per rate in it
RATE_DIR_RE = re.compile(r"^(\d+(?:\.\d+)?)hz$")


def rate_folder_name(freq: float) -> str:
    """The folder of a step rate's episodes: ``100hz``, ``25hz``, ``12.5hz``."""
    return f"{float(freq):g}hz"


def rate_dir(recordings_dir: str, freq: float, output_name: str = DEFAULT_OUTPUT_NAME) -> str:
    """``<recordings_dir>/sparsh_skin/<rate>hz``: the episodes processed at ``freq``; only a
    transform at the same rate overwrites them."""
    return os.path.join(recordings_dir, output_name, rate_folder_name(freq))


def rate_dirs(recordings_dir: str, output_name: str = DEFAULT_OUTPUT_NAME) -> dict[float, str]:
    """{rate (Hz): folder} of the rates processed so far, fastest first."""
    root = os.path.join(recordings_dir, output_name)
    found = {}
    for name in os.listdir(root) if os.path.isdir(root) else []:
        match = RATE_DIR_RE.match(name)
        if match and os.path.isdir(os.path.join(root, name)):
            found[float(match.group(1))] = os.path.join(root, name)
    return dict(sorted(found.items(), reverse=True))


def count_episodes(folder: str) -> int:
    return sum(n.startswith(EPISODE_PREFIX) and n.endswith(".npz")
               for n in (os.listdir(folder) if os.path.isdir(folder) else []))


def migrate_flat_output(
    recordings_dir: str, output_name: str = DEFAULT_OUTPUT_NAME, files_re: str = "",
) -> str | None:
    """Moves output written straight into ``<recordings_dir>/<output_name>/`` (before the
    folder per rate) into its rate's folder, the rate from its ``manifest.json`` (``freq``,
    100 Hz if none). ``files_re``: the files to move (default: ``episode_*.npz``); the manifest
    and ``sparsh_stats.json`` go along. Returns the folder moved to, or None."""
    root = os.path.join(recordings_dir, output_name)
    if not os.path.isdir(root):
        return None
    pattern = re.compile(files_re or rf"^{EPISODE_PREFIX}.*\.npz$")
    loose = [n for n in os.listdir(root)
             if os.path.isfile(os.path.join(root, n)) and pattern.match(n)]
    if not loose:
        return None
    try:
        with open(os.path.join(root, MANIFEST_NAME)) as f:
            freq = float(json.load(f).get("freq") or FREQ)
    except (OSError, ValueError, TypeError, AttributeError):
        freq = FREQ
    target = rate_dir(recordings_dir, freq, output_name)
    os.makedirs(target, exist_ok=True)
    for name in loose + [n for n in (MANIFEST_NAME, STATS_NAME)
                         if os.path.isfile(os.path.join(root, n))]:
        os.replace(os.path.join(root, name), os.path.join(target, name))
    return target


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


def stream_rate(t: np.ndarray) -> float:
    """A stream's recorded rate (Hz): 1 / its median sample interval (0: fewer than 2)."""
    t = np.asarray(t, np.float64)
    if len(t) < 2:
        return 0.0
    dt = np.median(np.diff(t))
    return float(1.0 / dt) if dt > 0 else 0.0


def resample_mode(source_hz: float, freq: float, held: bool = False) -> str:
    """How a stream recorded at ``source_hz`` gets onto a ``freq`` grid: ``DROP`` when it is
    faster by more than ``DROP_MARGIN``, else ``INTERPOLATE``; a ``held`` stream (commands) is
    ``HOLD_DROP`` / ``HOLD_REPEAT`` instead."""
    faster = source_hz > freq * DROP_MARGIN
    if held:
        return HOLD_DROP if faster else HOLD_REPEAT
    return DROP if faster else INTERPOLATE


def resample(t: np.ndarray, values: np.ndarray, grid: np.ndarray, mode: str) -> np.ndarray:
    """``values`` (stamped ``t``, strictly increasing) on ``grid``: ``INTERPOLATE`` with a
    ``CubicSpline``, ``DROP`` the recorded sample nearest each step (the others dropped)."""
    if mode == INTERPOLATE:
        return CubicSpline(t, values, axis=0)(grid)
    right = np.clip(np.searchsorted(t, grid), 1, len(t) - 1)
    nearest = np.where(grid - t[right - 1] <= t[right] - grid, right - 1, right)
    return np.asarray(values)[nearest]


def recording_rates(path: str) -> dict[str, float]:
    """{stream key: recorded rate (Hz)} of a recording (only its time arrays are read)."""
    with np.load(path, allow_pickle=False) as data:
        return {key: stream_rate(data[t_name]) if t_name in data.files else 0.0
                for key, t_name, _ in STREAMS}


def typical_rates(paths: list[str]) -> dict[str, float]:
    """{stream key: median recorded rate (Hz)} over ``paths`` (unreadable ones skipped)."""
    rates: dict[str, list[float]] = {key: [] for key, _, _ in STREAMS}
    for path in paths:
        try:
            for key, hz in recording_rates(path).items():
                if hz > 0:
                    rates[key].append(hz)
        except Exception:  # noqa: BLE001
            continue
    return {key: float(np.median(v)) if v else 0.0 for key, v in rates.items()}


def resampling_plan(rates: dict[str, float], freq: float) -> dict[str, str]:
    """{stream key: mode} for streams recorded at ``rates`` on a ``freq`` grid."""
    return {key: resample_mode(rates.get(key, 0.0), freq, held=key == "actions")
            for key, _, _ in STREAMS}


def _increasing(t: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Drops samples not later than every one before them (a repeated or backwards stamp;
    CubicSpline needs strictly increasing times)."""
    keep = np.concatenate([[True], t[1:] > np.maximum.accumulate(t)[:-1]])
    return t[keep], values[keep]


def preprocess_xela(
    xela_t: np.ndarray, xela: np.ndarray, baseline: np.ndarray, grid: np.ndarray,
    mode: str = INTERPOLATE,
) -> np.ndarray:
    """(T, 368, 3) Xela on ``grid`` in FK order: resampled (``mode``, ``resample``), outliers
    0, baseline subtracted where x is not 0 (``xela`` and ``baseline`` by hardware id)."""
    t, x = _increasing(np.asarray(xela_t, np.float64), np.asarray(xela, np.float64))
    return clean_xela(np.array(resample(t, x, grid, mode), np.float64), baseline)


def clean_xela(xela: np.ndarray, baseline: np.ndarray) -> np.ndarray:
    """(..., 368, 3) raw Xela by hardware id -> FK order with outliers 0 and the baseline
    subtracted where x is not 0: ``preprocess_xela`` after resampling, and ``live_obs``."""
    out = np.array(xela, np.float64)
    out = np.where((out < XELA_LOW) | (out > XELA_HIGH), 0.0, out)
    mask = out[..., 0] != 0
    out[mask] -= np.broadcast_to(np.asarray(baseline, np.float64), out.shape)[mask]
    return out[..., fk.TAXEL_IDS_IN_FK_ORDER, :].astype(np.float32)


def sim_joints(to_sim: Callable, names: list[str], q_hw: np.ndarray) -> np.ndarray:
    """(N, 16) hardware joints ``q_hw`` (columns ``names``) as sim angles in FK order."""
    sim = np.array([to_sim(names, q) for q in q_hw], dtype=np.float64).reshape(-1, 16)
    return fk.joint_angles_in_fk_order(list(to_sim.sim_names), sim).astype(np.float64)


def live_obs(
    xela: np.ndarray, baseline: np.ndarray, to_sim: Callable, names: list[str],
    q_hw: np.ndarray, urdf_path=None,
) -> np.ndarray:
    """One live Sparsh-skin step, as an episode's: (368, 6) float32 per taxel in FK order,
    ``flex_taxel_fk/forces_local`` then ``flex_taxel_fk/positions``. ``xela`` (368, 3) raw by
    hardware id (the newest ``/xServTopic`` reading), ``q_hw`` (16,) hardware joints in
    ``names`` order (the newest ``leap_state``). Same code as ``transform_recording``."""
    forces = clean_xela(np.asarray(xela, np.float64)[None], baseline)[0]
    joints = sim_joints(to_sim, names, np.asarray(q_hw, np.float64)[None])
    positions, _ = fk.get_fk_taxel_frames(joints, urdf_path, mujoco_world=False)
    return np.concatenate([forces, np.asarray(positions, np.float32)[0]], -1)


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


# Each reward of an episode: ``rewards/<source>`` (``set_reward_sources``); the primary one is
# also ``rewards``, named by the metadata's ``reward_primary``.
REWARD_PREFIX = "rewards/"
MANUAL = "manual"
REWARD_PRIMARY_KEY = "reward_primary"


def set_episode_rewards(path: str, rewards: dict[str, float]) -> str | None:
    """Sets the manual rewards of an episode file (``rewards/manual`` and its metadata's
    ``rewards``) to ``rewards``, and ``rewards`` too while the manual one is its primary
    reward, unless it has them already. Returns its label."""
    with np.load(path) as data:
        arrays = {k: data[k] for k in data.files}
    metadata = json.loads(str(arrays["metadata_json"]))
    manual_key = REWARD_PREFIX + MANUAL
    if metadata.get("rewards") != rewards or manual_key not in arrays:
        manual = episode_rewards(metadata.get("label"), len(arrays["rewards"]), rewards)
        arrays[manual_key] = manual
        if metadata.get(REWARD_PRIMARY_KEY, MANUAL) == MANUAL:
            arrays["rewards"] = manual
        metadata["rewards"] = dict(rewards)
        arrays["metadata_json"] = np.array(json.dumps(metadata))
        np.savez_compressed(path, **arrays)
    return metadata.get("label")


def episode_grid(metadata: dict) -> np.ndarray:
    """The time (s, of the recording) of each step of an episode, from its metadata."""
    return np.linspace(float(metadata["t_start"]), float(metadata["t_end"]),
                       int(metadata["steps"]))


def model_rewards_on_grid(
    method: str, grid: np.ndarray, t: np.ndarray, reward: np.ndarray, terms: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    """A reward model's rewards (from reward_models' inference: per step at times ``t``, at
    the model's own step rate) at the episode's steps ``grid``, as ``rewards/<name>`` arrays:
    ``rank2reward`` its reward (a value per state: interpolated); ``sarm`` SARM's progress phi
    (interpolated) and ``sarm_delta`` phi_t - phi_{t-1} on the grid (0 at the first step), so
    its sum over the episode stays the progress made whatever the step rate."""
    t = np.asarray(t, np.float64)
    if method == "sarm":
        phi = np.interp(grid, t, np.asarray(terms["progress"], np.float64)).astype(np.float32)
        delta = np.concatenate([[0.0], np.diff(phi)]).astype(np.float32)
        return {"sarm": phi, "sarm_delta": delta}
    return {method: np.interp(grid, t, np.asarray(reward, np.float64)).astype(np.float32)}


def set_reward_sources(
    path: str, rewards: dict[str, float], include: list[str],
    models: dict[str, np.ndarray], primary: str, sources: dict[str, str],
) -> str | None:
    """Process reward with reward models: the rewards of an episode file are ``rewards/<name>``
    of each source in ``include`` (``manual``: ``rewards``' values; the models' arrays from
    ``model_rewards_on_grid`` in ``models``), the others removed; ``rewards`` is the one of
    ``primary``. Its metadata gets ``reward_primary`` and ``reward_models`` ({name: the run
    used}, ``sources``). Returns its label."""
    with np.load(path) as data:
        arrays = {k: data[k] for k in data.files if not k.startswith(REWARD_PREFIX)}
    metadata = json.loads(str(arrays["metadata_json"]))
    steps = len(arrays["rewards"])
    if MANUAL in include:
        arrays[REWARD_PREFIX + MANUAL] = episode_rewards(metadata.get("label"), steps, rewards)
    for name, values in models.items():
        if len(values) != steps:
            raise ValueError(f"{name} has {len(values)} steps, the episode {steps}")
        arrays[REWARD_PREFIX + name] = np.asarray(values, np.float32)
    if REWARD_PREFIX + primary not in arrays:
        raise ValueError(f"no '{primary}' reward for the primary reward")
    arrays["rewards"] = arrays[REWARD_PREFIX + primary]
    metadata["rewards"] = dict(rewards)
    metadata[REWARD_PRIMARY_KEY] = primary
    metadata["reward_models"] = dict(sources)
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
    return episode_metadata(path).get("baseline")


def episode_metadata(path: str) -> dict:
    with np.load(path) as data:
        return json.loads(str(data["metadata_json"]))


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

    rates = {key: stream_rate(getattr(rec, t_name)) for key, t_name, _ in STREAMS}
    plan = resampling_plan(rates, freq)
    forces = preprocess_xela(rec.xela_t, rec.xela, baseline, grid, plan["xela"])

    state_t, q = _increasing(rec.state_t, sim_joints(to_sim, rec.joint_names, rec.position))
    joints = resample(state_t, q, grid, plan["joints"])
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
        "resampling": {key: {"source_hz": round(rates[key], 2), "mode": plan[key]}
                       for key in plan},
        "joint_order": fk.LEAP_JOINT_ORDER,
        "taxel_order": "XELA_FLATTEN_ORDER",
        "forces_local": "Sparsh-skin preprocessed Xela counts (outliers 0, baseline subtracted)",
        "baseline": os.path.abspath(baseline_file) if baseline_file else RECORDING_BASELINE,
        "rewards": rewards,
        REWARD_PRIMARY_KEY: MANUAL,
        "positions": "FK taxel positions (m), hand base frame",
        "actions": "sim joint targets (rad), last command at each step",
    }
    return {
        "actions": actions.astype(np.float32),
        "flex_taxel_fk/forces_local": forces,
        "flex_taxel_fk/positions": positions.astype(np.float32),
        "rewards": episode_rewards(label.get("label"), len(grid), rewards),
        REWARD_PREFIX + MANUAL: episode_rewards(label.get("label"), len(grid), rewards),
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
    kept unless ``overwrite`` or written with another baseline or step rate (``out_dir`` is
    the rate's own folder, ``rate_dir``, so other rates are not touched). ``progress(done, total,
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
            meta = episode_metadata(target) if os.path.exists(target) else {}
            if (meta and not overwrite and meta.get("baseline") == used
                    and abs(float(meta.get("freq", FREQ)) - freq) < 1e-6):
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
