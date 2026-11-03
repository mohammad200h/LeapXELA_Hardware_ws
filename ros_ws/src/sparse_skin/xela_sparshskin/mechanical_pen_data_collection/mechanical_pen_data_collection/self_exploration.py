"""Goal poses for record_demonstration's "Learning about your own body" tab, without ROS or Qt.

The hand learns its own body by moving from the open pose (0 on every sim joint) to goals and
back, on the MuJoCo model ``hand_ik`` plans on (``HandIK``). Three kinds of goals:

- Workspace exploration (``sample_workspace_goal``): uniform in the joint ranges, no two parts
  of the hand pressing into one another, and novel: further (L2 of the sim joint angles, rad)
  than a threshold from every goal and every trajectory point already played on the hand
  (``ExploredSet``, rebuilt from the saved episodes by ``ExploredSet.from_episodes``).
- Fingers -> palm (``SelfTouchSolver.palm_touch``): every combination of fingers
  (``palm_combinations``, the 15 non-empty subsets of Thumb / Index / Middle / Ring) touches
  the palm's skin pads (``PALM_PADS``, the ``uspa46`` patches) with their fingertips at once.
  Each finger is its own chain on the fixed palm, so each finger's touch is found alone (the
  other fingers open) and the touches are put together; the thumb, which crosses the palm,
  is found last among the other fingers already there.
- Thumb -> fingers (``SelfTouchSolver.thumb_touch``): the thumb's fingertip touches one sensor
  pad of the Index / Middle / Ring finger (``THUMB_TARGETS``: its fingertip ``<f>_ds_tip`` and
  its ``uspa44`` pads ``md`` / ``px`` / ``bs``).

A touch is found by choosing goals and checking them (``SelfTouchSolver.sample_touch``): the
joints of the touching finger (and of the finger touched) at random, MuJoCo reset to the goal
(``reset_contacts``: ``mj_resetData``, qpos and the actuators' targets set to it,
``mj_forward``, as the sim would be if it jumped there), and the goal kept only if the
fingertip (``<finger>_ds_tip``) is then in contact with the pad ``CONTACT_DEPTH`` (the sim's
``min_contact_depth``) to ``TOUCH_DEPTH`` deep and nothing else presses in; else it is ignored
and another chosen (one that touches the pad but is rejected is first nudged a little).
``least_covered`` orders the combinations / pads by how often the hand has touched them.

Every pose here is sim joint angles in the order of the ``names`` passed in.
"""

from __future__ import annotations

import itertools
import json
import os
import re
from typing import Iterable

import numpy as np

FINGERS = ("th", "if", "mf", "rf")
PALM = "palm"
PARTS = (PALM, *FINGERS)
WORKSPACE, PALM_TOUCH, THUMB_TOUCH = "workspace", "palm_touch", "thumb_touch"
TIP_GEOMS = {finger: f"{finger}_ds_tip" for finger in FINGERS}  # fingertip pads
# Skin pads: the Xela patches (``uspa44`` / ``uspa46``) and the fingertip pads.
SKIN_GEOM = re.compile(r"uspa4[46]|^(th|if|mf|rf)_ds_tip$")
PALM_PADS = re.compile(r"^uspa46_\d+$")
# A finger's sensor pads the thumb touches, fingertip to base: <finger>_<pad>.
PAD_ORDER = ("ds_tip", "md_uspa44", "px_uspa44", "bs_uspa44")
THUMB_TARGETS = tuple(f"{f}_{pad}" for f in FINGERS[1:] for pad in PAD_ORDER)
CONTACT_DEPTH = 0.0005  # m: a goal's fingertip-pad contact at least this deep (as the sim's)
TOUCH_DEPTH = 0.003  # m: deepest a fingertip may go into the pad it touches
PRESS_DEPTH = 0.001  # m: other parts of the hand deeper into one another press (not allowed)
# m: default deepest contact of two fingers not meant to touch (the sim's min_contact_depth:
# deeper, it reports them colliding); ``SelfTouchSolver.min_depth``
MIN_DEPTH = 0.0005
TOUCH_SAMPLES = 60000  # goals a touch checks (a MuJoCo reset each, nudges too) before giving up
THUMB_PALM_SAMPLES = 3000  # the same for the thumb onto the palm among other fingers
NUDGES = 30  # nudged goals checked around one touching the pad but rejected
NUDGE_RAD = 0.05  # rad: standard deviation of a nudge of each joint
SINGLE_CACHE = 6  # single-finger palm touches kept per finger to put combinations together
REJECT_RADIUS = 0.15  # rad (L2 of the sim angles): goals this close to a rejected one are too


