"""Finger-finger collision check of a Test in sim plan, in a headless MuJoCo.

Runs the same model as ``mujoco_sim_node`` (``xela_description/mjcf/scene.xml``) with the same
position actuators and the same contact rule (a contact between bodies of two different fingers,
``th_`` / ``if_`` / ``mf_`` / ``rf_``), but steps it as fast as it can instead of in real time,
so many plans can be checked one after another. The commands change at the command rate, as
when the Compose tab streams them to the sim.

A plan is what Test in sim plays: the hand pose ``base`` (hardware joints ``names``) and, per
finger, ``(columns, take, (start, end), delay)``: the take's joints go to ``columns`` and run from
take time ``start`` to ``end`` (backwards when ``end < start``) after ``delay`` s, holding
``start`` before and ``end`` after.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np

FINGER_PREFIXES = ("th", "if", "mf", "rf")
# Sim time after the plan ends, for the fingers to get to its last command.
SETTLE_S = 0.5


def default_model_path() -> str:
    from ament_index_python.packages import get_package_share_directory

    return os.path.join(get_package_share_directory("xela_description"), "mjcf", "scene.xml")


def plan_end(parts: Sequence) -> float:
    return max((delay + abs(end - start) for _, _, (start, end), delay in parts), default=0.0)


def plan_pose(base: np.ndarray, parts: Sequence, elapsed: float) -> np.ndarray:
    """Hardware joints of the plan ``elapsed`` s from its start."""
    q = np.array(base, dtype=float)
    for cols, take, (start, end), delay in parts:
        run = min(max(elapsed - delay, 0.0), abs(end - start))
        local = start + np.sign(end - start) * run
        q[cols] = [np.interp(local, take.t, take.q[:, j]) for j in range(take.q.shape[1])]
    return q


@dataclass
class Touch:
    first_t: float  # plan time of the first contact, of any depth (s)
    depth: float  # largest penetration (m)
    bodies: tuple[str, str]  # bodies of the deepest contact


@dataclass
class CollisionResult:
    duration: float
    # Every finger pair that touched at all (however shallow) -> its first touch and max depth.
    touches: dict[tuple[str, str], Touch] = field(default_factory=dict)
    partial: bool = False  # ended early (``give_up``)

    def counted(self, min_depth: float = 0.0) -> dict[tuple[str, str], Touch]:
        """The pairs that got at least ``min_depth`` (m) deep: shallower touches, e.g. collision
        geoms that reach just past the visual meshes, are not collisions."""
        return {pair: t for pair, t in self.touches.items() if t.depth >= min_depth}

    def collides(self, min_depth: float = 0.0) -> bool:
        return bool(self.counted(min_depth))


class SimCollisionChecker:
    """Loads the sim model once; ``check`` runs a plan in it from a reset."""

    def __init__(self, model_path: str | None = None) -> None:
        import mujoco

        self._mj = mujoco
        self.model_path = model_path or default_model_path()
        self.m = mujoco.MjModel.from_xml_path(self.model_path)
        self.d = mujoco.MjData(self.m)
        m = self.m
        self._actuator: dict[str, int] = {}
        self._qpos: dict[str, int] = {}
        for a in range(m.nu):
            if m.actuator_trntype[a] != mujoco.mjtTrn.mjTRN_JOINT:
                continue
            j = m.actuator_trnid[a, 0]
            name = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, j)
            if name:
                self._actuator[name] = a
                self._qpos[name] = m.jnt_qposadr[j]
        # Finger of every body: that of its nearest ancestor (or itself) named "<finger>_...".
        self._finger = [-1] * m.nbody
        for b in range(1, m.nbody):
            a = b
            while a > 0 and self._finger[b] < 0:
                name = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, a) or ""
                self._finger[b] = next(
                    (i for i, f in enumerate(FINGER_PREFIXES) if name.startswith(f + "_")), -1
                )
                a = m.body_parentid[a]

    def check(
        self,
        names: list[str],
        base: np.ndarray,
        parts: Sequence,
        to_sim: Callable[[list[str], np.ndarray], tuple[list[str], np.ndarray]],
        rate_hz: float,
        settle_s: float = SETTLE_S,
        should_stop: Callable[[], bool] | None = None,
        give_up: Callable[[CollisionResult], bool] | None = None,
    ) -> CollisionResult | None:
        """Runs the plan; the finger pairs that touched (None if ``should_stop`` said so).
        ``to_sim`` turns hardware joints into (sim joint names, positions). The hand starts at
        rest at the plan's first pose. With ``give_up``, the run ends early (``partial``) once it
        returns True for the touches so far."""
        mj, m, d = self._mj, self.m, self.d
        mj.mj_resetData(m, d)
        if m.nkey > 0:
            mj.mj_resetDataKeyframe(m, d, 0)
        sim_names, q = to_sim(names, plan_pose(base, parts, 0.0))
        self._set_ctrl(sim_names, q)
        for name, value in zip(sim_names, q):
            if name in self._qpos:
                d.qpos[self._qpos[name]] = value
        d.qvel[:] = 0.0
        mj.mj_forward(m, d)
        duration = plan_end(parts)
        result = CollisionResult(duration)
        self._collect(result, 0.0)
        if give_up is not None and give_up(result):
            result.partial = True
            return result
        period = 1.0 / rate_hz
        steps = max(int(round(period / m.opt.timestep)), 1)
        t = 0.0
        while t < duration + settle_s:
            if should_stop is not None and should_stop():
                return None
            t += period
            sim_names, q = to_sim(names, plan_pose(base, parts, min(t, duration)))
            self._set_ctrl(sim_names, q)
            for _ in range(steps):
                mj.mj_step(m, d)
                self._collect(result, min(t, duration))
            if give_up is not None and give_up(result):
                result.partial = True
                return result
        return result

    def ctrl_range(self, joint: str) -> tuple[float, float] | None:
        """(min, max) command of the actuator of sim joint ``joint`` (None if unlimited)."""
        a = self._actuator.get(joint)
        if a is None or not self.m.actuator_ctrllimited[a]:
            return None
        lo, hi = self.m.actuator_ctrlrange[a]
        return float(lo), float(hi)

    def clear_pair(
        self,
        names: list[str],
        base: np.ndarray,
        parts: Sequence,
        to_sim: Callable[[list[str], np.ndarray], tuple[list[str], np.ndarray]],
        rate_hz: float,
        joint: str,
        pair: tuple[str, str],
        min_depth: float,
        before: CollisionResult,
        step: float = 0.02,
        should_stop: Callable[[], bool] | None = None,
    ) -> tuple[float, CollisionResult] | None:
        """Moves the held joint ``joint`` (hardware joint of ``base``, not driven by any part)
        the least it can, both ways in ``step`` rad steps within its actuator's range, until
        ``pair`` no longer collides (``min_depth`` deep) and no pair collides that did not in
        ``before``. The joint value and the plan's result with it; None if no value does."""
        col = names.index(joint)
        start = float(base[col])
        allowed = set(before.counted(min_depth)) - {pair}
        sim_names, q = to_sim(names, base)
        k = list(sim_names).index(joint)
        limits = self.ctrl_range(joint)

        def in_range(value: float) -> bool:
            if limits is None:
                return True
            trial = np.array(base, dtype=float)
            trial[col] = value
            v = to_sim(names, trial)[1][k]
            return limits[0] - 1e-6 <= v <= limits[1] + 1e-6

        def bad(result: CollisionResult) -> bool:
            return any(p not in allowed for p in result.counted(min_depth))

        n = 1
        while True:
            candidates = [start + n * step, start - n * step]
            candidates = [v for v in candidates if in_range(v)]
            if not candidates:
                return None
            for value in candidates:
                if should_stop is not None and should_stop():
                    return None
                trial = np.array(base, dtype=float)
                trial[col] = value
                result = self.check(names, trial, parts, to_sim, rate_hz,
                                    should_stop=should_stop, give_up=bad)
                if result is None:
                    return None
                if not result.partial and not bad(result):
                    return value, result
            n += 1

    def _set_ctrl(self, sim_names: list[str], q: np.ndarray) -> None:
        m, d = self.m, self.d
        for name, value in zip(sim_names, q):
            a = self._actuator.get(name)
            if a is None:
                continue
            if m.actuator_ctrllimited[a]:
                value = np.clip(value, *m.actuator_ctrlrange[a])
            d.ctrl[a] = value

    def _collect(self, result: CollisionResult, t: float) -> None:
        mj, m, d = self._mj, self.m, self.d
        for i in range(d.ncon):
            c = d.contact[i]
            if c.exclude != 0 or c.geom[0] < 0 or c.geom[1] < 0:
                continue
            b1, b2 = m.geom_bodyid[c.geom[0]], m.geom_bodyid[c.geom[1]]
            f1, f2 = self._finger[b1], self._finger[b2]
            if f1 < 0 or f2 < 0 or f1 == f2:
                continue
            if f1 > f2:
                f1, f2, b1, b2 = f2, f1, b2, b1
            pair = (FINGER_PREFIXES[f1], FINGER_PREFIXES[f2])
            depth = max(0.0, -float(c.dist))
            touch = result.touches.get(pair)
            if touch is None:
                result.touches[pair] = Touch(round(t, 3), depth, (
                    mj.mj_id2name(m, mj.mjtObj.mjOBJ_BODY, b1),
                    mj.mj_id2name(m, mj.mjtObj.mjOBJ_BODY, b2),
                ))
            elif depth > touch.depth:
                touch.depth = depth
                touch.bodies = (
                    mj.mj_id2name(m, mj.mjtObj.mjOBJ_BODY, b1),
                    mj.mj_id2name(m, mj.mjtObj.mjOBJ_BODY, b2),
                )
