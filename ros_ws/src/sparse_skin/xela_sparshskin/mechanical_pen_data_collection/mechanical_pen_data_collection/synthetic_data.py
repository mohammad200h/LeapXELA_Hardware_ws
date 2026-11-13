"""Synthetic recordings: the commands replayed in MuJoCo, actions and joints on one grid.

The hand's ``leap_state`` is recorded at ~10 Hz while the commands go out at ~30 Hz (with
jitter), so ``sparsh_processing`` spline-interpolates the joints (and the FK taxel positions)
between samples a third of a step rate apart. This writes, per labelled recording, a recording
of the same format (``playback_recording``) in which every stream is on one ``freq`` grid
(``sparsh_processing.time_grid`` over the span ``transform_recording`` uses):

- ``cmd_q``: the actions. ``clean`` (default): the recorded commands interpolated in time
  (the send jitter, held on a fixed grid, repeats ~15 % of the steps and skips ~13 %) and
  Gaussian smoothed (``SMOOTH_SIGMA_S``: jumps such as a finger's release become ramps).
  ``hold``: the last command sent at or before each step, as ``sparsh_processing`` does;
- ``position`` / ``velocity`` / ``effort``: the joints of a headless MuJoCo (the model, the
  position actuators and the ctrl clamping of ``mujoco_sim_node``, via
  ``sim_collision.SimCollisionChecker``) driven by those actions. ``clean``: settled at the
  first action (``WARMUP_S``), the target ramped from one action to the next, collisions off
  (the scene has no pen, so the fingers would hit one another where the pen keeps them apart;
  ``--contacts`` keeps them). ``hold``: from the recorded pose, each action held.
  ``position`` is in hardware angles (``HardwareToSim.to_hardware``) as in a real recording, the
  sim angles are kept as ``sim_qpos`` (``sim_joint_names``);
- ``xela``: the recorded raw Xela sample nearest each step.

Sparsh-skin processing at the same ``freq`` builds the same grid, so its resampling is then the
identity. The scene has no pen: the sim fingers are not stopped by it.

Run (workspace sourced)::

    python3 -m mechanical_pen_data_collection.synthetic_data --freq 30

which writes ``<recordings>/synthetic_data_30hz/`` (recordings, labels, ``processing.json``),
then its ``sparsh_skin/30hz/`` (``sparsh_processing.write_dataset``) and ``DV3/30hz/``
(``dv3_processing.write_chunks``).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from typing import Callable

import numpy as np

from mechanical_pen_data_collection import dv3_processing, sparsh_processing as sp
from mechanical_pen_data_collection.episode_processing import settings_path
from mechanical_pen_data_collection.playback_recording import (
    PlaybackRecording,
    label_path,
    load_label,
)

DEFAULT_RECORDINGS = "/workspace/LeapXELA_Hardware_ws/ros_ws/demonstrations/compose_playbacks"
FREQ = 30.0
MANIFEST_NAME = "manifest.json"
# Actions: CLEAN (interpolated in time, Gaussian smoothed, ramped in the sim) or HOLD (the last
# command sent at or before each step, held in the sim: the send jitter repeats / skips steps).
CLEAN, HOLD = "clean", "hold"
SMOOTH_SIGMA_S = 0.05  # Gaussian sigma (s) of CLEAN actions (-3 dB at about 2.6 Hz)
# Sim time the hand holds the first action before the first step, to settle (no snap at step 0).
WARMUP_S = 1.0


def synthetic_dir_name(freq: float) -> str:
    return f"synthetic_data_{float(freq):g}hz"


def model_path(path: str = "") -> str:
    """``path``, else the installed ``xela_description`` scene, else the source tree's."""
    if path:
        return path
    try:
        from mechanical_pen_data_collection.sim_collision import default_model_path

        return default_model_path()
    except Exception:  # noqa: BLE001 - workspace not sourced
        src = os.path.realpath(__file__)
        for _ in range(5):
            src = os.path.dirname(src)
        return os.path.join(src, "xela_description", "mjcf", "scene.xml")


