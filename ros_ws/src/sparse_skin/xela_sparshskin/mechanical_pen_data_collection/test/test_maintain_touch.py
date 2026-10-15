"""Maintain touch against the simulated finger of ``test_click_press``: joint springs pressing a
pen surface with friction (no click)."""

import numpy as np
from test_click_press import J, KP, NOISE, Thumb, Z, tilt, unit

from mechanical_pen_data_collection import maintain_touch as mt

HOLD = 2.0
TARGET = NOISE + HOLD  # relative: hold_force above the force at the entry (the noise)


class Kin:
    def __init__(self, normal=Z):
        self.n = unit(normal)

    def point_and_jacobian(self, q):
        return J @ q, J

    def point(self, q_hand):
        return None if q_hand is None else J @ q_hand

    def normal(self, q):
        return self.n


def run(finger, axis=Z, entry=1.0, exit_=6.0, seconds=12.0, reverse=False, during=None,
        **settings):
    """Plays a take over a region ``entry``-``exit_`` (backwards if ``reverse``) holding the
    recorded joints still; returns (touch, finger, take time held, forces over the region's
    hold, local at the end). ``during(now, finger)`` can change the finger as it goes."""
    region = mt.TouchPressRegion(entry=entry, exit=exit_, axis=unit(axis), kin=Kin(),
                                 kp=KP / KP.max())
    touch = mt.TouchPress([region], mt.MaintainTouchSettings(**{"hold_force": HOLD, **settings}))
    q_rec = finger.q.copy()
    start = max(entry, exit_) + 1.0 if reverse else 0.0
    touch.reset(start)
    dt, now, held = 1 / 30, 0.0, 0.0
    goal = q_rec
    held_forces = []
    local = start
    while now < seconds:
        now += dt
        local = start - (now - held) if reverse else start + now - held
        if during is not None:
            during(now, finger)
        finger.settle(goal)
        step = touch.step(local, dt, now, q_rec, finger.q.copy(), finger.force,
                          finger.effort)
        if touch.state == mt.HOLD and touch._t > 1.0:
            held_forces.append(finger.force)
        if step is None:
            goal = q_rec
            continue
        goal = step.q
        if step.hold:
            held += dt
    return touch, finger, held, np.array(held_forces), local


def events(touch):
    return [e["event"] for e in touch.trace]


def test_approaches_until_contact_then_holds_the_force():
    touch, finger, held, forces, _ = run(Thumb(np.zeros(4), clicks=False))
    assert events(touch)[:2] == ["approach", "contact"]
    assert "release" in events(touch)
    # The take waited while approaching the 2 mm gap (10 mm/s) ...
    assert 0.1 < held < 0.6
    # ... then the force was held at hold_force over the region.
    assert len(forces) and abs(np.median(forces) - TARGET) < 0.2
    assert np.all(np.abs(forces[len(forces) // 2:] - TARGET) < 0.1)
    # Back on the take after the region.
    assert touch.state == ""
    assert np.allclose(finger.q, 0.0, atol=1e-3)


def test_force_along_a_tilted_axis():
    axis = tilt(25.0)
    touch, finger, _, forces, _ = run(Thumb(np.zeros(4), n=axis, clicks=False), axis=axis)
    assert abs(np.median(forces) - TARGET) < 0.2


def test_lost_contact_approaches_again():
    moved = []

    def pen_moves_away(now, finger):
        if now >= 3.0 and not moved:
            moved.append(now)
            finger.surface += 0.01

    _, _, held_once, _, _ = run(Thumb(np.zeros(4), clicks=False))
    touch, _, held, forces, _ = run(Thumb(np.zeros(4), clicks=False), during=pen_moves_away)
    assert events(touch).count("contact") == 2
    assert events(touch).count("approach") == 2
    assert held > held_once + 0.05  # held for the second approach too
    assert abs(forces[-1] - TARGET) < 0.3


def test_gives_up_without_a_pen_and_plays_the_take():
    touch, finger, held, _, local = run(Thumb(np.zeros(4), pen=False, clicks=False),
                                        max_travel=0.01)
    assert "give up" in events(touch)
    assert held < 1.5  # 10 mm at 10 mm/s
    assert local > 6.0  # the take went on past the region
    assert np.allclose(finger.q, 0.0, atol=1e-3)


def test_reverse_enters_at_the_regions_end():
    touch, _, held, forces, local = run(
        Thumb(np.zeros(4), clicks=False), entry=6.0, exit_=1.0, reverse=True
    )
    assert touch.trace[0]["region"] == [6.0, 1.0]
    assert held > 0.1
    assert abs(np.median(forces) - TARGET) < 0.2
    assert local < 1.0


def test_axis_from_approach_motion_or_pad_normal():
    t = np.linspace(0.0, 2.0, 21)
    q_toward = lambda at: np.linalg.pinv(J) @ (Z * 0.01 * at)  # noqa: E731
    axis, source = mt.touch_axis(Kin(), q_toward, 1.0, False, (0.0, 2.0))
    assert np.allclose(axis, Z, atol=1e-6) and source.startswith("approach")
    # Reversed: the motion toward the entry runs back in take time, away from the pad.
    axis, source = mt.touch_axis(Kin(), q_toward, 1.0, True, (t[0], t[-1]))
    assert source.startswith("pad normal") and np.allclose(axis, Z)
    still = lambda at: np.zeros(4)  # noqa: E731
    axis, source = mt.touch_axis(Kin(normal=tilt(10.0)), still, 1.0, False, (0.0, 2.0))
    assert np.allclose(axis, tilt(10.0)) and "only" in source


class CurledFinger(Thumb):
    """A finger whose fingertip taxels read ``offset`` without any contact (skin stretch)."""

    offset = 3.0

    @property
    def force(self):
        return self.offset + super().force


def test_force_offset_without_contact_is_tared_at_entry():
    touch, finger, held, forces, _ = run(CurledFinger(np.zeros(4), clicks=False))
    entry = CurledFinger.offset + NOISE
    # It approached the 2 mm gap instead of taking the offset for contact ...
    assert events(touch)[:2] == ["approach", "contact"]
    assert held > 0.1
    assert touch.trace[1]["why"].split(";")[1].strip().startswith("travel 2.")
    # ... and held hold_force above the force at the entry.
    assert abs(np.median(forces) - (entry + HOLD)) < 0.2


def test_absolute_forces_take_the_offset_for_contact():
    touch, _, held, _, _ = run(CurledFinger(np.zeros(4), clicks=False), relative=False)
    assert held == 0.0
    assert "travel 0.0 mm" in touch.trace[1]["why"]
