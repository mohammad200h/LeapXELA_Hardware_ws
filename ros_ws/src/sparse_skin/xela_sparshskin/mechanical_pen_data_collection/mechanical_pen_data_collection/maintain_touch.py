"""Maintain touch: hold a finger in contact over the ``maintain_touch`` regions of a take.

A ``maintain_touch`` event marks a region of a take where the finger has to stay in contact
with the pen. When Play enters a region (at its start, or its end when the take plays
backwards) the take's time is held and the fingertip is driven like ``click_press`` drives the
thumb (``TouchPress``):

    approach -> hold -> (region's exit) -> release

- approach: guarded move of the fingertip's contact point along the press axis ``d``
  (Cartesian, by damped least squares) until the live fingertip force reaches
  ``contact_force``, or rises a little while the measured fingertip stops advancing (blocked).
  The take's time is held until then. With ``relative`` (default) the forces are measured from
  the force at the region's entry ``F_entry``: the fingertip taxels read a few units without
  any contact once the finger is curled (the skin stretches), so contact is a rise of
  ``contact_force`` above ``F_entry`` and the hold is at ``F_entry + hold_force``;
- hold: the take plays on over the region while the force is held at ``hold_force``. The joint
  goals are pushed past where contact was made (``q_c``) along ``u = K^-1 J^T d`` (normalised;
  ``K`` the joints' relative kP), which makes the fingertip force point along ``d``:

      F_des  = F_contact + (hold_force - F_contact) * min(tau / ramp_s, 1)
      dq    += force_gain * (F_des - F) * u * dt
      q_cmd  = q_c + dq

  The motors are springs (force ~ goal error), so integrating the force error into the goal
  holds the force without a steady error. While a joint's effort is at ``sat_effort`` ``dq``
  does not grow. When the force stays below half ``contact_force`` for ``loss_s`` the contact
  is lost: the take's time is held again and the finger approaches again from where it is;
- release: after the region the joints blend back into the take over ``release_s``.

No contact within ``max_travel`` / ``max_wait`` gives up on the region: the finger blends back
into the take and Play goes on.

The press axis ``d`` is the way the contact point moved over ``APPROACH_S`` before the entry
(in playback order), if that is within ``MAX_AXIS_ANGLE`` of the fingertip pad's normal, else
the pad's normal (``touch_axis``). ``F`` is the fingertip force as force replay and the plots
measure it: the sum of the fingertip taxel magnitudes from a no-contact baseline. A region's
``params`` can override any of the settings (``hold_force``, ``contact_force``, ...).

Without live Xela readings or fingertip kinematics, ``TouchHold`` holds the recorded pose at
the entry and presses along the joint motion that led there instead (open loop):

    q_cmd  = q_rec(entry) + offset * direction
    offset = clip(press_offset + press_rate * (time in the region), 0, max_offset)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from mechanical_pen_data_collection.click_press import (
    IK_DAMPING,
    IK_MAX_STEP,
    U_UPDATE_S,
    Kinematics,
    PressStep,
    region_settings,
    unit,
)

# The press direction is the motion over this long before the region's entry point.
APPROACH_S = 0.3
APPROACH, HOLD, RELEASE = "approach", "hold", "release"
# Approach motion of the contact point shorter than this (m) gives no press axis.
MIN_AXIS_MOTION = 1e-3
# The approach motion is the press axis only within this angle (deg) of the pad's normal.
MAX_AXIS_ANGLE = 75.0
# Blocked contact: the force has been above this fraction of contact_force for BLOCKED_S ...
BLOCKED_LEVEL = 0.5
BLOCKED_S = 0.2
# ... while the measured fingertip advanced less than this fraction of the commanded advance.
BLOCKED_RATIO = 0.3
# The fingertip's advance is measured over at least this long (leap_state comes at ~10 Hz).
MIN_SPEED_SPAN_S = 0.2
# Contact is lost below this fraction of contact_force.
LOSS_RATIO = 0.5


@dataclass
class MaintainTouchSettings:
    """Settings tab "Maintain touch" section; a region's ``params`` can override them."""

    enabled: bool = True
    relative: bool = True  # forces from the force at the region's entry (not from the Zero)
    hold_force: float = 2.0  # fingertip force held in contact (force units, as the tip plots)
    contact_force: float = 0.5  # fingertip force that ends the approach
    ramp_s: float = 0.5  # s the force ramps from contact up to hold_force
    force_gain: float = 0.1  # rad/s along u per force unit missing
    approach_speed: float = 0.01  # m/s of the guarded move
    max_travel: float = 0.02  # m the approach may move
    max_wait: float = 4.0  # s for contact
    max_press_q: float = 0.5  # rad: largest press offset |dq| past the contact joints
    max_joint_offset: float = 0.4  # rad: largest press offset of any one joint
    sat_effort: float = 600.0  # leap_state effort of a joint at its current limit (0: off)
    loss_s: float = 0.3  # s below LOSS_RATIO x contact_force before approaching again
    release_s: float = 0.3  # s to blend back into the recording after a region
    # Without live force / kinematics (``TouchHold``):
    press_offset: float = 0.03  # rad pressed past the held pose
    press_rate: float = 0.05  # rad/s the press grows by during a region (0: fixed press)
    max_offset: float = 0.2  # rad


