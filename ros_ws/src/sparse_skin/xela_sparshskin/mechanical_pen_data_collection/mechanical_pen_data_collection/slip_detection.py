"""Slip detection on a fingertip from its live Xela taxels.

``SlipDetector.update`` is fed every Xela reading of one fingertip: the magnitudes of its taxels
from the live no-contact baseline (``taxel_magnitudes``) and whether the finger is in contact
with the pen. Slip is only looked for in contact: curled fingertips read a few units with no
contact at all (the skin stretches), so the force alone does not tell contact.

In contact, two cues each report a slip:

- spot shift: the contact spot (force-weighted taxel position on the pad, ``grid``) moves more
  than ``slip_shift`` from where it settled (its mean over the first ``settle_s`` of contact, and
  where it was after each slip). The same test as ``click_press``'s slip;
- force drop: the fingertip force ``F`` (sum of the magnitudes) falls below
  ``1 - drop_ratio`` of its peak over the last ``drop_window_s``, by at least ``min_drop``: the
  pen sliding out of the grip.

After a slip, no other is reported for ``refractory_s``.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np

SPOT_SHIFT, FORCE_DROP = "spot shift", "force drop"


@dataclass
class SlipSettings:
    slip_shift: float = 0.0025  # m the contact spot may move on the pad
    settle_s: float = 0.15  # s of contact the spot's reference is averaged over
    drop_ratio: float = 0.3  # fraction of the recent peak force a drop must lose
    drop_window_s: float = 0.3  # s the recent peak is taken over
    min_drop: float = 0.3  # smallest force drop (units) that counts
    refractory_s: float = 0.3  # s after a slip before the next one is reported


@dataclass
class SlipEvent:
    t: float  # time of the reading it was detected on
    cue: str  # SPOT_SHIFT or FORCE_DROP
    value: float  # spot shift (m) or force drop (units)
    force: float  # fingertip force at the time


class SlipDetector:
    """Slips of one fingertip; ``grid`` is the (n, 3) taxel positions on its pad (m), in the
    order of the magnitudes (None: the spot shift cue is off)."""

    def __init__(self, grid: np.ndarray | None, settings: SlipSettings | None = None) -> None:
        self.grid = None if grid is None else np.asarray(grid, dtype=float)
        self.settings = settings or SlipSettings()
        self.events: list[SlipEvent] = []
        self.in_contact = False
        self.force = 0.0
        self._contact_since: float | None = None
        self._settle: list[np.ndarray] = []
        self._ref: np.ndarray | None = None
        self._forces: deque[tuple[float, float]] = deque()
        self._last_slip = -np.inf

    def update(self, t: float, mags: np.ndarray, in_contact: bool) -> SlipEvent | None:
        """Feeds the taxel magnitudes ``mags`` read at ``t``; the slip they show, if any."""
        s = self.settings
        mags = np.asarray(mags, dtype=float)
        self.force = float(mags.sum())
        self.in_contact = in_contact
        if not in_contact:
            self._contact_since, self._ref = None, None
            self._settle.clear()
            self._forces.clear()
            return None
        if self._contact_since is None:
            self._contact_since = t
        self._forces.append((t, self.force))
        while self._forces and self._forces[0][0] < t - s.drop_window_s:
            self._forces.popleft()

        spot = None
        if self.grid is not None and len(self.grid) == len(mags) and self.force > 1e-9:
            spot = (mags / self.force) @ self.grid
        if t - self._contact_since < s.settle_s:
            if spot is not None:
                self._settle.append(spot)
            return None
        if self._ref is None and spot is not None:
            self._ref = np.mean(self._settle, axis=0) if self._settle else spot

        event = None
        if spot is not None and self._ref is not None:
            shift = float(np.linalg.norm(spot - self._ref))
            if shift > s.slip_shift:
                event = SlipEvent(t, SPOT_SHIFT, shift, self.force)
                self._ref = spot  # the next slip is measured from here
        peak = max(f for _, f in self._forces)
        drop = peak - self.force
        if event is None and drop >= s.min_drop and self.force < (1.0 - s.drop_ratio) * peak:
            event = SlipEvent(t, FORCE_DROP, drop, self.force)
            self._forces.clear()
            self._forces.append((t, self.force))  # the next drop is from here
        if event is None or t - self._last_slip < s.refractory_s:
            return None
        self._last_slip = t
        self.events.append(event)
        return event