def to_sim_array(to_sim: Callable, names: list[str], q_hw: np.ndarray) -> np.ndarray:
    """(N, 16) sim angles (``to_sim.sim_names`` order) of hardware joints ``q_hw``."""
    return np.array([to_sim(names, q) for q in np.atleast_2d(q_hw)], np.float64).reshape(-1, 16)


def to_hw_array(to_sim, names: list[str], q_sim: np.ndarray) -> np.ndarray:
    """(N, 16) hardware angles in ``names`` order of sim joints ``q_sim`` (``sim_names``)."""
    sim_names = list(to_sim.sim_names)
    hw = np.array([to_sim.to_hardware(sim_names, q) for q in q_sim], np.float64)
    return hw[:, [sim_names.index(n) for n in names]]


def held(t: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """Index of the last sample of ``t`` at or before each step of ``grid``."""
    return np.clip(np.searchsorted(t, grid, side="right") - 1, 0, len(t) - 1)


def nearest(t: np.ndarray, grid: np.ndarray) -> np.ndarray:
    right = np.clip(np.searchsorted(t, grid), 1, len(t) - 1)
    return np.where(grid - t[right - 1] <= t[right] - grid, right - 1, right)


def clean_actions(
    cmd_t: np.ndarray, cmd_q: np.ndarray, grid: np.ndarray, sigma_s: float = SMOOTH_SIGMA_S,
) -> np.ndarray:
    """(T, D) commands on ``grid`` without jerk: linearly interpolated in time (no step
    repeated or skipped by the send jitter), then Gaussian smoothed (``sigma_s`` s; no overshoot
    or ringing, step jumps become ramps of about ``4 * sigma_s``). Smoothed over every command
    sent, on ``grid``'s spacing extended both ways, so the episode's ends have no edge effect."""
    from scipy.ndimage import gaussian_filter1d

    t, q = sp._increasing(np.asarray(cmd_t, np.float64), np.asarray(cmd_q, np.float64))
    dt = (grid[-1] - grid[0]) / (len(grid) - 1)
    before = int(np.ceil(max(grid[0] - t[0], 0.0) / dt))
    after = int(np.ceil(max(t[-1] - grid[-1], 0.0) / dt))
    full = grid[0] + dt * np.arange(-before, len(grid) + after)
    full[before:before + len(grid)] = grid
    lin = np.stack([np.interp(full, t, q[:, j]) for j in range(q.shape[1])], axis=1)
    if sigma_s > 0:
        lin = gaussian_filter1d(lin, sigma_s / dt, axis=0, mode="nearest")
    return lin[before:before + len(grid)]


def simulate(
    sim, sim_names: list[str], q0: np.ndarray, ctrl: np.ndarray, grid: np.ndarray,
    ramp: bool = True, warmup_s: float = WARMUP_S, contacts: bool = False,
):
    """(qpos, qvel, effort), each (T, 16) in ``sim_names`` order: the hand at rest at ``q0``
    holding ``ctrl[0]`` for ``warmup_s`` (sim s, not recorded), then from ``grid[k]`` to
    ``grid[k + 1]`` the target ``ctrl[k]`` held, or (``ramp``) moved linearly from ``ctrl[k]``
    to ``ctrl[k + 1]`` every physics step; read at every step. Without ``contacts`` the
    collisions are off (the scene has no pen: the fingers would hit one another or the palm
    where the pen keeps them apart)."""
    import mujoco

    m, d = sim.m, sim.d
    mujoco.mj_resetData(m, d)
    if m.nkey > 0:
        mujoco.mj_resetDataKeyframe(m, d, 0)
    qadr = np.array([sim._qpos[n] for n in sim_names])
    dadr = np.array([m.jnt_dofadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n)]
                     for n in sim_names])
    d.qpos[qadr] = q0
    d.qvel[:] = 0.0
    sim._set_ctrl(sim_names, ctrl[0])
    if contacts:
        m.opt.disableflags &= ~int(mujoco.mjtDisableBit.mjDSBL_CONTACT)
    else:
        m.opt.disableflags |= int(mujoco.mjtDisableBit.mjDSBL_CONTACT)
    mujoco.mj_forward(m, d)
    while d.time < warmup_s - 1e-9:
        mujoco.mj_step(m, d)

    n = len(grid)
    qpos, qvel, eff = (np.empty((n, len(sim_names))) for _ in range(3))

    def read(k: int) -> None:
        qpos[k], qvel[k], eff[k] = d.qpos[qadr], d.qvel[dadr], d.qfrc_actuator[dadr]

    read(0)
    t0 = d.time
    for k in range(n - 1):
        begin = t0 + grid[k] - grid[0]
        target = t0 + grid[k + 1] - grid[0]
        sim._set_ctrl(sim_names, ctrl[k])
        while d.time < target - 1e-9:
            if ramp:
                w = min(max((d.time + m.opt.timestep - begin) / (target - begin), 0.0), 1.0)
                sim._set_ctrl(sim_names, (1.0 - w) * ctrl[k] + w * ctrl[k + 1])
            mujoco.mj_step(m, d)
        read(k + 1)
    return qpos, qvel, eff


