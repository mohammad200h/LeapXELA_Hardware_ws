"""Search for a press direction of force replay that clicks the pen, listening to the click
detector (``push_button_pen_click_detection``, Int32 1 while a click is heard).

The click setting sliders are normalised, so what is searched is a *direction* in joint space
(a unit sphere), not the cube of slider values: a grid over the cube would spend most trials on
scaled copies of the same direction. Every trial moves the real finger, so the likeliest
directions go first: the start direction (the computed or saved one), then rings of directions
at growing angles around it (``candidate_directions``). The search stops at the first click.

One trial (``ClickProbe``) is a press probe:

    approach -> settle -> press -> hold -> retract -> (next direction)

- approach: ramp (``ramp_s``) from where the finger is to ``base`` (the take just before the
  contact);
- settle: wait until no click is heard;
- press: ``q = base + offset * direction`` with ``offset`` growing at ``force_push_rate`` up to
  ``force_max_offset`` (the click setting's values); stops growing once the live fingertip
  force reaches ``FORCE_LIMIT`` times the recorded peak;
- hold: stay pressed a moment, still listening;
- retract: ramp back to ``base``.

A click (a new rising edge of the click topic) during press or hold ends the search as found;
the finger still retracts before the probe is done.
"""

from __future__ import annotations

from typing import Callable, Protocol

import numpy as np

from mechanical_pen_data_collection.force_replay import FORCE_LIMIT

SETTLE_S = 0.3  # quiet time before a press starts
HOLD_S = 0.5  # time pressed at the deepest offset, still listening for the click
DUPLICATE_DEG = 1.0  # candidates closer than this to an earlier one are dropped

APPROACH, SETTLE, PRESS, HOLD, RETRACT, DONE = (
    "approach", "settle", "press", "hold", "retract", "done"
)


class ProbeSettings(Protocol):
    force_push_rate: float  # rad/s
    force_max_offset: float  # rad


