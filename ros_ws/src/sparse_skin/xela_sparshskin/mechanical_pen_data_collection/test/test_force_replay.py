"""Force replay against a simulated finger: a P-servo pressing a pen that clicks."""

from dataclasses import dataclass

import numpy as np
import pytest

from mechanical_pen_data_collection import force_replay as fr

K_SERVO = 40.0  # force units per rad of position error (kP 600 on the real thumb)
K_PEN = 42.0  # force units per rad of pen travel
TRAVEL = 0.08  # rad the pen gives way when it clicks
DIRECTION = np.array([0.0, 0.0, -0.7, -0.7]) / np.hypot(0.7, 0.7)


@dataclass
class Settings:
    force_replay: bool = True
    force_gain: float = 0.1
    force_max_offset: float = 0.25
    force_push_rate: float = 0.15
    force_max_wait: float = 3.0


def demo_take():
    """A take pressing 0.15 rad along DIRECTION from t = 4 s, clicking at 6.0 s (force 6)."""
    t = np.arange(0.0, 10.0, 0.1)
    depth = np.interp(t, [0, 4, 6, 6.3, 7.5, 10], [0, 0, 0.15, 0.15, 0, 0])
    q = depth[:, None] * DIRECTION
    t_force = np.arange(0.0, 10.0, 1 / 90)
    force = 0.3 + np.interp(t_force, [0, 4, 6, 6.1, 7.0, 10], [0, 0, 6.0, 4.0, 0, 0])
    return t, q, t_force, force


def simulate(force_on=True, pen_shift=0.0, pen=True):
    t, q, t_force, force = demo_take()
    phases = fr.contact_phases(t_force, force, t, q)
    tracker = fr.ForceTracker(phases, t_force, force, 4, Settings(force_replay=force_on))
    tracker.reset(0.0)
    surface = 0.15 - 6.0 / K_PEN + pen_shift  # the demo reached force 6 at its deepest point
    dt, now, held, local = 1 / 30, 0.0, 0.0, 0.0
    clicked, top = None, 0.0
    while local < t[-1] and now < t[-1] + 15:
        now += dt
        local = min(now - held, t[-1])
        x_cmd = float(np.interp(local, t, q @ DIRECTION)) + tracker.offset
        f = K_PEN * K_SERVO / (K_PEN + K_SERVO) * max(0.0, x_cmd - surface) if pen else 0.0
        if pen and clicked is None and f >= 0.95 * 6.0:
            clicked = local
            surface += TRAVEL
            f = K_PEN * K_SERVO / (K_PEN + K_SERVO) * max(0.0, x_cmd - surface)
        top = max(top, f)
        if not tracker.step(local, dt, now, f + 0.3):
            held += dt
    return clicked, top, held, tracker


def test_contact_phase_of_demo():
    t, q, t_force, force = demo_take()
    (phase,) = fr.contact_phases(t_force, force, t, q)
    assert phase.click == pytest.approx(6.0, abs=0.05)
    assert phase.peak == pytest.approx(6.3, abs=0.05)
    np.testing.assert_allclose(phase.direction, DIRECTION, atol=1e-6)


def test_drop_while_letting_go_is_not_a_click():
    t, q, t_force, force = demo_take()
    # Force falls only as the finger retracts: no click.
    force = 0.3 + np.interp(t_force, [0, 4, 6, 6.3, 7.5, 10], [0, 0, 6.0, 6.0, 0, 0])
    (phase,) = fr.contact_phases(t_force, force, t, q)
    assert phase.click is None


def test_position_replay_does_not_click():
    clicked, top, held, _ = simulate(force_on=False)
    assert clicked is None and top < 4.0 and held == 0.0


@pytest.mark.parametrize("pen_shift", [0.0, 0.04, -0.04])
def test_force_replay_clicks(pen_shift):
    clicked, top, _, tracker = simulate(pen_shift=pen_shift)
    assert clicked is not None
    assert top < fr.FORCE_LIMIT * 6.3
    assert tracker.offset < 0.01  # released after the click


def test_no_pen_gives_up_and_continues():
    clicked, top, held, tracker = simulate(pen=False)
    assert clicked is None and top == 0.0
    assert held == pytest.approx(Settings.force_max_wait, abs=0.1)
    assert tracker.offset < 0.01


def test_offset_respects_limit():
    t, q, t_force, force = demo_take()
    tracker = fr.ForceTracker(fr.contact_phases(t_force, force, t, q), t_force, force, 4,
                              Settings(force_max_wait=100.0))
    tracker.reset(0.0)
    for k in range(600):  # pressing on nothing for 20 s
        tracker.step(5.0, 1 / 30, k / 30, 0.3)
    assert tracker.offset == pytest.approx(Settings.force_max_offset)