def synthesize_recording(
    path: str, label: dict, to_sim, sim, freq: float = FREQ,
    actions: str = CLEAN, sigma_s: float = SMOOTH_SIGMA_S, contacts: bool = False,
) -> tuple[dict[str, np.ndarray], dict]:
    """The arrays of the synthetic recording of ``path`` (labelled ``label``) and stats."""
    span = sp.episode_span(label)
    if isinstance(span, str):
        raise ValueError(span)
    rec = PlaybackRecording.load(path)
    for name in ("xela_t", "state_t", "cmd_t"):
        if len(getattr(rec, name)) < 2:
            raise ValueError(f"no {name.removesuffix('_t')} recorded")
    # The span transform_recording uses, so it builds this same grid again.
    start = max(span[0], rec.xela_t[0], rec.state_t[0])
    end = min(span[1], rec.xela_t[-1], rec.state_t[-1])
    grid = sp.time_grid(start, end, freq)
    if len(grid) < 2:
        raise ValueError(f"episode shorter than one step at {freq:g} Hz")
    names = list(rec.joint_names)
    sim_names = list(to_sim.sim_names)

    # Actions on the grid (sim angles; smoothed there, where the hand moves).
    cmd_i = held(rec.cmd_t, grid)
    if actions == CLEAN:
        all_sim = to_sim_array(to_sim, names, rec.cmd_q)
        cmd_sim = clean_actions(rec.cmd_t, all_sim, grid, sigma_s)
        cmd_hw = to_hw_array(to_sim, names, cmd_sim)
    elif actions == HOLD:
        cmd_hw = np.asarray(rec.cmd_q, np.float64)[cmd_i]
        cmd_sim = to_sim_array(to_sim, names, cmd_hw)
    else:
        raise ValueError(f"actions {actions!r}: not {CLEAN!r} / {HOLD!r}")

    # Joints: the sim driven by them, settled at the first one (CLEAN), or from the recorded
    # pose at the first step (HOLD, as recorded).
    if actions == CLEAN:
        q0, warmup = cmd_sim[0], WARMUP_S
    else:
        state_t, position = sp._increasing(np.asarray(rec.state_t, np.float64),
                                           np.asarray(rec.position, np.float64))
        q0 = to_sim_array(to_sim, names, position[nearest(state_t, grid[:1])])[0]
        warmup = 0.0
    qpos, qvel, eff = simulate(sim, sim_names, q0, cmd_sim, grid, ramp=actions == CLEAN,
                               warmup_s=warmup, contacts=contacts)
    pos_hw = to_hw_array(to_sim, names, qpos)
    roundtrip = float(np.abs(to_sim_array(to_sim, names, pos_hw) - qpos).max())
    cols = [sim_names.index(n) for n in names]

    # Forces: the raw sample nearest each step (outliers / baseline: Sparsh processing).
    xela_t, xela = sp._increasing(np.asarray(rec.xela_t, np.float64), np.asarray(rec.xela))
    xela_grid = np.asarray(xela, np.float32)[nearest(xela_t, grid)]

    meta = dict(rec.meta)
    meta["synthetic"] = {
        "freq": freq, "source": os.path.abspath(path), "model": sim.model_path,
        "start": round(float(grid[0]), 4), "end": round(float(grid[-1]), 4),
        "steps": len(grid),
        "actions": actions,
        "smooth_sigma_s": sigma_s if actions == CLEAN else None,
        "warmup_s": warmup,
        "contacts": contacts,
        "cmd_q": ("recorded commands interpolated in time, Gaussian smoothed (sim angles)"
                  if actions == CLEAN else "the recorded command held at each step"),
        "position": "MuJoCo replay of cmd_q (" + ("ramped between steps"
                     if actions == CLEAN else "held at each step") + "), hardware angles",
        "xela": "raw sample nearest each step",
        "source_rates_hz": {k: round(sp.stream_rate(getattr(rec, t)), 2)
                            for k, t in (("cmd", "cmd_t"), ("state", "state_t"),
                                         ("xela", "xela_t"))},
    }
    with np.load(path, allow_pickle=False) as data:
        arrays = {k: data[k] for k in data.files}
    cmd_local = arrays.get("cmd_local")
    arrays.update(
        cmd_t=grid, cmd_q=cmd_hw,
        state_t=grid, position=pos_hw, velocity=qvel[:, cols], effort=eff[:, cols],
        xela_t=grid, xela=xela_grid,
        sim_qpos=qpos, sim_joint_names=np.array(sim_names),
        meta=np.array(json.dumps(meta)),
    )
    if cmd_local is not None and len(cmd_local) == len(rec.cmd_t):
        arrays["cmd_local"] = cmd_local[cmd_i]
    stats = {
        "steps": len(grid),
        "roundtrip_err": roundtrip,
        "track_err_mean": float(np.abs(qpos[1:] - cmd_sim[:-1]).mean()),
    }
    return arrays, stats