def touch_axis(
    kin: Kinematics, q_at: Callable[[float], np.ndarray], entry: float, reverse: bool,
    t_range: tuple[float, float],
) -> tuple[np.ndarray, str]:
    """Press axis ``d`` (3,) of a region entered at take time ``entry`` (played backwards if
    ``reverse``), from the recorded finger joints ``q_at(t)``, and where it came from."""
    before = float(np.clip(entry + APPROACH_S if reverse else entry - APPROACH_S, *t_range))
    q_entry = q_at(entry)
    x_entry, _ = kin.point_and_jacobian(q_entry)
    x_before, _ = kin.point_and_jacobian(q_at(before))
    normal = unit(kin.normal(q_entry))
    motion = x_entry - x_before
    moved = float(np.linalg.norm(motion))
    if moved >= MIN_AXIS_MOTION:
        angle = float(np.degrees(np.arccos(np.clip(np.dot(motion / moved, normal), -1, 1))))
        if angle <= MAX_AXIS_ANGLE:
            return motion / moved, f"approach motion ({moved * 1000:.1f} mm, {angle:.0f} deg " \
                                   "off the pad normal)"
        return normal, f"pad normal (approach motion {angle:.0f} deg off it)"
    return normal, f"pad normal (approach motion only {moved * 1000:.1f} mm)"


@dataclass
class TouchPressRegion:
    entry: float  # take time Play enters the region (its start, or its end in reverse)
    exit: float  # take time Play leaves it
    axis: np.ndarray  # (3,) unit press direction d in the hand's base frame
    kin: Kinematics
    params: dict = field(default_factory=dict)  # the event's own settings
    kp: np.ndarray | None = None  # (J,) relative kP of the finger's joints (None: equal)

    def contains(self, local: float) -> bool:
        return min(self.entry, self.exit) <= local <= max(self.entry, self.exit)