def part_of(name: str) -> str:
    """Part of the hand (``PARTS``) of a body or pad: its finger prefix, else the palm."""
    prefix = name.split("_")[0]
    return prefix if prefix in FINGERS else PALM


def joint_ranges(ik, names: list[str]) -> np.ndarray:
    """(len(names), 2) [low, high] sim angles of joints ``names``."""
    model = ik.model
    return np.array([model.jnt_range[model.joint(n).id] for n in names], dtype=float)


def contact_depths(model, data) -> dict[tuple[str, str], float]:
    """Sorted (part, part) pairs of different parts of the hand in contact at the pose ``data``
    holds (``mj_forward`` done) -> their deepest penetration (m)."""
    depths: dict[tuple[str, str], float] = {}
    for c in data.contact[: data.ncon]:
        b1, b2 = model.geom_bodyid[c.geom1], model.geom_bodyid[c.geom2]
        if b1 == 0 or b2 == 0 or c.dist >= 0:  # the floor, or not in
            continue
        p1, p2 = part_of(model.body(b1).name), part_of(model.body(b2).name)
        if p1 != p2:
            pair = tuple(sorted((p1, p2)))
            depths[pair] = max(depths.get(pair, 0.0), -float(c.dist))
    return depths


def pressing_pairs(model, data, depth: float = PRESS_DEPTH) -> set[tuple[str, str]]:
    """The pairs of ``contact_depths`` deeper than ``depth`` (m)."""
    return {pair for pair, d in contact_depths(model, data).items() if d > depth}


class ExploredSet:
    """Goals and trajectory points (sim angles) played on the hand so far."""

    def __init__(self, n_joints: int) -> None:
        self.goals = np.empty((0, n_joints))
        self.points = np.empty((0, n_joints))

    def novelty(self, q: np.ndarray) -> float:
        """Smallest L2 distance (rad) of ``q`` to a goal or trajectory point (inf: none)."""
        everything = np.concatenate([self.goals, self.points])
        if not len(everything):
            return float("inf")
        return float(np.min(np.linalg.norm(everything - np.asarray(q), axis=1)))

    def add_episode(self, goal: np.ndarray | None, path: np.ndarray) -> None:
        """Adds the goal (None: not reached) and the trajectory points played."""
        if goal is not None:
            self.goals = np.concatenate([self.goals, np.asarray(goal, dtype=float)[None]])
        if len(path):
            self.points = np.concatenate([self.points, np.asarray(path, dtype=float)])

    @classmethod
    def from_episodes(cls, paths: Iterable[str], names: list[str]) -> ExploredSet:
        """The goals (if ``goal_reached``) and played trajectories of the saved episodes
        ``paths`` (``goal_sim`` / ``path_sim`` named ``sim_joint_names``), reordered to
        ``names``; unreadable ones are left out."""
        explored = cls(len(names))
        for path in paths:
            try:
                with np.load(path, allow_pickle=False) as data:
                    saved = [str(n) for n in data["sim_joint_names"]]
                    cols = [saved.index(n) for n in names]
                    goal, traj = data["goal_sim"][cols], data["path_sim"][:, cols]
                    if not bool(data["goal_reached"]):
                        goal = None
            except Exception:  # noqa: BLE001 - a broken file is not explored
                continue
            explored.add_episode(goal, traj)
        return explored


def sample_workspace_goal(
    ik, names: list[str], rng: np.random.Generator, explored: ExploredSet,
    threshold: float, tries: int = 2000, fingers: Iterable[str] | None = None,
) -> tuple[np.ndarray, float, int]:
    """(goal, its novelty, samples drawn): a pose uniform in the joint ranges of ``fingers``
    (all of them if None; the others open, at 0) where no two parts of the hand press into one
    another, more than ``threshold`` (rad) from everything ``explored``. Raises if none of
    ``tries`` samples is."""
    import mujoco

    ranges = joint_ranges(ik, names)
    if fingers is not None:
        moving = set(fingers)
        ranges[[i for i, n in enumerate(names) if n.split("_")[0] not in moving]] = 0.0
    best = 0.0
    for n in range(1, tries + 1):
        goal = rng.uniform(ranges[:, 0], ranges[:, 1])
        novelty = explored.novelty(goal)
        if novelty <= threshold:
            best = max(best, novelty)
            continue
        ik.data.qpos[:] = ik.to_qpos(names, goal)
        mujoco.mj_forward(ik.model, ik.data)
        if not pressing_pairs(ik.model, ik.data):
            return goal, novelty, n
    raise RuntimeError(
        f"no new pose in {tries} samples (the most novel was {best:.2f} rad from an explored "
        f"one, the threshold is {threshold:.2f} rad): lower the threshold"
    )


