"""Click press: a force-ramp press of the fingertip inside a ``click_press`` region.

Force replay (``force_replay``) presses past the recorded joints along a joint-space direction
until the fingertip force matches the take. A ``click_press`` region replaces the take instead:
when Play reaches the region's start the take's time is held and the finger is driven

    approach -> press -> retract -> (take continues from the region's end)

- approach: guarded move of the fingertip along the press axis ``d`` (Cartesian, by damped least
  squares) until the live fingertip force reaches the contact level, or rises a little while the
  measured fingertip stops advancing (blocked);
- press: the force is ramped until the pen clicks. The joint goals are pushed past where contact
  was made (``q_c``) along ``u = K^-1 J^T d`` (normalised; ``K`` the joints' relative kP):

      F_des   = min(F_contact + force_ramp * F_peak * tau, max_force_ratio * F_peak)
      dq     += press_gain_q * (F_des - F) / F_peak * u * dt
      q_cmd   = q_c + dq

  The motors are springs (torque ~ kP x goal error), so this makes the fingertip force point
  along ``d``. Pushing the goal along an IK direction instead makes a force along
  ``(J J^T)^-1 d``, 20-37 degrees off ``d`` on the thumb, which slides it off the cap. ``u`` is
  recomputed every ``U_UPDATE_S`` at the commanded joints.

  While a finger joint's ``leap_state`` effort is at ``sat_effort`` (its current limit), ``dq``
  does not grow: more goal there adds no force, only turns it sideways. Saturated for
  ``sat_hold_s`` without a click aborts the press.

  A slip (the contact spot moving ``slip_shift`` on the pad, or the measured fingertip moving
  more than ``button_travel`` along ``d`` / ``slip_across`` across it while the force does not
  grow) cuts ``dq`` to ``slip_backoff`` and tilts ``d`` by ``slip_tilt`` against the slip;
  ``max_slips`` aborts;
- retract: back off ``retract`` along ``-d`` over ``release_s``. The take then jumps to the
  region's end and the joints blend back into it over ``release_s``.

``F`` is the fingertip force as force replay and the plots measure it: the sum of the fingertip
taxel magnitudes from a no-contact baseline. Gains and the ramp are in units of the recorded
peak, so they do not depend on the take. The press axis ``d`` and the contact point (a
force-weighted centroid of the fingertip taxels) come from the take (``press_geometry``): ``d`` is
the way the contact point moved while the force loaded up to the region's peak.

A click is a new rising edge of the click detector; without it (unless
``require_click_detector``), a ``CLICK_DROP`` fall of ``F`` within ``CLICK_WINDOW_S`` from at
least ``click_min_ratio`` x the peak together with the measured fingertip giving way along ``d``
(advancing ``click_advance`` within the window along the way the joint springs unload,
``J K^-1 J^T d``), with no slip in that window. A slip drops the
force too, so a drop alone is not a click.

Every decision is appended to ``trace`` (saved with the Play recording).
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field, replace
from typing import Callable, Protocol

import numpy as np

from mechanical_pen_data_collection.force_replay import CLICK_DROP, CLICK_WINDOW_S, LOADING_LEVEL

APPROACH, PRESS, RETRACT, RELEASE, DONE = "approach", "press", "retract", "release", "done"
# Damping of the least-squares step (m); far below a fingertip Jacobian's singular values.
IK_DAMPING = 1e-3
# Largest joint change of one least-squares step (rad), so a bad Jacobian cannot jerk the finger.
IK_MAX_STEP = 0.05
# The fingertip's advance is measured over at least this long (leap_state comes at ~10 Hz).
MIN_SPEED_SPAN_S = 0.2
# Loading motion shorter than this (m) cannot give a press axis.
MIN_LOADING_MOTION = 1e-3
# No-contact force of a take: this percentile of its fingertip force (as ``contact_phases``).
NOISE_PERCENTILE = 20
# The press direction in joint space is recomputed this often (s).
U_UPDATE_S = 0.2
# Blocked contact: the force has been above noise + LOADING_LEVEL x (peak - noise) this long ...
BLOCKED_S = 0.2
# ... while the measured fingertip advanced less than this fraction of the commanded advance.
BLOCKED_RATIO = 0.3
# A give-way moves the fingertip off its give-way direction by at most this fraction of its
# advance along it.
GIVE_WAY_ACROSS = 0.5
# Fingertip motion across d (m) below this gives no direction to re-aim against.
MIN_SLIP_ACROSS = 3e-4
# The force "does not grow" while below this fraction of the highest since the slip reference.
SLIP_FORCE_RATIO = 1.02


@dataclass
class ClickPressSettings:
    """Settings tab "Click press" values; a region's ``params`` can override any of them."""

    enabled: bool = True
    approach_speed: float = 0.01  # m/s of the guarded move
    contact_ratio: float = 0.15  # contact: noise + this x (recorded peak - noise)
    force_ramp: float = 0.5  # recorded peaks per s the desired force ramps up at
    max_force_ratio: float = 1.3  # cap of the desired force: this x the recorded peak
    press_gain_q: float = 0.15  # rad/s along u per recorded peak of missing force
    max_press_q: float = 0.5  # rad: largest press offset |dq| past the contact joints
    max_joint_offset: float = 0.4  # rad: largest press offset of any one joint
    max_travel: float = 0.02  # m the approach may move from where the region starts
    max_wait: float = 4.0  # s for contact, and again for the click
    sat_effort: float = 600.0  # leap_state effort of a joint at its current limit (0: off)
    sat_hold_s: float = 1.0  # s saturated without a click before giving up
    slip_shift: float = 0.0025  # m the contact spot may move on the pad
    button_travel: float = 0.004  # m the fingertip may move along d past contact
    slip_across: float = 0.003  # m the fingertip may move across d past contact
    slip_backoff: float = 0.6  # fraction of the press offset kept after a slip
    slip_tilt: float = 10.0  # degrees d is turned against a slip
    max_slips: int = 3  # slips before giving up
    retract: float = 0.004  # m backed off along the press axis after the press
    release_s: float = 0.3  # s of the retract, and of the blend back into the take
    click_min_ratio: float = 0.7  # a force drop counts only from this x the recorded peak
    click_advance: float = 0.001  # m along d within the click window: the button giving way
    require_click_detector: bool = False  # only the click detector ends a press as a click
    max_current: float = 0.0  # finger joint |effort| that aborts the press at once (0: off)