class TouchPress:
    """Per-playback state of the ``maintain_touch`` regions of a take with live force feedback;
    ``step`` is called every command step."""

    def __init__(
        self,
        regions: list[TouchPressRegion],
        settings: MaintainTouchSettings,
        log: Callable[[str], None] = lambda _: None,
    ) -> None:
        self.regions = regions
        self.settings = settings  # read every step, so Settings tab changes apply at once
        self.log = log
        self.trace: list[dict] = []  # every decision: time, state, event, F, F_des, |dq|, why
        self.state = ""
        self.status = ""
        self.force = 0.0
        self.f_des = 0.0
        self.saturated = ""  # joint (column index) at its current limit, "" if none
        self._region: TouchPressRegion | None = None
        self._failed: TouchPressRegion | None = None  # gave up on it: the take plays over it
        self._now = 0.0
        self._t = 0.0  # time in the current state
        self._q = np.empty(0)  # commanded finger joints
        self._last: np.ndarray | None = None  # last returned command
        self._x0 = np.zeros(3)  # contact point where the approach started
        self._x = np.zeros(3)  # commanded contact point (approach)
        self._points: deque[tuple[float, np.ndarray]] = deque()  # measured (time, point)
        self._loading_since: float | None = None
        self._q_c = np.empty(0)  # commanded joints at contact
        self._dq = np.empty(0)  # press offset past ``_q_c``
        self._u = np.empty(0)  # unit joint direction of the press
        self._u_age = 0.0
        self._f0 = 0.0  # force where the hold started (start of the ramp)
        self._entry_force = 0.0  # force where Play entered the region
        self._low_t = 0.0  # time below the loss level
        self._blend: np.ndarray | None = None  # joints the blend into the take starts from

    def reset(self, local: float | None = None) -> None:
        """Playback (re)starts somewhere else (seek)."""
        self._region = None
        self._failed = None
        self._blend = None
        self._last = None
        self.state = self.status = ""

    @property
    def offset(self) -> float:
        return float(np.linalg.norm(self._dq)) if self.state == HOLD else 0.0

    # ---- bookkeeping --------------------------------------------------------------------

    def _note(self, event: str, why: str = "") -> None:
        region = self._region
        self.trace.append({
            "t": round(self._now, 3),
            "region": [region.entry, region.exit] if region is not None else None,
            "state": self.state,
            "event": event,
            "F": round(self.force, 3),
            "F_des": round(self.f_des, 3),
            "dq": round(self.offset, 4),
            "why": why,
        })
        self.log(f"{event}: {why}" if why else event)

    def _solve(self) -> None:
        """One damped least-squares step of the commanded joints toward ``_x``."""
        x, jac = self._region.kin.point_and_jacobian(self._q)
        jjt = jac @ jac.T + IK_DAMPING ** 2 * np.eye(3)
        dq = jac.T @ np.linalg.solve(jjt, self._x - x)
        self._q = self._q + np.clip(dq, -IK_MAX_STEP, IK_MAX_STEP)

    def _update_u(self) -> None:
        """Joint direction whose goal offset makes a fingertip force along ``d``."""
        _, jac = self._region.kin.point_and_jacobian(self._q_c + self._dq)
        kp = self._region.kp if self._region.kp is not None else np.ones(jac.shape[1])
        self._u = unit((jac.T @ self._region.axis) / kp)
        self._u_age = 0.0

    # ---- states -------------------------------------------------------------------------

    def _start_approach(self, why: str) -> None:
        self.state = APPROACH
        self._t = 0.0
        self._x0, _ = self._region.kin.point_and_jacobian(self._q)
        self._x = self._x0.copy()
        self._points.clear()
        self._loading_since = None
        self._note("approach", why)

    def _start_hold(self, why: str) -> None:
        self.state = HOLD
        self._t = 0.0
        self._q_c = self._q.copy()
        self._dq = np.zeros_like(self._q)
        self._f0 = self.force
        self._low_t = 0.0
        self._update_u()
        travel = float(np.dot(self._x - self._x0, self._region.axis))
        self._note("contact", f"{why}; travel {travel * 1000:.1f} mm, "
                              f"press direction {np.round(self._u, 3).tolist()}")

    def _leave(self, event: str, why: str) -> None:
        """Ends the active region: blend from the current command into the take."""
        self._note(event, why)
        self._blend = self._q.copy()
        self._region = None
        self._t = 0.0
        self.state = RELEASE
        self.status = "maintain touch: release"

    def _give_up(self, why: str) -> None:
        self._failed = self._region
        self._leave("give up", f"{why}; the take plays over the region")

    def _base(self, s: MaintainTouchSettings) -> float:
        """Force the settings' forces are measured from."""
        return self._entry_force if s.relative else 0.0

    def _approach(self, s: MaintainTouchSettings, dt: float, point: np.ndarray | None) -> None:
        d = self._region.axis
        if point is not None:
            self._points.append((self._now, point))
            while self._now - self._points[0][0] > 2 * MIN_SPEED_SPAN_S:
                self._points.popleft()
        base = self._base(s)
        contact = base + s.contact_force
        if self.force >= contact:
            self._start_hold(f"F {self.force:.2f} >= {contact:.2f}")
            return
        if self.force >= base + BLOCKED_LEVEL * s.contact_force:
            if self._loading_since is None:
                self._loading_since = self._now
            elif self._now - self._loading_since >= BLOCKED_S and len(self._points) >= 2:
                (t0, p0), (t1, p1) = self._points[0], self._points[-1]
                moved = float(np.dot(p1 - p0, d))
                if (t1 - t0 >= MIN_SPEED_SPAN_S
                        and moved < BLOCKED_RATIO * s.approach_speed * (t1 - t0)):
                    self._start_hold(f"blocked at F {self.force:.2f}")
                    return
        else:
            self._loading_since = None
        travel = float(np.dot(self._x - self._x0, d))
        if travel >= s.max_travel:
            self._give_up(f"no contact within {s.max_travel * 1000:.0f} mm "
                          f"(F {self.force:.2f}, contact {contact:.2f})")
        elif self._t > s.max_wait:
            self._give_up(f"no contact within {s.max_wait:.1f} s")
        else:
            self._x = self._x + d * s.approach_speed * dt
            self._solve()
            self.f_des = contact
            self.status = f"maintain touch: approach, F {self.force:.2f} / {contact:.2f}"

    def _hold(self, s: MaintainTouchSettings, dt: float, effort: np.ndarray | None) -> None:
        base = self._base(s)
        if self.force < base + LOSS_RATIO * s.contact_force:
            self._low_t += dt
            if self._low_t >= s.loss_s:
                self._q = self._q_c + self._dq
                self._start_approach(f"contact lost (F {self.force:.2f} for {s.loss_s:.1f} s)")
                return
        else:
            self._low_t = 0.0

        self.saturated = ""
        if s.sat_effort > 0.0 and effort is not None:
            hot = np.flatnonzero(np.abs(effort) >= s.sat_effort)
            if len(hot):
                self.saturated = ",".join(str(int(j)) for j in hot)

        a = 1.0 if s.ramp_s <= 0.0 else min(self._t / s.ramp_s, 1.0)
        self.f_des = self._f0 + a * (base + s.hold_force - self._f0)
        rate = s.force_gain * (self.f_des - self.force)
        if self.saturated:
            rate = min(rate, 0.0)  # more goal adds no force at the limit, only turns it
        self._u_age += dt
        if self._u_age >= U_UPDATE_S:
            self._update_u()
        dq = self._dq + rate * dt * self._u
        dq = np.clip(dq, -s.max_joint_offset, s.max_joint_offset)
        norm = float(np.linalg.norm(dq))
        if norm > s.max_press_q:
            dq *= s.max_press_q / norm
        if float(np.dot(dq, self._u)) < 0.0:  # never pull back past the contact joints
            dq = dq - float(np.dot(dq, self._u)) * self._u
        self._dq = dq
        self._q = self._q_c + self._dq
        sat = f", limit on joint {self.saturated}" if self.saturated else ""
        self.status = f"maintain touch: F {self.force:.2f} / {self.f_des:.2f}{sat}"

    # ---- step ---------------------------------------------------------------------------

    def step(
        self,
        local: float,
        dt: float,
        now: float,
        q_rec: np.ndarray,
        q_hand: np.ndarray | None,
        force: float | None,
        effort: np.ndarray | None = None,
    ) -> PressStep | None:
        """Finger joints for take time ``local`` (the take's ``q_rec`` there), from the measured
        hand joints ``q_hand``, fingertip force ``force`` and finger joint ``effort``; None when
        no region is active (nor blending out of one), so the take commands the finger."""
        self._now = now
        if force is not None:
            self.force = force
        region = next(
            (r for r in self.regions if r.contains(local) and r is not self._failed), None
        ) if self.settings.enabled else None
        if self._region is not None and region is not self._region:
            why = "maintain touch turned off" if not self.settings.enabled else \
                f"take time {local:.2f} s"
            self._leave("release", why)
        if self._region is None and region is not None:
            start = self._last if self._blend is not None and self._last is not None else q_rec
            self._region = region
            self._blend = None
            self._q = np.asarray(start, dtype=float).copy()
            self._entry_force = self.force
            self._start_approach(f"region {region.entry:.2f}-{region.exit:.2f} s, "
                                 f"axis {np.round(region.axis, 3).tolist()}, "
                                 f"F at entry {self.force:.2f}")
        if self._region is None:
            return self._step_blend(dt, q_rec)

        s = region_settings(self.settings, self._region.params)
        self._t += dt
        if force is None:
            self._give_up("no live fingertip force")
            return self._step_blend(0.0, q_rec)
        if self.state == APPROACH:
            self._approach(s, dt, self._region.kin.point(q_hand))
        if self.state == HOLD:
            self._hold(s, dt, effort)
        if self._region is None:  # gave up
            return self._step_blend(0.0, q_rec)
        self._last = self._q.copy()
        return PressStep(q=self._q.copy(), hold=self.state == APPROACH)

    def _step_blend(self, dt: float, q_rec: np.ndarray) -> PressStep | None:
        """Blends from where the region ended into the take over ``release_s``."""
        if self._blend is None:
            return None
        release = self.settings.release_s
        self._t += dt
        a = 1.0 if release <= 0.0 else min(self._t / release, 1.0)
        if a >= 1.0:
            self._blend = None
            self._last = None
            self.state = self.status = ""
            return None
        self._last = (1.0 - a) * self._blend + a * np.asarray(q_rec)
        return PressStep(q=self._last.copy(), hold=False)