def skin_targets(model) -> dict[str, str]:
    """Skin pad geom name -> part of the hand it belongs to, by its name (the ``bs`` pads at
    the base of a finger are the finger's, though the model mounts them on the palm)."""
    return {
        model.geom(g).name: part_of(model.geom(g).name)
        for g in range(model.ngeom) if SKIN_GEOM.search(model.geom(g).name)
    }


def palm_combinations() -> list[tuple[str, ...]]:
    """Every non-empty combination of fingers, by size."""
    return [c for n in range(1, len(FINGERS) + 1) for c in itertools.combinations(FINGERS, n)]


def item_key(item: tuple[str, ...] | str) -> str:
    """Name of a touch item: 'th+rf' for a combination of fingers, the pad name for a pad."""
    return "+".join(item) if isinstance(item, tuple) else item


def palm_combination(key: str) -> tuple[str, ...] | None:
    """The combination of fingers of a ``item_key`` ('th+rf'), None if it names a pad."""
    fingers = tuple(key.split("+"))
    return fingers if all(f in FINGERS for f in fingers) else None


def mode_items(mode: str) -> list[str]:
    """The combinations of a mode (``item_key``): which fingers move (workspace) or touch the
    palm (every combination of fingers), or the pad the thumb touches."""
    if mode in (WORKSPACE, PALM_TOUCH):
        return [item_key(c) for c in palm_combinations()]
    if mode == THUMB_TOUCH:
        return list(THUMB_TARGETS)
    return []


def least_covered(keys: list[str], counts: dict[str, int], skip: set[str]) -> list[str]:
    """``keys`` not in ``skip``, the least touched (``counts``) first, ties in the order of
    ``keys`` (one finger before two, ...; fingertip before base)."""
    return sorted((k for k in keys if k not in skip), key=lambda k: counts.get(k, 0))


