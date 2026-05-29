import json
import os
from typing import Any, List
from ament_index_python.packages import get_package_share_directory

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


def load_joint_config() -> dict[str, Any]:
    """
    Load the joint config JSON from the installed `xela_description` package.
    """
    resolved_path = os.path.join(
        get_package_share_directory("xela_description"),
        "joint_config.json",
    )
    if not os.path.exists(resolved_path):
        raise FileNotFoundError(
            f"Expected joint config at '{resolved_path}', but it does not exist. "
            "Make sure the 'xela_description' package is installed and contains joint_config.json."
        )

    with open(resolved_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_joint_ranges(ordered_joint_names, joint_config: dict[str, Any]) -> dict[str, list[float]]:
    """
    Build ordered lower/upper limits for each joint in `ordered_joint_names`.

    `joint_config` is expected to be a subtree like:
      joint_config["leapXela"]["hardware"]  (or ["sim"])
    with keys: {"thumb": {...}, "fingers": {...}}.
    """
    limits: dict[str, list[float]] = {"ll": [], "ul": []}

    for full_name in ordered_joint_names:
        prefix, joint = full_name.split("_", 1)
        if prefix == "th":
            section = joint_config["thumb"]
        else:
            section = joint_config["fingers"]

        limits["ll"].append(float(section[joint]["lower"]))
        limits["ul"].append(float(section[joint]["upper"]))

    return limits

def get_joint_names(joint_config: dict[str, Any]) -> tuple[list[str], list[int]]:
    hw_map = joint_config["leapXela"]["hardware"]["map"]
    joint_names = []
    idx = []

    for finger in ["th", "if", "mf", "rf"]:
        for key, value in hw_map[finger].items():
            idx.append(int(key))
            joint_names.append(f"{finger}_{value}")

    print(f"get_joint_names:: joint_names: {joint_names} \n idx: {idx}")
    print(f"get_joint_names:: joint_names::len:: {len(joint_names)} \n idx::len {len(idx)}")
    return joint_names, idx


def remap_joint_commands(ordered_joint_names, unordered_joint_names, unordered_joint_positions):
    """Reorder joint positions to match hardware joint order."""
    if len(unordered_joint_names) != len(unordered_joint_positions):
        raise ValueError(
            f"Joint name count ({len(unordered_joint_names)}) does not match "
            f"position count ({len(unordered_joint_positions)})"
        )
    by_name = dict(zip(unordered_joint_names, unordered_joint_positions))
    try:
        return [float(by_name[name]) for name in ordered_joint_names]
    except KeyError as e:
        missing = e.args[0]
        raise KeyError(
            f"Missing joint '{missing}' in command; "
            f"received: {unordered_joint_names}"
        ) from e


def map_sim_to_hardware(
    sim_value: List[float],
    sim_limits: dict[str, list[float]],
    hardware_limits: dict[str, list[float]],
) -> List[float]:
    """
    Linearly map each joint position from sim range to hardware range.

    `sim_limits` and `hardware_limits` must have list fields: {"ll": [...], "ul": [...]}.
    """
    out: list[float] = []
    for i, v in enumerate(sim_value):
        sim_ll = float(sim_limits["ll"][i])
        sim_ul = float(sim_limits["ul"][i])
        hw_ll = float(hardware_limits["ll"][i])
        hw_ul = float(hardware_limits["ul"][i])

        denom = sim_ul - sim_ll
        if denom == 0.0:
            raise ValueError(f"Invalid sim range at index {i}: lower == upper == {sim_ll}")

        alpha = (float(v) - sim_ll) / denom
        out.append(alpha * (hw_ul - hw_ll) + hw_ll)
    return out


class ConvertSimToHardware(Node):
    def __init__(self):
        super().__init__("convert_sim_to_hardware")
        self.declare_parameter("teleop_topic", "oculus_teleop_joint_commands")
        self.declare_parameter("hardware_topic", "cmd_xela")


        hardware_topic = str(self.get_parameter("hardware_topic").value)
        teleop_topic = str(self.get_parameter("teleop_topic").value)

        self.pub = self.create_publisher(JointState, hardware_topic, 10)
        self.sub = self.create_subscription(JointState, teleop_topic, self._callback, 10)

        joint_config = load_joint_config()
        self.joint_names, self.idx = get_joint_names(joint_config)
        self.hardware_joint_ranges = get_joint_ranges(self.joint_names, joint_config["leapXela"]["hardware"])
        self.sim_joint_ranges = get_joint_ranges(self.joint_names, joint_config["leapXela"]["sim"])

    def _callback(self, msg):
        ordered_joint_positions = remap_joint_commands(self.joint_names, msg.name, msg.position)
        ordered_joint_positions = map_sim_to_hardware(
            ordered_joint_positions,
            self.sim_joint_ranges,
            self.hardware_joint_ranges,
        )
        self.get_logger().info(f"unordered_joint_names: {msg.name} \n ordered_joint_names: {self.joint_names}")
        self.get_logger().info(f"unordered_joint_positions: {msg.position} \n ordered_joint_positions: {ordered_joint_positions}")

        out = JointState()
        out.header = msg.header
        out.name = list(self.joint_names)
        out.position = list(ordered_joint_positions)
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    convert_sim_to_hardware = ConvertSimToHardware()
    rclpy.spin(convert_sim_to_hardware)
    convert_sim_to_hardware.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()