# ---- open loop fallback -----------------------------------------------------------------


@dataclass
class TouchRegion:
    entry: float  # take time Play enters the region (its start, or its end in reverse)
    exit: float  # take time Play leaves it
    pose: np.ndarray  # (J,) recorded joints at ``entry``
    direction: np.ndarray  # (J,) unit press direction (zeros: no press)
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
) -> list[TouchRegion]:
    """Regions for the (start, end, params) take-time ``spans`` of a take with joints ``q``
    (N, J) at ``t``, played backwards if ``reverse``. ``params`` may hold the region's own
    ``press_offset`` / ``max_offset`` / ``press_rate``."""
    regions = []
    for start, end, params in spans:
        entry, exit_ = (end, start) if reverse else (start, end)
        before = entry + APPROACH_S if reverse else entry - APPROACH_S
        pose = _sample(t, q, entry)
        motion = pose - _sample(t, q, float(np.clip(before, t[0], t[-1])))
        norm = float(np.linalg.norm(motion))
        direction = motion / norm if norm > 1e-6 else np.zeros_like(motion)
        regions.append(TouchRegion(
            entry, exit_, pose, direction,
            press_offset=params.get("press_offset"), max_offset=params.get("max_offset"),
            press_rate=params.get("press_rate"),
        ))
    return regions


