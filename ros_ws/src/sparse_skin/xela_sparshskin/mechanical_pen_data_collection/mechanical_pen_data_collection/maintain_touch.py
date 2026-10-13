"""Maintain touch: hold a finger in contact over the ``maintain_touch`` regions of a take.

A ``maintain_touch`` event marks a region of a take where the finger has to stay in contact
with the pen. While Play is inside a region, the finger holds the recorded pose at the point
where Play entered it (its start, or its end when the take plays backwards) and presses along
the direction it was moving to get there:

    q_cmd = q_rec(entry) + offset * direction

``offset`` starts at ``press_offset`` and ramps up at ``press_rate`` so the force builds over
the region (``press_rate`` 0 keeps it fixed):

    offset = clip(press_offset + press_rate * (time in the region), 0, max_offset)

With ``match_force`` it instead grows / shrinks so the live fingertip force follows the recorded
force at the entry point:

    offset <- clip(offset + force_gain * (F_rec(entry) - F_live) * dt, 0, max_offset)

After the region the command blends back into the recording over ``release_s``. A region can
carry its own ``press_offset`` / ``max_offset`` / ``press_rate`` (set on its event in the Edit
tab), which replace the settings' values for it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

# The press direction is the motion over this long before the region's entry point.
APPROACH_S = 0.3


@dataclass
class MaintainTouchSettings:
    """Settings tab "Maintain touch" section."""

    enabled: bool = True
    press_offset: float = 0.03  # rad pressed past the held pose (without match_force)
    press_rate: float = 0.05  # rad/s the press grows by during a region (0: fixed press)
    match_force: bool = False
    force_gain: float = 0.1  # rad per (force unit * s)
    max_offset: float = 0.2  # rad
    release_s: float = 0.3  # s to blend back into the recording after a region


@dataclass
class TouchRegion:
    entry: float  # take time Play enters the region (its start, or its end in reverse)
    exit: float  # take time Play leaves it
    pose: np.ndarray  # (J,) recorded joints at ``entry``
    direction: np.ndarray  # (J,) unit press direction (zeros: no press)
    force: float | None  # recorded fingertip force at ``entry`` (None: no Xela readings)
    press_offset: float | None = None  # this region's own values (None: the settings')
    max_offset: float | None = None
    press_rate: float | None = None

    def contains(self, local: float) -> bool:
        return min(self.entry, self.exit) <= local <= max(self.entry, self.exit)


def _sample(t: np.ndarray, q: np.ndarray, at: float) -> np.ndarray:
    return np.array([np.interp(at, t, q[:, j]) for j in range(q.shape[1])])


def touch_regions(
    spans: tuple[tuple[float, float, dict], ...],
    t: np.ndarray,
    q: np.ndarray,
    reverse: bool,
    t_force: np.ndarray | None = None,
    force: np.ndarray | None = None,
) -> list[TouchRegion]:
    """Regions for the (start, end, params) take-time ``spans`` of a take with joints ``q``
    (N, J) at ``t`` and fingertip force ``force`` at ``t_force``, played backwards if
    ``reverse``. ``params`` may hold the region's own ``press_offset`` / ``max_offset``."""
    regions = []
    for start, end, params in spans:
        entry, exit_ = (end, start) if reverse else (start, end)
        before = entry + APPROACH_S if reverse else entry - APPROACH_S
        pose = _sample(t, q, entry)
        motion = pose - _sample(t, q, float(np.clip(before, t[0], t[-1])))
        norm = float(np.linalg.norm(motion))
        direction = motion / norm if norm > 1e-6 else np.zeros_like(motion)
        f = (
            float(np.interp(entry, t_force, force))
            if t_force is not None and force is not None and len(t_force)
            else None
        )
        regions.append(TouchRegion(
            entry, exit_, pose, direction, f,
            press_offset=params.get("press_offset"), max_offset=params.get("max_offset"),
            press_rate=params.get("press_rate"),
        ))
    return regions


class TouchHold:
    """Per-playback state of maintain touch; ``apply`` is called every command step."""

    def __init__(
        self,
        regions: list[TouchRegion],
        settings: MaintainTouchSettings,
        log: Callable[[str], None] = lambda _: None,
    ) -> None:
        self.regions = regions
        self.settings = settings
        self.log = log
        self.offset = 0.0
        self.status = ""
        self._active: TouchRegion | None = None
        self._held: np.ndarray | None = None  # last held command, blended out after a region
        self._release_left = 0.0

    def reset(self) -> None:
        """Playback (re)starts somewhere else (seek)."""
        self._active = None
        self._held = None
        self._release_left = 0.0
        self.offset = 0.0
        self.status = ""

    def apply(
        self, local: float, q_rec: np.ndarray, dt: float, live_force: Callable[[], float | None]
    ) -> tuple[np.ndarray, bool]:
        """Command for take time ``local`` given the recorded joints ``q_rec`` there; True while
        a region holds the finger."""
        s = self.settings
        region = (
            next((r for r in self.regions if r.contains(local)), None) if s.enabled else None
        )
        if region is not None:
            press = s.press_offset if region.press_offset is None else region.press_offset
            max_offset = s.max_offset if region.max_offset is None else region.max_offset
            rate = s.press_rate if region.press_rate is None else region.press_rate
            if region is not self._active:
                self._active = region
                self.offset = 0.0 if s.match_force and region.force is not None else press
                self.log(f"maintaining touch from take time {region.entry:.2f} s "
                         f"to {region.exit:.2f} s")
            f_live = live_force() if s.match_force and region.force is not None else None
            if f_live is not None:
                self.offset += s.force_gain * (region.force - f_live) * dt
                self.status = f"maintaining touch, force {f_live:.2f}/{region.force:.2f}"
            else:
                self.offset += rate * dt  # starts at ``press`` on entry
            self.offset = float(np.clip(self.offset, 0.0, max_offset))
            if f_live is None:
                capped = self.offset >= max_offset
                self.status = f"maintaining touch ({'max press' if capped else 'pressing'})"
            self._held = region.pose + self.offset * region.direction
            self._release_left = s.release_s
            return self._held.copy(), True
        if self._active is not None:
            self.log(f"released touch at take time {local:.2f} s")
            self._active = None
        self.status = ""
        if self._held is None or self._release_left <= 0.0 or s.release_s <= 0.0:
            self._held = None
            return q_rec, False
        a = self._release_left / s.release_s
        self._release_left -= dt
        return a * self._held + (1.0 - a) * q_rec, False
