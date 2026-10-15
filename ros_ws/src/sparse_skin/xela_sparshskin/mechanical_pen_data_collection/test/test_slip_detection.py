import numpy as np

from mechanical_pen_data_collection.slip_detection import (
    FORCE_DROP,
    SPOT_SHIFT,
    SlipDetector,
)

# 6 x 5 taxels, 2 mm apart, on a flat pad.
GRID = np.array([[x * 0.002, y * 0.002, 0.0] for y in range(6) for x in range(5)])


def press_at(index: int, force: float = 2.0) -> np.ndarray:
    """Magnitudes of a contact centred on taxel ``index``."""
    mags = np.full(len(GRID), 0.01)
    mags[index] = force
    return mags


def run(detector, samples, dt=0.01, in_contact=True):
    events, t = [], 0.0
    for mags in samples:
        event = detector.update(t, mags, in_contact)
        if event is not None:
            events.append(event)
        t += dt
    return events


def test_steady_contact_has_no_slip():
    assert run(SlipDetector(GRID), [press_at(12)] * 200) == []


def test_spot_moving_on_the_pad_is_a_slip():
    events = run(SlipDetector(GRID), [press_at(12)] * 50 + [press_at(14)] * 50)
    assert [e.cue for e in events] == [SPOT_SHIFT]
    assert events[0].value > 0.0025


def test_force_falling_out_is_a_slip():
    samples = [press_at(12, 2.0)] * 50 + [press_at(12, 1.0)] * 50
    events = run(SlipDetector(GRID), samples)
    assert [e.cue for e in events] == [FORCE_DROP]


def test_no_slip_without_contact():
    samples = [press_at(12)] * 50 + [press_at(14, 0.5)] * 50
    assert run(SlipDetector(GRID), samples, in_contact=False) == []


def test_refractory_period_merges_one_slip():
    # The spot sliding over several taxels within the refractory time is one slip.
    samples = [press_at(10)] * 50 + [press_at(12)] * 5 + [press_at(14)] * 5 + [press_at(12)] * 40
    assert len(run(SlipDetector(GRID), samples)) == 1


def test_without_grid_only_force_drop():
    samples = [press_at(12)] * 50 + [press_at(14)] * 50
    assert run(SlipDetector(None), samples) == []