class SelfTouchSolver:
    """Poses where fingertips touch skin pads, chosen at random and checked by resetting
    MuJoCo (``HandIK``'s model) to them."""

    def __init__(self, ik) -> None:
        import mujoco

        self._mj = mujoco
        self.ik = ik
        self.model = ik.model
        self.targets = skin_targets(self.model)
        self.palm_pads = sorted(p for p in self.targets if PALM_PADS.match(p))
        self.thumb_targets = [p for p in THUMB_TARGETS if p in self.targets]
        # Part of every dof (the joints are hinges: qpos and dofs line up).
        self._dof_part = [
            part_of(self.model.body(self.model.jnt_bodyid[self.model.dof_jntid[d]]).name)
            for d in range(self.model.nv)
        ]
        self._reset_data = mujoco.MjData(self.model)  # ``reset_contacts``' own
        self._geom_names = [self.model.geom(g).name for g in range(self.model.ngeom)]
        # Single-finger palm touches found, by finger: [(qpos, details), ...].
        self._singles: dict[str, list[tuple[np.ndarray, dict]]] = {}
        self._min_depth = MIN_DEPTH

    @property
    def min_depth(self) -> float:
        """Deepest (m) two fingers not meant to touch may go into one another at a goal."""
        return self._min_depth

    @min_depth.setter
    def min_depth(self, depth: float) -> None:
        if depth != self._min_depth:
            self._singles.clear()  # checked against the old depth
        self._min_depth = depth

    def _limit(self, pair: tuple[str, str]) -> float:
        """Deepest contact allowed of a part pair not meant to touch: ``min_depth`` for two
        fingers, ``PRESS_DEPTH`` else."""
        return self._min_depth if pair[0] in FINGERS and pair[1] in FINGERS else PRESS_DEPTH

    def _geom_id(self, name: str) -> int:
        return self._mj.mj_name2id(self.model, self._mj.mjtObj.mjOBJ_GEOM, name)

    def _geoms_of(self, pad: str) -> set[int]:
        """Geoms of a pad: a fingertip pad is its ellipsoids ``<f>_ds_tip``, ``_2``..."""
        if pad.endswith("_ds_tip"):
            return {g for g, n in enumerate(self._geom_names)
                    if n == pad or n.startswith(f"{pad}_")}
        return {self._geom_id(pad)}

    def _mount(self, pad: str) -> str:
        """Part of the body a pad is mounted on (the ``bs`` pads: the palm)."""
        return part_of(self.model.body(self.model.geom_bodyid[self._geom_id(pad)]).name)

    def reset_contacts(self, qpos: np.ndarray) -> dict[tuple[int, int], float]:
        """MuJoCo reset to the pose ``qpos`` (``mj_resetData``, qpos and the actuators' targets
        set to it, ``mj_forward``): (geom, geom) of every contact -> its depth (m)."""
        mj, model, data = self._mj, self.model, self._reset_data
        mj.mj_resetData(model, data)
        data.qpos[:] = qpos
        for a in range(model.nu):
            if model.actuator_trntype[a] == mj.mjtTrn.mjTRN_JOINT:
                data.ctrl[a] = data.qpos[model.jnt_qposadr[model.actuator_trnid[a, 0]]]
        mj.mj_forward(model, data)
        contacts: dict[tuple[int, int], float] = {}
        for c in data.contact[: data.ncon]:
            pair = (min(c.geom1, c.geom2), max(c.geom1, c.geom2))
            contacts[pair] = max(contacts.get(pair, 0.0), -float(c.dist))
        return contacts

    def _depth(self, contacts: dict[tuple[int, int], float], a: set[int], b: set[int]) -> float:
        """Deepest of ``contacts`` between geoms ``a`` and ``b`` (0: none)."""
        return max((d for (g1, g2), d in contacts.items()
                    if (g1 in a and g2 in b) or (g2 in a and g1 in b)), default=0.0)

    def touch_depths(
        self, names: list[str], goal: np.ndarray, touch: dict[str, str]
    ) -> dict[str, float]:
        """Finger -> deepest contact (m; 0: none) of its fingertip with its pad of ``touch``
        after a MuJoCo reset to ``goal`` (``reset_contacts``)."""
        contacts = self.reset_contacts(self.ik.to_qpos(names, goal))
        return {
            f: self._depth(contacts, self._geoms_of(TIP_GEOMS[f]), self._geoms_of(pad))
            for f, pad in touch.items()
        }

    def _sample(
        self, finger: str, pads: list[str], rng: np.random.Generator,
        base: np.ndarray | None = None, allow: set[tuple[str, str]] = frozenset(),
        samples: int = TOUCH_SAMPLES,
    ) -> tuple[np.ndarray, dict]:
        """(qpos, {pad, part, contact_depth, spot}): ``finger``'s fingertip on one of
        ``pads``. Goals are ``base`` (default open) with the joints of ``finger`` (and of a
        finger the pads are on) at random; MuJoCo is reset to each (``reset_contacts``) and
        one is kept if the fingertip is then in contact with a pad ``CONTACT_DEPTH`` to
        ``TOUCH_DEPTH`` deep, ``finger`` no deeper than that into the pad's part elsewhere,
        the part pairs ``allow`` too, and any other no deeper than ``_limit`` (two fingers:
        ``min_depth``). A goal touching a pad but rejected is nudged
        ``NUDGES`` times (``NUDGE_RAD``) first. Raises after ``samples`` goals checked
        (nudges included)."""
        model, data = self.model, self._reset_data
        base = np.zeros(model.nq) if base is None else np.asarray(base, dtype=float)
        moving = {finger} | {part_of(p) for p in pads if part_of(p) in FINGERS}
        free = [d for d, part in enumerate(self._dof_part) if part in moving]
        low, high = model.jnt_range[free, 0], model.jnt_range[free, 1]
        tips = self._geoms_of(TIP_GEOMS[finger])
        pad_geoms = {pad: self._geoms_of(pad) for pad in pads}
        touched = {
            pad: {tuple(sorted((finger, part_of(pad)))), tuple(sorted((finger, self._mount(pad))))}
            | set(allow)
            for pad in pads
        }

        def check(q: np.ndarray) -> tuple[str | None, float, bool]:
            """(pad touched or None, depth, whether the goal is kept), MuJoCo reset to ``q``."""
            contacts = self.reset_contacts(q)
            pad, depth = max(
                ((p, self._depth(contacts, tips, g)) for p, g in pad_geoms.items()),
                key=lambda item: item[1],
            )
            if depth < CONTACT_DEPTH:
                return None, 0.0, False
            ok = depth <= TOUCH_DEPTH and all(
                d <= (TOUCH_DEPTH if pair in touched[pad] else self._limit(pair))
                for pair, d in contact_depths(model, data).items()
            )
            return pad, depth, ok

        near = 0  # goals touching a pad, but too deep or pressing elsewhere
        checks = 0  # MuJoCo resets, nudges included
        while checks < samples:
            q = base.copy()
            q[free] = rng.uniform(low, high)
            pad, depth, ok = check(q)
            checks += 1
            if pad is not None and not ok:  # close: look around it
                near += 1
                start = q[free].copy()
                for _ in range(min(NUDGES, samples - checks)):
                    q[free] = np.clip(start + rng.normal(0.0, NUDGE_RAD, len(free)), low, high)
                    pad, depth, ok = check(q)
                    checks += 1
                    if ok:
                        break
            if not ok:
                continue
            # Where on the pad: its deepest contact with the fingertip, in the pad's frame
            # (``check`` left MuJoCo reset to ``q``).
            geoms = pad_geoms[pad]
            c = max(
                (c for c in data.contact[: data.ncon]
                 if (c.geom1 in tips and c.geom2 in geoms)
                 or (c.geom2 in tips and c.geom1 in geoms)),
                key=lambda c: -c.dist,
            )
            g = c.geom2 if c.geom2 in geoms else c.geom1
            spot = data.geom_xmat[g].reshape(3, 3).T @ (c.pos - data.geom_xpos[g])
            return q, {"pad": pad, "part": self.targets[pad], "contact_depth": depth,
                       "spot": spot.tolist()}
        raise RuntimeError(
            f"no goal with the {finger} fingertip on {' / '.join(pads)} in {samples} (MuJoCo "
            f"reset to each); {near} touched it but too deep or pressing elsewhere"
        )

    def sample_touch(
        self, names: list[str], finger: str, pads: list[str], rng: np.random.Generator,
        **kwargs,
    ) -> tuple[np.ndarray, dict[str, dict]]:
        """(goal, {finger: touch details}) of ``_sample``."""
        q, details = self._sample(finger, pads, rng, **kwargs)
        return self.ik.from_qpos(names, q), {finger: details}

    def thumb_touch(
        self, names: list[str], pad: str, rng: np.random.Generator
    ) -> tuple[np.ndarray, dict[str, dict]]:
        """The thumb's fingertip on ``pad`` (one of ``thumb_targets``), the thumb's and that
        finger's joints chosen."""
        return self.sample_touch(names, "th", [pad], rng)

    def _palm_single(
        self, finger: str, rng: np.random.Generator, fresh: bool
    ) -> tuple[np.ndarray, dict] | None:
        """(qpos with only ``finger``'s joints moved, details): its fingertip on a palm pad, a
        new one if ``fresh`` (or half the time), else one found before (the last
        ``SINGLE_CACHE`` are kept). None if none is found."""
        known = self._singles.get(finger, [])
        if known and not fresh and rng.random() < 0.5:
            return known[rng.integers(len(known))]
        try:
            single = self._sample(finger, self.palm_pads, rng)
        except RuntimeError:
            return known[rng.integers(len(known))] if known else None
        self._singles[finger] = [*known, single][-SINGLE_CACHE:]
        return single

    def palm_touch(
        self, names: list[str], combo: tuple[str, ...], rng: np.random.Generator,
        attempts: int = 24,
    ) -> tuple[np.ndarray, dict[str, dict]]:
        """Every finger of ``combo`` with its fingertip on a palm pad: single-finger touches
        (``_palm_single``, new ones every other attempt) put together, the thumb then found
        among the other fingers already there; kept if, with MuJoCo reset to it, every
        fingertip is still in contact and nothing presses in (two fingers no deeper than
        ``min_depth``). Raises after ``attempts``."""
        model = self.model
        palm = {tuple(sorted((f, PALM))) for f in combo}
        others = [f for f in combo if f != "th"]
        reason = "no attempt"
        for attempt in range(attempts):
            q, details = np.zeros(model.nq), {}
            for f in others or combo:
                single = self._palm_single(f, rng, fresh=attempt % 2 == 1)
                if single is None:
                    raise RuntimeError(f"no palm touch of {f} found")
                cols = [d for d, part in enumerate(self._dof_part) if part == f]
                q[cols] = single[0][cols]
                details[f] = single[1]
            if "th" in combo and others:
                # The thumb only joins fingers that hold together without it.
                reason = self._palm_problems(q, others, details, palm)
                if reason:
                    continue
                try:
                    q, details["th"] = self._sample(
                        "th", self.palm_pads, rng, base=q, allow=palm,
                        samples=THUMB_PALM_SAMPLES,
                    )
                except RuntimeError as e:
                    reason = str(e)
                    continue
            reason = self._palm_problems(q, combo, details, palm)
            if not reason:
                return self.ik.from_qpos(names, q), details
        raise RuntimeError(f"no pose in {attempts} attempts; last: {reason}")

    def _palm_problems(
        self, q: np.ndarray, fingers: Iterable[str], details: dict[str, dict],
        palm: set[tuple[str, str]],
    ) -> str:
        """Why ``fingers`` do not touch the palm together at ``q`` (MuJoCo reset to it): a
        fingertip off its pad, or parts pressing in (finger-palm deeper than ``TOUCH_DEPTH``,
        others than ``_limit``); ""
        if they do."""
        contacts = self.reset_contacts(q)
        missing = [
            f for f in fingers if self._depth(
                contacts, self._geoms_of(TIP_GEOMS[f]), self._geoms_of(details[f]["pad"])
            ) < CONTACT_DEPTH
        ]
        depths = contact_depths(self.model, self._reset_data)
        pressing = sorted(
            pair for pair, depth in depths.items() if depth > (
                TOUCH_DEPTH if pair in palm else self._limit(pair)
            )
        )
        return ", ".join(
            [f"{f} lost its contact" for f in missing]
            + [f"{a}-{b} {depths[(a, b)] * 1000:.1f} mm" for a, b in pressing]
        )


