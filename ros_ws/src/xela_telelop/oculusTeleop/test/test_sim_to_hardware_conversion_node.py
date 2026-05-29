import json
import time
from pathlib import Path

import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState


def _load_workspace_joint_config() -> dict:
    """
    Load the workspace copy of `xela_description/joint_config.json`.

    We avoid `ament_index_python.get_package_share_directory()` here because in
    test environments the `xela_description` share directory may not be installed.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "xela_description" / "joint_config.json"
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    raise FileNotFoundError(
        "Could not find xela_description/joint_config.json in workspace parents"
    )


def test_get_joint_names():
    from oculusTeleop.sim_to_hardware_conversion import get_joint_names
    from samples import get_ordered_joint_state_message_with_index_as_joint_value

    joint_config = _load_workspace_joint_config()
    joint_names, idx = get_joint_names(joint_config)
    assert len(joint_names) == 16
    assert len(idx) == 16

    hardware_joint_names = (
        get_ordered_joint_state_message_with_index_as_joint_value().name
    )
    assert joint_names == hardware_joint_names


def test_get_joint_ranges():
    from oculusTeleop.sim_to_hardware_conversion import get_joint_ranges
    from samples import (
        get_joint_ranges_hw,
        get_joint_ranges_sim,
        get_ordered_joint_state_message_with_index_as_joint_value,
    )

    joint_config = _load_workspace_joint_config()
    ordered_joint_names = (
        get_ordered_joint_state_message_with_index_as_joint_value().name
    )
    joint_ranges_hw = get_joint_ranges(
        ordered_joint_names, joint_config["leapXela"]["hardware"]
    )
    assert len(joint_ranges_hw["ll"]) == 16
    assert len(joint_ranges_hw["ul"]) == 16
    assert joint_ranges_hw["ll"] == pytest.approx(
        get_joint_ranges_hw()["ll"], rel=1e-2, abs=1e-2
    )
    assert joint_ranges_hw["ul"] == pytest.approx(
        get_joint_ranges_hw()["ul"], rel=1e-2, abs=1e-2
    )
    assert joint_ranges_hw["zero"] == pytest.approx(
        get_joint_ranges_hw()["zero"], rel=1e-2, abs=1e-2
    )

    joint_ranges_sim = get_joint_ranges(
        ordered_joint_names, joint_config["leapXela"]["sim"]
    )
    assert len(joint_ranges_sim["ll"]) == 16
    assert len(joint_ranges_sim["ul"]) == 16
    assert len(joint_ranges_sim["zero"]) == 16
    assert joint_ranges_sim["ll"] == pytest.approx(
        get_joint_ranges_sim()["ll"], rel=1e-5, abs=1e-2
    )
    assert joint_ranges_sim["ul"] == pytest.approx(
        get_joint_ranges_sim()["ul"], rel=1e-5, abs=1e-2
    )
    assert joint_ranges_sim["zero"] == get_joint_ranges_sim()["zero"]


def test_remap_joint_commands():
    from samples import (
        get_ordered_joint_state_message_with_index_as_joint_value,
        get_unordered_joint_state_message_with_index_as_joint_value,
    )
    from oculusTeleop.sim_to_hardware_conversion import remap_joint_commands

    unordered_joint_state_message = (
        get_unordered_joint_state_message_with_index_as_joint_value()
    )
    ordered_joint_state_message = (
        get_ordered_joint_state_message_with_index_as_joint_value()
    )

    assert list(
        remap_joint_commands(
            ordered_joint_state_message.name,
            unordered_joint_state_message.name,
            unordered_joint_state_message.position,
        )
    ) == list(ordered_joint_state_message.position)


def test_map_sim_to_hardware():
    from samples import (
        get_hardware_joints_at_zero_position,
        get_joint_ranges_hw,
        get_joint_ranges_sim,
    )
    from oculusTeleop.sim_to_hardware_conversion import map_sim_to_hardware

    joint_ranges_hw = get_joint_ranges_hw()
    joint_ranges_sim = get_joint_ranges_sim()
    hardware_joints_at_zero_position = get_hardware_joints_at_zero_position()

    sim_values = joint_ranges_sim["ll"]
    hardware_ll = joint_ranges_hw["ll"]
    hardware_values = map_sim_to_hardware(
        sim_values, joint_ranges_sim, joint_ranges_hw
    )
    assert hardware_values == pytest.approx(hardware_ll, rel=1e-5, abs=1e-2), (
        "mapping at lower limits failed"
    )

    sim_values = joint_ranges_sim["ul"]
    hardware_ul = joint_ranges_hw["ul"]
    hardware_values = map_sim_to_hardware(
        sim_values, joint_ranges_sim, joint_ranges_hw
    )
    assert hardware_values == pytest.approx(hardware_ul, rel=1e-5, abs=1e-2), (
        "mapping at upper limits failed"
    )

    sim_values = [0.0] * 16
    hardware_values = map_sim_to_hardware(
        sim_values, joint_ranges_sim, joint_ranges_hw
    )
    assert hardware_values == pytest.approx(
        hardware_joints_at_zero_position, rel=1e-5, abs=1e-2
    ), "mapping at zero position failed"


def _test_convert_sim_to_hardware_publishes_ordered_and_mapped(monkeypatch):
    from oculusTeleop import sim_to_hardware_conversion as conv
    from samples import (
        get_ordered_joint_state_message_with_index_as_joint_value,
        get_unordered_joint_state_message_with_index_as_joint_value,
    )

    joint_config = _load_workspace_joint_config()
    monkeypatch.setattr(conv, "load_joint_config", lambda: joint_config)

    unordered_joint_state_message = (
        get_unordered_joint_state_message_with_index_as_joint_value()
    )
    ordered_joint_state_message = (
        get_ordered_joint_state_message_with_index_as_joint_value()
    )

    rclpy.init()
    ex = None
    dut = None
    helper = None
    try:
        dut = conv.ConvertSimToHardware()
        helper = Node("test_helper")

        received = {}

        def on_msg(msg: JointState):
            received["msg"] = msg

        sub = helper.create_subscription(JointState, "cmd_xela", on_msg, 10)
        pub = helper.create_publisher(
            JointState, "oculus_teleop_joint_commands", 10
        )

        ex = SingleThreadedExecutor()
        ex.add_node(dut)
        ex.add_node(helper)

        deadline = time.time() + 2.0
        while time.time() < deadline and "msg" not in received:
            pub.publish(unordered_joint_state_message)
            ex.spin_once(timeout_sec=0.05)

        assert "msg" in received, (
            "Timed out waiting for converted JointState on cmd_xela"
        )
        out: JointState = received["msg"]
        assert list(out.name) == ordered_joint_state_message.name
        assert list(out.position) == ordered_joint_state_message.position

        helper.destroy_subscription(sub)
        helper.destroy_publisher(pub)
    finally:
        if ex is not None:
            try:
                if dut is not None:
                    ex.remove_node(dut)
                if helper is not None:
                    ex.remove_node(helper)
                ex.shutdown()
            except Exception:
                pass
        try:
            if dut is not None:
                dut.destroy_node()
        except Exception:
            pass
        try:
            if helper is not None:
                helper.destroy_node()
        except Exception:
            pass
        rclpy.shutdown()