def unit(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    norm = float(np.linalg.norm(v))
    if norm < 1e-9:
        raise ValueError("direction has zero length")
    return v / norm


def angle_deg(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.degrees(np.arccos(np.clip(np.dot(unit(a), unit(b)), -1.0, 1.0))))


def _sphere_points(dim: int, count: int, ring: int) -> np.ndarray:
    """``count`` unit vectors spread over the sphere of ``dim`` dimensions, turned per ``ring``
    so neighbouring rings do not line up."""
    if dim == 1:
        return np.array([[1.0], [-1.0]])
    if dim == 2:
        a = 2.0 * np.pi * (np.arange(count) + 0.5 * (ring % 2)) / count
        return np.stack([np.cos(a), np.sin(a)], axis=1)
    if dim == 3:  # Fibonacci sphere
        i = np.arange(count) + 0.5
        z = 1.0 - 2.0 * i / count
        r = np.sqrt(1.0 - z * z)
        a = np.pi * (3.0 - np.sqrt(5.0)) * i + ring
        return np.stack([r * np.cos(a), r * np.sin(a), z], axis=1)
    points = np.random.default_rng(ring).normal(size=(count, dim))
    return points / np.linalg.norm(points, axis=1, keepdims=True)


def candidate_directions(
    start: np.ndarray,
    ring_step_deg: float = 15.0,
    max_angle_deg: float = 90.0,
    base_count: int = 5,
) -> list[np.ndarray]:
    """Unit directions to try, in order: ``start``, then rings every ``ring_step_deg`` up to
    ``max_angle_deg`` around it; a ring has ``base_count`` directions, more the wider it is."""
    d = unit(start)
    n = len(d)
    out = [d]
    if n < 2:
        return out
    basis = np.linalg.svd(d[None])[2][1:]  # (n - 1, n) orthonormal, orthogonal to d
    step = np.radians(ring_step_deg)
    angles = np.arange(step, np.radians(max_angle_deg) + 1e-9, step)
    for ring, a in enumerate(angles):
        count = max(base_count, int(round(base_count * np.sin(a) / np.sin(step))))
        for u in _sphere_points(n - 1, count, ring):
            c = unit(np.cos(a) * d + np.sin(a) * (u @ basis))
            if all(angle_deg(c, o) >= DUPLICATE_DEG for o in out):
                out.append(c)
    return out


def slider_values(direction: np.ndarray) -> np.ndarray:
    """``direction`` scaled so its largest value is +-1 (the slider range)."""
    d = np.asarray(direction, dtype=float)
    return d / float(np.max(np.abs(d)))


class ClickProbe:
    """Tries ``directions`` one after the other from ``base`` until a click is heard; ``step``
    is called every command step and returns the finger joints to command. The attributes read
    by the GUI (``index``, ``state``, ``offset``, ``found``, ``message``) are plain values."""

    def __init__(
        self,
        base: np.ndarray,
        directions: list[np.ndarray],
        settings: ProbeSettings,
        ramp_s: float = 0.5,
        peak: float | None = None,
        log: Callable[[str], None] = lambda _: None,
    ) -> None:
        self.base = np.asarray(base, dtype=float)
        self.directions = [unit(d) for d in directions]
        self.settings = settings
        self.ramp_s = ramp_s  # s, ramp to and from the base pose
        self.peak = peak  # recorded peak fingertip force of the contact phase (None: no limit)
        self.log = log
        self.index = 0
        self.state = APPROACH
        self.offset = 0.0
        self.found: np.ndarray | None = None
        self.message = "moving to the contact"
        self._cancelled = False
        self._from: np.ndarray | None = None  # start of the current ramp
        self._q: np.ndarray | None = None  # last command
        self._t0: float | None = None  # time the current state started
        self._count0 = 0  # click count when the press started

    @property
    def total(self) -> int:
        return len(self.directions)

    @property
    def direction(self) -> np.ndarray:
        return self.directions[min(self.index, self.total - 1)]

    @property
    def angle(self) -> float:
        """Angle of the current direction from the first one (deg)."""
        return angle_deg(self.direction, self.directions[0])

    @property
    def done(self) -> bool:
        return self.state == DONE

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        """Stop after retracting to ``base`` (thread-safe enough: one flag)."""
        self._cancelled = True

    def _enter(self, state: str, now: float) -> None:
        self.state = state
        self._t0 = now
        if state in (APPROACH, RETRACT):
            self._from = self._q.copy()

    def _ramp(self, now: float) -> tuple[np.ndarray, bool]:
        ramp = max(self.ramp_s, 1e-3)
        a = min((now - self._t0) / ramp, 1.0)
        return (1.0 - a) * self._from + a * self.base, a >= 1.0

    def _retract(self, now: float, message: str) -> None:
        self.message = message
        self._enter(RETRACT, now)

    def step(
        self,
        now: float,
        dt: float,
        current: np.ndarray,
        click_on: bool,
        click_count: int,
        f_live: float | None = None,
    ) -> np.ndarray:
        """Finger joints to command at ``now``; ``current`` is what the finger was last commanded
        (used once, as the start of the first ramp)."""
        if self._q is None:
            self._q = np.asarray(current, dtype=float).copy()
            self._enter(APPROACH, now)
        s = self.settings
        if self._cancelled and self.state in (APPROACH, SETTLE, PRESS, HOLD):
            self._retract(now, "stopped")
            self.log("search stopped")

        if self.state == APPROACH:
            self._q, arrived = self._ramp(now)
            if arrived:
                self._enter(SETTLE, now)
        elif self.state == SETTLE:
            self._q = self.base.copy()
            if click_on:
                self._t0 = now
            elif now - self._t0 >= SETTLE_S:
                self.offset = 0.0
                self._count0 = click_count
                self.message = "pressing"
                self._enter(PRESS, now)
        elif self.state in (PRESS, HOLD):
            if click_count > self._count0:
                self.found = self.direction.copy()
                self.log(f"click on trial {self.index + 1}/{self.total} "
                         f"({self.angle:.0f} deg, offset {self.offset:.3f} rad)")
                self._retract(now, "click heard")
            elif self.state == PRESS:
                limit = self.peak is not None and f_live is not None and (
                    f_live >= FORCE_LIMIT * self.peak
                )
                self.offset = min(self.offset + s.force_push_rate * dt, s.force_max_offset)
                if limit or self.offset >= s.force_max_offset:
                    self.message = "force limit, holding" if limit else "holding"
                    self._enter(HOLD, now)
            elif now - self._t0 >= HOLD_S:
                self._retract(now, "no click, backing off")
            if self.state != RETRACT:
                self._q = self.base + self.offset * self.direction
        if self.state == RETRACT:
            self._q, arrived = self._ramp(now)
            if arrived:
                self.offset = 0.0
                if self.found is not None or self._cancelled:
                    self.state = DONE
                elif self.index + 1 >= self.total:
                    self.message = "no click in any direction"
                    self.log(f"no click in {self.total} directions")
                    self.state = DONE
                else:
                    self.index += 1
                    self.message = "settling"
                    self._enter(SETTLE, now)
        return self._q.copy()
