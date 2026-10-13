"""Force-aware playback of a take: track the recorded fingertip force while in contact.

Pure position replay presses only as hard as kP x tracking error allows, and the pen stops the
finger short of the recorded joints. During each contact phase of a take the commanded joints are
therefore pushed past the recording, along the direction the finger moved while it loaded up:

    offset <- clip(offset + gain * (F_rec(t) - F_live) * dt, 0, max_offset)
    q_cmd   = q_rec(t) + offset * direction

``F`` is the fingertip force: the sum of the fingertip taxel magnitudes from a no-contact
baseline (what the Create tab plots). Around that:

- wait for contact: while the take is in contact but the live fingertip is not, the take's time
  is held and the finger keeps pressing until it touches (or ``max_wait`` passes);
- wait for the click: a click shows as a sharp force drop while the finger is still pressed in.
  If the take clicked and the live finger has not by then, the take's time is held and the
  offset grows at ``push_rate`` until the live force drops (or ``max_wait`` passes), but not
  while the live force is already ``FORCE_LIMIT`` times the recorded peak. A live click is
  watched for all the time, so a pen clicking earlier than in the take is not pressed again;
- release: once clicked (or given up) the offset decays and the take continues as recorded.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Protocol

import numpy as np

# Contact: recorded force above noise + CONTACT_LEVEL * (peak - noise).
CONTACT_LEVEL = 0.25
# Loading starts where the force rises above noise + LOADING_LEVEL * (peak - noise).
LOADING_LEVEL = 0.1
# Takes whose force never rises this far above the noise have no contact phase.
MIN_CONTACT_FORCE = 0.5
MIN_PHASE_S = 0.1
# The live fingertip touches once its force reaches this fraction of the recorded contact level.
LIVE_CONTACT = 0.5
# A click: the force falls by CLICK_DROP of its maximum over the last CLICK_WINDOW_S...
CLICK_DROP = 0.2
CLICK_WINDOW_S = 0.25
# ...while the finger moves back by less than this fraction of its loading travel. Letting go of
# a springy contact drops the force about in proportion to the retraction, so a click must drop
# it at least twice as fast as that.
CLICK_MAX_RETRACT = 0.1
# A live click up to this long before a contact phase starts counts for it (the pen can click
# earlier than in the take).
CLICK_EARLY_S = 1.0
# While held for the click, stop pushing once the live force reaches this many times the
# recorded peak.
FORCE_LIMIT = 1.5
# Time constant of the offset decaying back to zero after a contact phase.
RELEASE_TAU_S = 0.3


class ForceSettings(Protocol):
    force_replay: bool
    force_gain: float  # rad per (force unit * s)
    force_max_offset: float  # rad
    force_push_rate: float  # rad/s
    force_max_wait: float  # s


@dataclass
class ContactPhase:
    start: float  # take time the recorded force rises above ``level``
    end: float  # take time it falls back below it
    level: float  # recorded force that counts as contact
    peak: float  # highest recorded force in the phase
    click: float | None  # take time of the recorded click (force just before its sharp drop)
    direction: np.ndarray  # (J,) unit joint direction of the finger while loading up
    done: bool = False


def sample(t: np.ndarray, values: np.ndarray, at: float) -> np.ndarray:
    return np.array([np.interp(at, t, values[:, j]) for j in range(values.shape[1])])


def find_click(
    t_force: np.ndarray, force: np.ndarray, peak: int, end: int,
    t: np.ndarray, q: np.ndarray, direction: np.ndarray, travel: float,
) -> float | None:
    """Take time of the first sharp force drop in ``force[peak:end + 1]`` during which the finger
    stays pressed in; None if the force only falls as the finger lets go."""
    for m in range(peak, end + 1):
        window = (t_force >= t_force[m] - CLICK_WINDOW_S) & (t_force <= t_force[m])
        top = int(np.flatnonzero(window)[np.argmax(force[window])])
        if force[m] > (1.0 - CLICK_DROP) * force[top]:
            continue
        retract = -float(np.dot(sample(t, q, t_force[m]) - sample(t, q, t_force[top]), direction))
        return float(t_force[top]) if retract < CLICK_MAX_RETRACT * travel else None
    return None


def contact_phases(
    t_force: np.ndarray, force: np.ndarray, t: np.ndarray, q: np.ndarray
) -> list[ContactPhase]:
    """Contact phases of a take from its fingertip force ``force`` (at ``t_force``) and its
    finger joints ``q`` (N, J) at ``t``."""
    if len(force) < 2 or len(t) < 2:
        return []
    noise = float(np.percentile(force, 20))
    top = float(force.max())
    if top - noise < MIN_CONTACT_FORCE:
        return []
    level = noise + CONTACT_LEVEL * (top - noise)
    loading = noise + LOADING_LEVEL * (top - noise)
    above = force > level
    phases = []
    i, n = 0, len(force)
    while i < n:
        if not above[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and above[j + 1]:
            j += 1
        if t_force[j] - t_force[i] >= MIN_PHASE_S:
            k = i + int(np.argmax(force[i: j + 1]))
            b = i
            while b > 0 and force[b] > loading:
                b -= 1
            motion = sample(t, q, t_force[k]) - sample(t, q, t_force[b])
            travel = float(np.linalg.norm(motion))
            if travel > 1e-6:
                direction = motion / travel
                phases.append(ContactPhase(
                    start=float(t_force[i]),
                    end=float(t_force[j]),
                    level=level,
                    peak=float(force[k]),
                    click=find_click(t_force, force, k, j, t, q, direction, travel),
                    direction=direction,
                ))
        i = j + 1
    return phases


class ForceTracker:
    """Per-playback state of the force-aware replay; ``step`` is called every command step."""

    def __init__(
        self,
        phases: list[ContactPhase],
        t_force: np.ndarray,
        force: np.ndarray,
        n_joints: int,
        settings: ForceSettings,
        log: Callable[[str], None] = lambda _: None,
    ) -> None:
        self.phases = phases
        self.t_force = t_force
        self.force = force
        self.settings = settings
        self.log = log
        self.offset = 0.0  # rad along ``direction``
        self.direction = np.zeros(n_joints)
        self.status = ""
        self._contact = False
        self._waited = 0.0
        self._window: deque[tuple[float, float]] = deque()  # (time, live force)
        self._last_click: float | None = None  # time of the last live click
        self._active_since: float | None = None  # time the current phase became active

    def reset(self, local: float) -> None:
        """Playback (re)starts at take time ``local``: phases already over count as done."""
        for phase in self.phases:
            phase.done = phase.end < local
        self._contact = False
        self._waited = 0.0
        self._window.clear()
        self._last_click = None
        self._active_since = None

    @property
    def offset_q(self) -> np.ndarray:
        return self.offset * self.direction

    def _active(self, local: float) -> ContactPhase | None:
        return next((p for p in self.phases if not p.done and p.start <= local), None)

    def _push(self, amount: float) -> None:
        self.offset = float(np.clip(self.offset + amount, 0.0, self.settings.force_max_offset))

    def _finish(self, phase: ContactPhase, message: str) -> None:
        phase.done = True
        self._contact = False
        self._waited = 0.0
        self._active_since = None
        self.log(message)

    def _watch_click(self, now: float, f_live: float) -> None:
        """Records a live click: a sharp drop from a force at least the next phase's contact."""
        self._window.append((now, f_live))
        while self._window[0][0] < now - CLICK_WINDOW_S:
            self._window.popleft()
        upcoming = next((p for p in self.phases if not p.done), None)
        top = max(f for _, f in self._window)
        if (
            upcoming is not None
            and top >= LIVE_CONTACT * upcoming.level
            and f_live <= (1.0 - CLICK_DROP) * top
        ):
            self._last_click = now
            self._window.clear()  # one drop, one click

    def step(self, local: float, dt: float, now: float, f_live: float | None) -> bool:
        """Updates ``offset`` for take time ``local``; returns False to hold the take's time."""
        s = self.settings
        if f_live is not None:
            self._watch_click(now, f_live)
        phase = self._active(local) if s.force_replay and f_live is not None else None
        if phase is None:
            self.offset *= float(np.exp(-dt / RELEASE_TAU_S))
            self.status = ""
            return True
        if self._active_since is None:
            self._active_since = now
        self.direction = phase.direction
        f_rec = float(np.interp(local, self.t_force, self.force))

        if (
            phase.click is not None
            and self._last_click is not None
            and self._last_click >= self._active_since - CLICK_EARLY_S
        ):
            self._finish(phase, f"click at take time {local:.2f} s "
                                f"(offset {self.offset:.3f} rad, force {f_live:.2f})")
            return True

        if not self._contact:
            if f_live >= LIVE_CONTACT * phase.level:
                self._contact = True
                self._waited = 0.0
                self.log(f"contact at take time {local:.2f} s (offset {self.offset:.3f} rad)")
            else:
                self._waited += dt
                if self._waited > s.force_max_wait:
                    self._finish(phase, f"no contact within {s.force_max_wait:.1f} s at take "
                                        f"time {local:.2f} s; continuing without force replay")
                    return True
                self._push(s.force_gain * max(f_rec - f_live, 0.0) * dt)
                self.status = "waiting for contact"
                return False

        if phase.click is not None and local >= phase.click:
            self._waited += dt
            if self._waited > s.force_max_wait:
                self._finish(phase, f"no click within {s.force_max_wait:.1f} s at take time "
                                    f"{local:.2f} s (offset {self.offset:.3f} rad, force "
                                    f"{f_live:.2f}); continuing")
                return True
            if f_live < FORCE_LIMIT * phase.peak:
                self._push(
                    (s.force_push_rate + s.force_gain * max(phase.peak - f_live, 0.0)) * dt
                )
            self.status = "pressing for the click"
            return False
        if local > phase.end:
            self._finish(phase, f"contact phase ended at take time {local:.2f} s")
            return True
        self._push(s.force_gain * (f_rec - f_live) * dt)
        self.status = "tracking force"
        return True