def touch_pairs(mode: str, item: str) -> set[tuple[str, str]]:
    """Pairs of fingers meant to touch in a combination: the thumb and the finger whose pad it
    touches (Thumb -> fingers), none else."""
    if mode == THUMB_TOUCH:
        return {tuple(sorted(("th", part_of(item))))}
    return set()


def finger_collision(
    model, data, names: list[str], path: np.ndarray, allowed: set[tuple[str, str]],
) -> tuple[float, tuple[str, str] | None, int]:
    """(deepest contact (m), its finger pair, its index) of two fingers not ``allowed`` to
    touch along ``path`` (sim angles of joints ``names``), MuJoCo set to each point with its
    own ``data``; (0, None, -1) if none touch."""
    import mujoco

    adr = [int(model.jnt_qposadr[model.joint(n).id]) for n in names]
    worst: tuple[float, tuple[str, str] | None, int] = (0.0, None, -1)
    for i, q in enumerate(path):
        data.qpos[:] = 0.0
        data.qpos[adr] = q
        mujoco.mj_forward(model, data)
        for pair, depth in contact_depths(model, data).items():
            if (pair[0] in FINGERS and pair[1] in FINGERS and pair not in allowed
                    and depth > worst[0]):
                worst = (depth, pair, i)
    return worst


