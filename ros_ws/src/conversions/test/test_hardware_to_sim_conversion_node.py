import json
from pathlib import Path

import pytest


def _load_workspace_joint_config() -> dict:
    """Load the workspace copy of `xela_description/joint_config.json`."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "xela_description" / "joint_config.json"
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    raise FileNotFoundError(
        "Could not find xela_description/joint_config.json in workspace parents"
    )


def test_map_hardware_to_sim():
    from samples import (
        get_hardware_joints_at_zero_position,
        get_joint_ranges_hw,
        get_joint_ranges_sim,
    )
    from conversions.hardware_to_sim_conversion import map_hardware_to_sim

    joint_ranges_hw = get_joint_ranges_hw()
    joint_ranges_sim = get_joint_ranges_sim()

    sim_values = map_hardware_to_sim(
        joint_ranges_hw["ll"], joint_ranges_sim, joint_ranges_hw
    )
    assert sim_values == pytest.approx(joint_ranges_sim["ll"], rel=1e-5, abs=1e-2), (
        "mapping at lower limits failed"
    )

    sim_values = map_hardware_to_sim(
        joint_ranges_hw["ul"], joint_ranges_sim, joint_ranges_hw
    )
    assert sim_values == pytest.approx(joint_ranges_sim["ul"], rel=1e-5, abs=1e-2), (
        "mapping at upper limits failed"
    )

    sim_values = map_hardware_to_sim(
        get_hardware_joints_at_zero_position(), joint_ranges_sim, joint_ranges_hw
    )
    assert sim_values == pytest.approx([0.0] * 16, abs=1e-6), (
        "mapping at zero position failed"
    )


def test_hardware_to_sim_inverts_sim_to_hardware():
    from samples import get_ordered_joint_state_message_with_index_as_joint_value
    from conversions.hardware_to_sim_conversion import map_hardware_to_sim
    from conversions.sim_to_hardware_conversion import (
        get_joint_ranges,
        map_sim_to_hardware,
    )

    joint_config = _load_workspace_joint_config()
    names = get_ordered_joint_state_message_with_index_as_joint_value().name
    hw = get_joint_ranges(names, joint_config["leapXela"]["hardware"])
    sim = get_joint_ranges(names, joint_config["leapXela"]["sim"])

    for alpha in (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0):
        sim_values = [ll + alpha * (ul - ll) for ll, ul in zip(sim["ll"], sim["ul"])]
        round_trip = map_hardware_to_sim(
            map_sim_to_hardware(sim_values, sim, hw), sim, hw
        )
        assert round_trip == pytest.approx(sim_values, abs=1e-9), (
            f"round trip failed at alpha={alpha}"
        )