def write_synthetic(
    recordings_dir: str, out_dir: str, to_sim, sim, freq: float = FREQ,
    limit: int | None = None, progress: Callable[[int, int, str], None] | None = None,
    actions: str = CLEAN, sigma_s: float = SMOOTH_SIGMA_S, contacts: bool = False,
) -> dict:
    """Writes the synthetic recording (same name), its label and ``processing.json`` of every
    labelled episode of ``recordings_dir`` to ``out_dir``. Returns the manifest."""
    paths, skipped = sp.eligible_episodes(recordings_dir)
    if limit:
        paths = paths[:limit]
    os.makedirs(out_dir, exist_ok=True)
    if os.path.isfile(settings_path(recordings_dir)):
        shutil.copy2(settings_path(recordings_dir), settings_path(out_dir))
    written, worst_rt, track = [], 0.0, []
    for i, path in enumerate(paths, start=1):
        name = os.path.basename(path)
        try:
            arrays, stats = synthesize_recording(
                path, load_label(path), to_sim, sim, freq, actions, sigma_s, contacts)
            target = os.path.join(out_dir, name)
            np.savez_compressed(target, **arrays)
            shutil.copy2(label_path(path), label_path(target))
            written.append(name)
            worst_rt = max(worst_rt, stats["roundtrip_err"])
            track.append(stats["track_err_mean"])
            text = f"{stats['steps']} steps, track {stats['track_err_mean']:.4f} rad"
        except Exception as e:  # noqa: BLE001 - one bad recording does not stop it
            skipped[name] = f"failed: {e}"
            text = skipped[name]
        if progress is not None:
            progress(i, len(paths), f"{i} / {len(paths)} {name}: {text}")
    manifest = {
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "recordings_dir": os.path.abspath(recordings_dir),
        "freq": freq,
        "model": sim.model_path,
        "actions": actions,
        "smooth_sigma_s": sigma_s if actions == CLEAN else None,
        "contacts": contacts,
        "written": written,
        "skipped": skipped,
        "max_roundtrip_err_rad": worst_rt,
        "mean_track_err_rad": float(np.mean(track)) if track else None,
    }
    with open(os.path.join(out_dir, MANIFEST_NAME), "w") as f:
        json.dump(manifest, f, indent=1)
    return manifest