def waypoints(names: list[str], goal: np.ndarray, combo: tuple[str, ...] | None) -> list:
    """Poses an episode goes through on its way to ``goal`` (and back, reversed): with the
    thumb and other fingers on the palm, the others first (the thumb still open), so the thumb
    comes in among fingers already there, as ``palm_touch`` placed it."""
    if not combo or "th" not in combo or len(combo) == 1:
        return []
    mid = np.array(goal, dtype=float)
    mid[[i for i, n in enumerate(names) if n.startswith("th_")]] = 0.0
    return [mid]


def join_paths(paths: list[np.ndarray]) -> np.ndarray:
    """Paths one after another, each starting where the previous ends (its first point
    dropped)."""
    return np.concatenate([paths[0], *(p[1:] for p in paths[1:])])


def episode_path(out: np.ndarray, back: np.ndarray, dt: float, hold_s: float) -> np.ndarray:
    """The open -> goal path ``out``, the goal held ``hold_s``, then the goal -> open ``back``."""
    hold = np.repeat(out[-1:], max(int(round(hold_s / dt)), 0), axis=0)
    return np.concatenate([out, hold, back[1:]])


def touch_counts(paths: Iterable[str], field: str = "item") -> dict[str, int]:
    """Touch item (``item_key``) -> how many saved episodes ``paths`` reached its touch (or,
    with ``field="goal_id"``, stored goal -> how many reached it)."""
    counts: dict[str, int] = {}
    for path in paths:
        try:
            with np.load(path, allow_pickle=False) as data:
                meta = json.loads(str(data["meta"]))
        except Exception:  # noqa: BLE001 - a broken file touched nothing
            continue
        if meta.get("goal_reached") and meta.get(field):
            counts[meta[field]] = counts.get(meta[field], 0) + 1
    return counts