def region_settings(settings: ClickPressSettings, params: dict | None) -> ClickPressSettings:
    """``settings`` with the values a region's ``params`` set."""
    defaults = asdict(settings)
    own = {k: type(defaults[k])(v) for k, v in (params or {}).items() if k in defaults}
    return replace(settings, **own) if own else settings


def unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v


@dataclass
class PressGeometry:
    axis: np.ndarray  # (3,) unit press direction d in the hand's base frame
    peak: float  # recorded peak fingertip force in the region
    noise: float  # recorded no-contact fingertip force
    weights: np.ndarray  # (n,) fingertip taxel weights of the contact point (sum 1)
    loading: float  # m the contact point moved along ``axis`` while loading in the take

    def contact(self, ratio: float) -> float:
        return self.noise + ratio * (self.peak - self.noise)


class Kinematics(Protocol):
    def point_and_jacobian(self, q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Contact point (3,) and its (3, J) Jacobian at finger joints ``q``."""

    def point(self, q_hand: np.ndarray | None) -> np.ndarray | None:
        """Contact point at measured hand joints ``q_hand`` (None if unknown)."""


def press_geometry(
    start: float,
    end: float,
    t_force: np.ndarray,
    magnitudes: np.ndarray,
    positions_at: Callable[[float], np.ndarray],
) -> PressGeometry | None:
    """Press geometry of the region ``start``-``end`` of a take.

    ``magnitudes`` (L, n) are the fingertip taxels' force magnitudes at ``t_force``;
    ``positions_at(t)`` gives their (n, 3) positions at take time ``t``. None when the region
    has no force peak or the contact point did not move while loading.
    """
    force = magnitudes.sum(axis=1)
    inside = np.flatnonzero((t_force >= start) & (t_force <= end))
    if len(inside) == 0:
        return None
    k = int(inside[np.argmax(force[inside])])
    noise = float(np.percentile(force, NOISE_PERCENTILE))
    peak = float(force[k])
    if peak <= noise or magnitudes[k].sum() <= 0.0:
        return None
    weights = magnitudes[k] / magnitudes[k].sum()
    # Loading starts where the force rises above the noise (as ``contact_phases``), at the
    # earliest at the region's start.
    b = k
    while b > inside[0] and force[b] > noise + LOADING_LEVEL * (peak - noise):
        b -= 1
    motion = weights @ positions_at(float(t_force[k])) - weights @ positions_at(float(t_force[b]))
    loading = float(np.linalg.norm(motion))
    if loading < MIN_LOADING_MOTION:
        return None
    return PressGeometry(
        axis=motion / loading, peak=peak, noise=noise, weights=weights, loading=loading
    )


@dataclass
class PressRegion:
    start: float
    end: float
    geometry: PressGeometry
    kin: Kinematics
    params: dict = field(default_factory=dict)  # the event's own settings
    kp: np.ndarray | None = None  # (J,) relative kP of the finger's joints (None: equal)
    done: bool = False


@dataclass
class PressStep:
    q: np.ndarray  # (J,) finger joints to command
    hold: bool  # hold the take's time
    skip_to: float | None = None  # jump the take's time here (the region's end)


class ClickPress:
    """Per-playback state of the ``click_press`` regions of a take; ``step`` is called every
    command step."""

    def __init__(
        self,
        regions: list[PressRegion],
        settings: ClickPressSettings,
        log: Callable[[str], None] = lambda _: None,
    ) -> None:
        self.regions = sorted(regions, key=lambda r: r.start)
        self.settings = settings  # read every step, so Settings tab changes apply at once
        self.log = log
        self.trace: list[dict] = []  # every decision: time, state, event, F, |dq|, slips, why
        self.state = ""
        self.status = ""
        self.force = 0.0
        self.f_des = 0.0
        self.slips = 0
        self.saturated = ""  # joint (column index) at its current limit, "" if none
        self._region: PressRegion | None = None
        self._d = np.zeros(3)  # current press axis (re-aimed after slips)
        self._q = np.empty(0)  # commanded finger joints
        self._x0 = np.zeros(3)  # contact point where the region started
        self._x = np.zeros(3)  # commanded contact point (approach / retract)
        self._t = 0.0  # time in the current state
        self._now = 0.0
        self._clicks = 0  # click detector count when the region started
        # Press
        self._q_c = np.empty(0)  # commanded joints at contact
        self._dq = np.empty(0)  # press offset past ``_q_c``
        self._u = np.empty(0)  # unit joint direction of the press
        self._e = np.zeros(3)  # unit direction the fingertip gives way in when the force drops
        self._u_age = 0.0
        self._sat_t = 0.0  # time saturated without a click
        self._ref_point: np.ndarray | None = None  # measured fingertip at the slip reference
        self._ref_spot: np.ndarray | None = None  # contact spot on the pad at the reference
        self._ref_force = 0.0  # highest force since the slip reference
        self._last_slip = -np.inf
        # Measured fingertip (time, point) and (time, F) histories.
        self._points: deque[tuple[float, np.ndarray]] = deque()
        self._forces: deque[tuple[float, float]] = deque()
        self._loading_since: float | None = None  # approach: force above the loading level
        self._retract_from = np.zeros(3)
        self._blend: np.ndarray | None = None  # joints the blend into the take starts from

    def reset(self, local: float) -> None:
        """Playback (re)starts at take time ``local``: regions it starts past are skipped."""
        for region in self.regions:
            region.done = region.start < local
        self._region = None
        self._blend = None
        self.state = self.status = ""

    @property
    def press_offset(self) -> float:
        return float(np.linalg.norm(self._dq)) if self.state == PRESS else 0.0

    # ---- bookkeeping --------------------------------------------------------------------

    def _note(self, event: str, why: str = "") -> None:
        region = self._region
        self.trace.append({
            "t": round(self._now, 3),
            "region": [region.start, region.end] if region is not None else None,
            "state": self.state,
            "event": event,
            "F": round(self.force, 3),
            "F_des": round(self.f_des, 3),
            "dq": round(self.press_offset, 4),
            "slips": self.slips,
            "why": why,
        })
        self.log(f"{event}: {why}" if why else event)

    def _enter(self, region: PressRegion, q_rec: np.ndarray, click_count: int) -> None:
        self._region = region
        self._d = region.geometry.axis.copy()
        self._q = np.asarray(q_rec, dtype=float).copy()
        self._x0, _ = region.kin.point_and_jacobian(self._q)
        self._x = self._x0.copy()
        self._t = 0.0
        self._clicks = click_count
        self.slips = 0
        self.saturated = ""
        self._forces.clear()
        self._points.clear()
        self._loading_since = None
        self.state = APPROACH
        self._note("approach", f"region {region.start:.2f}-{region.end:.2f} s")

    def _travel(self, x: np.ndarray) -> float:
        return float(np.dot(x - self._x0, self._region.geometry.axis))

    def _abort(self, why: str) -> None:
        self._note("abort", why)
        self._to_retract()

    def _to_retract(self) -> None:
        if self.state == PRESS:
            self._q = self._q_c + self._dq
            self._x, _ = self._region.kin.point_and_jacobian(self._q)
        self.state = RETRACT
        self._t = 0.0
        self._retract_from = self._x.copy()

    def _solve(self) -> None:
        """One damped least-squares step of the commanded joints toward ``_x``."""
        x, jac = self._region.kin.point_and_jacobian(self._q)
        jjt = jac @ jac.T + IK_DAMPING ** 2 * np.eye(3)
        dq = jac.T @ np.linalg.solve(jjt, self._x - x)
        self._q = self._q + np.clip(dq, -IK_MAX_STEP, IK_MAX_STEP)

    def _advance(self) -> tuple[float, float] | None:
        """(along, across) the give-way direction ``e``: how far the measured fingertip moved
        over the last ``CLICK_WINDOW_S`` (None if that span is shorter than
        ``MIN_SPEED_SPAN_S``)."""
        if len(self._points) < 2:
            return None
        (t0, p0), (t1, p1) = self._points[0], self._points[-1]
        if t1 - t0 < MIN_SPEED_SPAN_S:
            return None
        along = float(np.dot(p1 - p0, self._e))
        return along, float(np.linalg.norm(p1 - p0 - along * self._e))

    def _update_u(self) -> None:
        """Joint direction whose goal offset makes a fingertip force along ``d``, and the way
        the fingertip gives way when that force drops (``J K^-1 J^T d``: the joint springs
        unloading, not ``d`` itself)."""
        _, jac = self._region.kin.point_and_jacobian(self._q_c + self._dq)
        kp = self._region.kp if self._region.kp is not None else np.ones(jac.shape[1])
        self._u = unit((jac.T @ self._d) / kp)
        self._e = unit(jac @ ((jac.T @ self._d) / kp))
        self._u_age = 0.0

    # ---- states -------------------------------------------------------------------------

    def _start_press(self, why: str, point: np.ndarray | None, spot: np.ndarray | None) -> None:
        self.state = PRESS
        self._t = 0.0
        self._q_c = self._q.copy()
        self._dq = np.zeros_like(self._q)
        self._sat_t = 0.0
        self._points.clear()  # the give-way is measured from the press on, not the approach
        self._update_u()
        self._set_slip_reference(point, spot)
        self._note("contact", f"{why}; travel {self._travel(self._x) * 1000:.1f} mm, "
                              f"press direction {np.round(self._u, 3).tolist()}")

    def _set_slip_reference(self, point: np.ndarray | None, spot: np.ndarray | None) -> None:
        self._ref_point = None if point is None else point.copy()
        self._ref_spot = None if spot is None else spot.copy()
        self._ref_force = self.force

    def _approach(self, s: ClickPressSettings, dt: float, point: np.ndarray | None,
                  spot: np.ndarray | None) -> None:
        g = self._region.geometry
        contact = g.contact(s.contact_ratio)
        loading = g.contact(LOADING_LEVEL)
        if self.force >= contact:
            self._start_press(f"F {self.force:.2f} >= {contact:.2f}", point, spot)
            return
        if self.force >= loading:
            if self._loading_since is None:
                self._loading_since = self._now
            elif self._now - self._loading_since >= BLOCKED_S and len(self._points) >= 2:
                (t0, p0), (t1, p1) = self._points[0], self._points[-1]
                moved = float(np.dot(p1 - p0, self._d))
                if moved < BLOCKED_RATIO * s.approach_speed * (t1 - t0):
                    self._start_press(f"blocked at F {self.force:.2f}", point, spot)
                    return
        else:
            self._loading_since = None
        if self._travel(self._x) >= s.max_travel:
            self._abort(f"no contact within {s.max_travel * 1000:.0f} mm "
                        f"(F {self.force:.2f}, contact {contact:.2f})")
        elif self._t > s.max_wait:
            self._abort(f"no contact within {s.max_wait:.1f} s")
        else:
            self._x = self._x + self._d * s.approach_speed * dt
            self.f_des = contact
            self.status = f"click press: approach, F {self.force:.2f} / {contact:.2f}"

    def _slipped(self, s: ClickPressSettings, point: np.ndarray | None,
                 spot: np.ndarray | None) -> tuple[str, np.ndarray | None] | None:
        """(why, tangential slip direction) when the fingertip slips, else None."""
        self._ref_force = max(self._ref_force, self.force)
        tangent, across, along = None, 0.0, 0.0
        if point is not None and self._ref_point is not None:
            motion = point - self._ref_point
            along = float(np.dot(motion, self._d))
            tangent = motion - along * self._d
            across = float(np.linalg.norm(tangent))
        # Which way the fingertip slid (to re-aim against), if it moved measurably across d.
        slid = unit(tangent) if tangent is not None and across > MIN_SLIP_ACROSS else None
        if spot is not None and self._ref_spot is not None:
            shift = float(np.linalg.norm(spot - self._ref_spot))
            if shift > s.slip_shift:
                return f"contact spot moved {shift * 1000:.1f} mm on the pad", slid
        if tangent is not None:
            if across > s.slip_across:
                return f"fingertip moved {across * 1000:.1f} mm across d", unit(tangent)
            # A button gives way a few mm; moving further along d while the force falls back
            # is the fingertip sliding over the cap (or pushing the pen away).
            if along > s.button_travel and self.force * SLIP_FORCE_RATIO < self._ref_force:
                return (f"fingertip moved {along * 1000:.1f} mm along d while the force fell "
                        f"to {self.force:.2f} from {self._ref_force:.2f}", slid)
        return None

    def _press(self, s: ClickPressSettings, dt: float, point: np.ndarray | None,
               spot: np.ndarray | None, click_count: int, effort: np.ndarray | None) -> None:
        g = self._region.geometry
        contact = g.contact(s.contact_ratio)
        self._forces.append((self._now, self.force))
        while self._forces[0][0] < self._now - CLICK_WINDOW_S:
            self._forces.popleft()

        # Click
        if click_count > self._clicks:
            self._note("click", "click detector")
            self._to_retract()
            return
        if not s.require_click_detector and self._now - self._last_slip > CLICK_WINDOW_S:
            top = max(f for _, f in self._forces)
            advance = self._advance()
            # The button gives way along e; sliding off the cap also drops the force and moves
            # the fingertip forward, but off e as well.
            if (top >= s.click_min_ratio * g.peak and self.force <= (1.0 - CLICK_DROP) * top
                    and advance is not None and advance[0] > s.click_advance
                    and advance[1] <= GIVE_WAY_ACROSS * advance[0]):
                self._note("click", f"force drop {top:.2f} -> {self.force:.2f} and fingertip "
                                    f"gave way {advance[0] * 1000:.1f} mm")
                self._to_retract()
                return

        # Slip
        slip = self._slipped(s, point, spot)
        if slip is not None:
            why, tangent = slip
            self.slips += 1
            self._last_slip = self._now
            if self.slips > s.max_slips:
                self._abort(f"thumb keeps sliding ({why})")
                return
            self._dq = s.slip_backoff * self._dq
            if tangent is not None and s.slip_tilt > 0.0:
                a = np.radians(s.slip_tilt)
                self._d = unit(np.cos(a) * self._d - np.sin(a) * tangent)
            self._update_u()
            self._set_slip_reference(point, spot)
            self._note("slip", f"{why}; backed off to {self.press_offset:.3f} rad, "
                               f"d {np.round(self._d, 3).tolist()}")

        # Saturation
        self.saturated = ""
        if s.sat_effort > 0.0 and effort is not None:
            hot = np.flatnonzero(np.abs(effort) >= s.sat_effort)
            if len(hot):
                self.saturated = ",".join(str(int(j)) for j in hot)
        if self.saturated:
            if self._sat_t == 0.0:
                self._note("saturated", f"joint(s) {self.saturated} at the current limit")
            self._sat_t += dt
            if self._sat_t > s.sat_hold_s:
                self._abort(f"current limit reached at F {self.force:.2f} / F_des "
                            f"{self.f_des:.2f}: raise the Playback current limit")
                return
        else:
            self._sat_t = 0.0

        if self._t > s.max_wait:
            self._abort(f"no click within {s.max_wait:.1f} s (F {self.force:.2f})")
            return

        # Force
        self.f_des = min(contact + s.force_ramp * g.peak * self._t, s.max_force_ratio * g.peak)
        rate = s.press_gain_q * (self.f_des - self.force) / g.peak
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
        slips = f", slip {self.slips}/{s.max_slips}" if self.slips else ""
        self.status = (f"click press: F {self.force:.2f} / {self.f_des:.2f}, "
                       f"{self.press_offset:.2f} rad{sat}{slips}")

    # ---- step ---------------------------------------------------------------------------

    def step(
        self,
        local: float,
        dt: float,
        now: float,
        q_rec: np.ndarray,
        q_hand: np.ndarray | None,
        force: float | None,
        click_count: int,
        effort: np.ndarray | None = None,
        spot: np.ndarray | None = None,
    ) -> PressStep | None:
        """Finger joints for take time ``local`` (the take's ``q_rec`` there), from the measured
        hand joints ``q_hand``, fingertip force ``force``, finger joint ``effort`` and contact
        spot on the pad ``spot`` (m, fingertip frame); None when no region is active, so the
        take (and force replay) command the finger."""
        self._now = now
        if self._blend is not None:
            return self._step_blend(dt, q_rec)
        if self._region is None:
            region = next(
                (r for r in self.regions if not r.done and r.start <= local <= r.end), None
            )
            if region is None:
                return None
            self._enter(region, q_rec, click_count)
        region = self._region
        s = region_settings(self.settings, region.params)
        self._t += dt
        point = region.kin.point(q_hand) if self.state in (APPROACH, PRESS) else None
        if point is not None:
            self._points.append((now, point))
            while self._points[0][0] < now - CLICK_WINDOW_S:
                self._points.popleft()
        if force is not None:
            self.force = force
        active = self.state in (APPROACH, PRESS)
        if active and not s.enabled:
            self._abort("click press turned off")
        elif active and force is None:
            self._abort("no live fingertip force")
        elif (active and s.max_current > 0.0 and effort is not None
              and float(np.max(np.abs(effort))) > s.max_current):
            self._abort(f"joint current {float(np.max(np.abs(effort))):.0f} above "
                        f"{s.max_current:.0f}")

        if self.state == APPROACH:
            self._approach(s, dt, point, spot)
        if self.state == PRESS:
            self._press(s, dt, point, spot, click_count, effort)
            if self.state == PRESS:
                return PressStep(q=self._q.copy(), hold=True)

        if self.state == RETRACT:
            a = 1.0 if s.release_s <= 0.0 else min(self._t / s.release_s, 1.0)
            self._x = self._retract_from - a * s.retract * self._d
            self.status = "click press: retract"
            if a >= 1.0:
                self._solve()
                region.done = True
                self._note("done", f"take continues from {region.end:.2f} s")
                self._region = None
                self._blend = self._q.copy()
                self._t = 0.0
                self.state = RELEASE
                self.status = "click press: release"
                return PressStep(q=self._q.copy(), hold=False, skip_to=region.end)

        self._solve()
        return PressStep(q=self._q.copy(), hold=True)

    def _step_blend(self, dt: float, q_rec: np.ndarray) -> PressStep | None:
        """Blends from where the retract ended into the take over ``release_s``."""
        release = self.settings.release_s
        self._t += dt
        a = 1.0 if release <= 0.0 else min(self._t / release, 1.0)
        if a >= 1.0:
            self._blend = None
            self.state = DONE
            self.status = ""
            return None
        return PressStep(q=(1.0 - a) * self._blend + a * np.asarray(q_rec), hold=False)


class HandKinematics:
    """Fingertip taxel frames of the LEAP hand from hardware joints (``hand_ss.urdf`` FK of the
    ``convert_hardware_to_sim`` angles), in the URDF base frame."""

    def __init__(self, hw_joint_names: list[str]) -> None:
        from conversions.hardware_to_sim_conversion import map_hardware_to_sim
        from conversions.sim_to_hardware_conversion import (
            get_joint_names,
            get_joint_ranges,
            load_joint_config,
            remap_joint_commands,
        )

        from mechanical_pen_data_collection import taxel_fk_util as fk

        self._fk = fk
        self._map = map_hardware_to_sim
        self._remap = remap_joint_commands
        config = load_joint_config()
        self.sim_names, _ = get_joint_names(config)
        leap = config["leapXela"]
        self._hw_ranges = get_joint_ranges(self.sim_names, leap["hardware"])
        self._sim_ranges = get_joint_ranges(self.sim_names, leap["sim"])
        self.hw_joint_names = list(hw_joint_names)
        self._grids: dict[str, tuple[np.ndarray, object]] = {}  # link -> (taxel grid, frame index)

    def to_fk(self, q_hw: np.ndarray) -> np.ndarray:
        """(B, 16) hardware joints (``hw_joint_names`` order) -> FK order sim angles."""
        rows = []
        for q in np.atleast_2d(q_hw):
            ordered = self._remap(self.sim_names, self.hw_joint_names, [float(v) for v in q])
            sim = self._map(ordered, self._sim_ranges, self._hw_ranges)
            rows.append(self._fk.joint_angles_in_fk_order(self.sim_names, np.array(sim)))
        return np.stack(rows)

    def frames(self, q_fk: np.ndarray, link: str) -> tuple[np.ndarray, np.ndarray]:
        """(B, n, 3) positions and (B, n, 3, 3) rotations of the taxels of patch ``link`` (same
        order as ``get_fk_taxel_frames``) at FK order angles ``q_fk`` (B, 16). Only that link is
        computed: ~10x faster than all 368 taxels."""
        import torch

        fk = self._fk
        chain = fk.get_kinematic_chain()
        if link not in self._grids:
            xx, yy, d = fk.get_sensor_grid(link)
            grid = np.stack([xx.ravel(), yy.ravel(), np.full(xx.size, d), np.ones(xx.size)], 1)
            self._grids[link] = (grid, chain.get_frame_indices(link))
        grid, index = self._grids[link]
        q = torch.tensor(np.atleast_2d(q_fk), dtype=torch.float32)
        joints = {name: q[:, i] for i, name in enumerate(fk.LEAP_JOINT_ORDER)}
        pose = chain.forward_kinematics(joints, frame_indices=index)[link].get_matrix()
        pose = pose.numpy().astype(np.float64)  # (B, 4, 4)
        positions = np.einsum("bij,nj->bni", pose[:, :3], grid)
        rotations = np.repeat(pose[:, None, :3, :3], len(grid), axis=1)
        return positions, rotations

    def grid(self, link: str) -> np.ndarray:
        """(n, 3) taxel positions of patch link in its own frame (m), FK order."""
        xx, yy, d = self._fk.get_sensor_grid(link)
        return np.stack([xx.ravel(), yy.ravel(), np.full(xx.size, d)], 1).astype(np.float64)

    def frames_from_sim(
        self, sim_names: list[str], sim_q: np.ndarray, link: str
    ) -> tuple[np.ndarray, np.ndarray]:
        """Same as ``frames`` from recorded sim joints ``sim_q`` (B, 16) named ``sim_names``."""
        return self.frames(self._fk.joint_angles_in_fk_order(sim_names, sim_q), link)


class FingerKinematics:
    """``Kinematics`` of one finger's contact point (``weights`` over the taxels of its fingertip
    patch ``link``) for ``ClickPress``; the other joints of the hand stay at ``q_hand``."""

    EPS = 1e-3  # rad of the finite-difference Jacobian

    def __init__(
        self, hand: HandKinematics, q_hand: np.ndarray, cols: list[int], link: str,
        weights: np.ndarray,
    ) -> None:
        self.hand = hand
        self.q_hand = np.asarray(q_hand, dtype=float).copy()
        self.cols = list(cols)
        self.link = link
        self.weights = weights

    def point_and_jacobian(self, q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        batch = np.repeat(self.q_hand[None], len(self.cols) + 1, axis=0)
        batch[:, self.cols] = q
        for j, col in enumerate(self.cols):
            batch[j + 1, col] += self.EPS
        positions, _ = self.hand.frames(self.hand.to_fk(batch), self.link)
        points = positions.transpose(0, 2, 1) @ self.weights  # (B, 3)
        return points[0], ((points[1:] - points[0]) / self.EPS).T

    def point(self, q_hand: np.ndarray | None) -> np.ndarray | None:
        if q_hand is None:
            return None
        positions, _ = self.hand.frames(self.hand.to_fk(q_hand), self.link)
        return self.weights @ positions[0]

    def normal(self, q: np.ndarray) -> np.ndarray:
        """(3,) outward normal of the fingertip pad at finger joints ``q``: the patch frame's z
        axis, toward the side its taxels sit on (``maintain_touch`` press axis)."""
        batch = self.q_hand[None].copy()
        batch[0, self.cols] = q
        _, rotations = self.hand.frames(self.hand.to_fk(batch), self.link)
        side = float(np.sign(self.grid[:, 2].mean())) or 1.0
        return side * rotations[0, 0, :, 2]

    @property
    def grid(self) -> np.ndarray:
        """(n, 3) fingertip taxel positions in the fingertip patch's frame (m): where on the
        pad the contact is (``ClickPress`` slip detection)."""
        return self.hand.grid(self.link)
