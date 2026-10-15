"""Click setting search against a simulated pen that clicks for some press directions."""

from dataclasses import dataclass

import numpy as np
import pytest

from mechanical_pen_data_collection import click_search as cs

DT = 1 / 30


@dataclass
class Settings:
    force_push_rate: float = 0.15
    force_max_offset: float = 0.25


@pytest.mark.parametrize("n", [2, 3, 4])
def test_candidates_start_first_and_widen(n):
    start = np.arange(1.0, n + 1.0)
    dirs = cs.candidate_directions(start)
    assert np.allclose(dirs[0], start / np.linalg.norm(start))
    assert all(abs(np.linalg.norm(d) - 1.0) < 1e-9 for d in dirs)
    angles = [cs.angle_deg(d, dirs[0]) for d in dirs]
    assert all(b >= a - 1e-6 for a, b in zip(angles, angles[1:]))
    assert max(angles) <= 90.0 + 1e-6
    for i, a in enumerate(dirs):
        assert all(cs.angle_deg(a, b) >= cs.DUPLICATE_DEG for b in dirs[:i])


def test_slider_values_fit_range():
    v = cs.slider_values(np.array([0.2, -0.4, 0.1]))
    assert np.allclose(v, [0.5, -1.0, 0.25])


def run(probe, clicks, force=None, base=None, limit=20000):
    """Steps ``probe`` with a pen that clicks (one pulse) when ``clicks(q)`` is true."""
    now, count, on, was = 0.0, 0, False, False
    qs = []
    q = np.zeros_like(probe.base) if base is None else base
    for _ in range(limit):
        hit = clicks(q)
        if hit and not was:
            count += 1
        on, was = hit, hit
        q = probe.step(now, DT, q, on, count, force(q) if force else None)
        qs.append((probe.state, probe.index, q))
        now += DT
        if probe.done:
            return qs
    raise AssertionError("probe did not finish")


def test_finds_clicking_direction():
    base = np.array([0.1, 0.2, 0.3, 0.4])
    true = cs.unit(np.array([0.0, 1.0, 1.0, 0.0]))
    start = cs.unit(np.array([1.0, 1.0, 0.0, 0.0]))  # 60 deg away

    def clicks(q):
        d = q - base
        depth = float(np.dot(d, true))
        return depth > 0.1 and cs.angle_deg(d, true) < 20.0

    probe = cs.ClickProbe(base, cs.candidate_directions(start), Settings())
    qs = run(probe, clicks)
    assert probe.found is not None
    assert cs.angle_deg(probe.found, true) < 20.0
    assert np.allclose(qs[-1][2], base)  # backed off before finishing
    # Between trials the finger is back at the base pose.
    for (_, i0, _), (_, i1, q1) in zip(qs, qs[1:]):
        if i1 != i0:
            assert np.allclose(q1, base)


def test_not_found_and_force_limit():
    base = np.zeros(3)
    dirs = cs.candidate_directions(np.array([1.0, 0.0, 0.0]), max_angle_deg=15.0)
    probe = cs.ClickProbe(base, dirs, Settings(), peak=1.0)
    deepest = []

    def force(q):
        deepest.append(np.linalg.norm(q - base))
        return 20.0 * np.linalg.norm(q - base)  # reaches FORCE_LIMIT * peak at 0.075 rad

    run(probe, lambda q: False, force)
    assert probe.found is None
    assert probe.message == "no click in any direction"
    assert max(deepest) < 0.075 + Settings.force_push_rate * DT + 1e-9


def test_cancel_retracts():
    base = np.zeros(2)
    probe = cs.ClickProbe(base, cs.candidate_directions(np.array([1.0, 0.0])), Settings())
    q = np.zeros(2)
    for k in range(60):
        q = probe.step(k * DT, DT, q, False, 0)
    probe.cancel()
    k = 60
    while not probe.done:
        q = probe.step(k * DT, DT, q, False, 0)
        k += 1
    assert probe.found is None
    assert np.allclose(q, base)