def latest_baseline(recordings_dir: str) -> str:
    """The baseline file of the newest Sparsh-skin output of ``recordings_dir`` ("" if none)."""
    best, baseline = 0.0, ""
    for folder in sp.rate_dirs(recordings_dir).values():
        path = os.path.join(folder, sp.MANIFEST_NAME)
        try:
            with open(path) as f:
                used = json.load(f).get("baseline") or ""
        except (OSError, ValueError):
            continue
        if os.path.isfile(used) and os.path.getmtime(path) > best:
            best, baseline = os.path.getmtime(path), used
    return baseline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--recordings", default=DEFAULT_RECORDINGS)
    parser.add_argument("--freq", type=float, default=FREQ)
    parser.add_argument("--out", default="", help="default: <recordings>/synthetic_data_<f>hz")
    parser.add_argument("--baseline", default=None,
                        help="Xela baseline file (default: that of the newest sparsh_skin "
                             "output; '' for each recording's own)")
    parser.add_argument("--model", default="", help="MuJoCo scene.xml")
    parser.add_argument("--actions", choices=(CLEAN, HOLD), default=CLEAN,
                        help="clean: interpolated, smoothed, ramped (default); hold: as recorded")
    parser.add_argument("--sigma", type=float, default=SMOOTH_SIGMA_S,
                        help="Gaussian sigma (s) of clean actions")
    parser.add_argument("--contacts", action="store_true",
                        help="keep the sim's collisions on (off by default: no pen in the scene)")
    parser.add_argument("--limit", type=int, default=None, help="first N episodes only")
    parser.add_argument("--skip-synth", action="store_true")
    parser.add_argument("--skip-sparsh", action="store_true")
    parser.add_argument("--skip-dv3", action="store_true")
    args = parser.parse_args(argv)

    from mechanical_pen_data_collection.joint_conversion import HardwareToSim
    from mechanical_pen_data_collection.sim_collision import SimCollisionChecker

    out_dir = args.out or os.path.join(args.recordings, synthetic_dir_name(args.freq))
    to_sim = HardwareToSim()

    def report(done: int, total: int, text: str) -> None:
        if done:
            print(text, flush=True)

    if not args.skip_synth:
        sim = SimCollisionChecker(model_path(args.model))
        print(f"Synthesizing {args.recordings} -> {out_dir} at {args.freq:g} Hz "
              f"({sim.model_path})", flush=True)
        manifest = write_synthetic(args.recordings, out_dir, to_sim, sim, args.freq,
                                   args.limit, report, args.actions, args.sigma,
                                   args.contacts)
        print(f"synthetic: {len(manifest['written'])} written, {len(manifest['skipped'])} "
              f"skipped, max hw<->sim round trip {manifest['max_roundtrip_err_rad']:.2e} rad, "
              f"mean tracking error {manifest['mean_track_err_rad']} rad", flush=True)

    sparsh_dir = sp.rate_dir(out_dir, args.freq)
    if not args.skip_sparsh:
        baseline = latest_baseline(args.recordings) if args.baseline is None else args.baseline
        print(f"Sparsh-skin -> {sparsh_dir}, baseline {baseline or 'of each recording'}",
              flush=True)
        manifest = sp.write_dataset(out_dir, sparsh_dir, to_sim, freq=args.freq,
                                    overwrite=True, progress=report, baseline_file=baseline)
        print(f"sparsh: {len(manifest['written'])} written, {len(manifest['skipped'])} skipped",
              flush=True)

    if not args.skip_dv3:
        dv3_dir = sp.rate_dir(out_dir, args.freq, dv3_processing.DEFAULT_OUTPUT_NAME)
        print(f"DreamerV3 -> {dv3_dir}", flush=True)
        manifest = dv3_processing.write_chunks(sparsh_dir, dv3_dir)
        print(f"dv3: {len(manifest['written'])} chunks, steps {manifest['steps']}, "
              f"{len(manifest['skipped'])} skipped", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