class TouchHold:
    """Per-playback state of open loop maintain touch; ``step`` is called every command
    step."""

    def __init__(
        self,
        regions: list[TouchRegion],
        settings: MaintainTouchSettings,
        log: Callable[[str], None] = lambda _: None,
    ) -> None:
        self.regions = regions
        self.settings = settings
        self.log = log
        self.trace: list[dict] = []
        self._offset = 0.0
        self.status = ""
        self._active: TouchRegion | None = None
        self._held: np.ndarray | None = None  # last held command, blended out after a region
        self._release_left = 0.0

    @property
    def offset(self) -> float:
        return self._offset

    def reset(self, local: float | None = None) -> None:
        """Playback (re)starts somewhere else (seek)."""
        self._active = None
        self._held = None
        self._release_left = 0.0
        self._offset = 0.0
        self.status = ""

    def step(
        self, local: float, dt: float, now: float, q_rec: np.ndarray, *_, **__
    ) -> PressStep | None:
        """Command for take time ``local`` given the recorded joints ``q_rec`` there; None
        when the take commands the finger."""
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
                self._offset = press
                self.log(f"maintaining touch (open loop) from take time {region.entry:.2f} s "
                         f"to {region.exit:.2f} s")
            else:
                self._offset += rate * dt
            self._offset = float(np.clip(self._offset, 0.0, max_offset))
            capped = self._offset >= max_offset
            self.status = f"maintaining touch ({'max press' if capped else 'pressing'})"
            self._held = region.pose + self._offset * region.direction
            self._release_left = s.release_s
            return PressStep(q=self._held.copy(), hold=False)
        if self._active is not None:
            self.log(f"released touch at take time {local:.2f} s")
            self._active = None
        self.status = ""
        if self._held is None or self._release_left <= 0.0 or s.release_s <= 0.0:
            self._held = None
            return None
        a = self._release_left / s.release_s
        self._release_left -= dt
        return PressStep(q=a * self._held + (1.0 - a) * q_rec, hold=False)