class GoalBank:
    """Goals found ahead for each combination of each mode (``mode_items``), saved as JSON:
    ``goals[mode][item]`` lists entries {id, goal (sim angles in ``names`` order), touches,
    novelty, created}; ``rejected[mode][item]`` the goals rejected (the black list: never
    used again, nor goals within ``REJECT_RADIUS`` of them); ``failed[mode][item]`` why the
    last search for it found none."""

    def __init__(self, names: list[str]) -> None:
        self.names = list(names)
        self.goals: dict[str, dict[str, list[dict]]] = {}
        self.rejected: dict[str, dict[str, list[dict]]] = {}
        self.failed: dict[str, dict[str, str]] = {}

    def of(self, mode: str, item: str) -> list[dict]:
        return self.goals.get(mode, {}).get(item, [])

    def add(self, mode: str, item: str, entry: dict) -> None:
        self.goals.setdefault(mode, {}).setdefault(item, []).append(entry)
        self.failed.get(mode, {}).pop(item, None)

    def remove(self, mode: str, ids: set[str]) -> None:
        for item, entries in self.goals.get(mode, {}).items():
            entries[:] = [e for e in entries if e["id"] not in ids]

    def reject(self, mode: str, item: str, goal_id: str) -> dict | None:
        """Moves the goal ``goal_id`` to the black list; the entry, or None if not stored."""
        entry = next((e for e in self.of(mode, item) if e["id"] == goal_id), None)
        if entry is not None:
            self.remove(mode, {goal_id})
            self.rejected.setdefault(mode, {}).setdefault(item, []).append(entry)
        return entry

    def near_rejected(self, mode: str, item: str, goal: np.ndarray,
                      radius: float = REJECT_RADIUS) -> bool:
        """Whether ``goal`` is within ``radius`` (L2 of the sim angles) of a rejected goal of
        the combination."""
        return any(np.linalg.norm(np.asarray(e["goal"]) - goal) <= radius
                   for e in self.rejected.get(mode, {}).get(item, []))

    def fail(self, mode: str, item: str, reason: str) -> None:
        self.failed.setdefault(mode, {})[item] = reason

    @classmethod
    def load(cls, path: str, names: list[str]) -> GoalBank:
        """The bank saved at ``path``, its goals reordered to ``names`` (empty if there is
        none or it cannot be read)."""
        bank = cls(names)
        try:
            with open(path) as f:
                data = json.load(f)
            cols = [list(data["sim_joint_names"]).index(n) for n in names]
        except (OSError, ValueError, KeyError):
            return bank
        for key, store in (("goals", bank.goals), ("rejected", bank.rejected)):
            for mode, items in data.get(key, {}).items():
                for item, entries in items.items():
                    store.setdefault(mode, {})[item] = [
                        dict(e, goal=np.asarray(e["goal"])[cols]) for e in entries
                    ]
        bank.failed = data.get("failed", {})
        return bank

    def save(self, path: str) -> None:
        def plain(store):
            return {
                mode: {item: [dict(e, goal=[float(v) for v in e["goal"]]) for e in entries]
                       for item, entries in items.items() if entries}
                for mode, items in store.items()
            }

        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = f"{path}.tmp"
        with open(tmp, "w") as f:
            json.dump({"sim_joint_names": self.names, "goals": plain(self.goals),
                       "rejected": plain(self.rejected), "failed": self.failed}, f, indent=1)
        os.replace(tmp, path)


def episode_mode(path: str) -> str:
    """The mode (``WORKSPACE`` / ``PALM_TOUCH`` / ``THUMB_TOUCH``) from an episode's folder."""
    return os.path.basename(os.path.dirname(path))
