from typing import List

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

from conversions.sim_to_hardware_conversion import (
    _has_uniform_scale,
    get_joint_names,
    get_joint_ranges,
    load_joint_config,
    remap_joint_commands,
)


def _inverse_piecewise_map(
    value: float,
    sim_ll: float,
    sim_zero: float,
    sim_ul: float,
    hw_ll: float,
    hw_zero: float,
    hw_ul: float,
) -> float:
    """
    Invert the two-segment affine map hardware [ll, zero, ul] -> sim.

    `_piecewise_map` picks its segment by `sim <= sim_zero`, and either the
    sim or hardware limits may be inverted (lower > upper). Each segment is
    inverted independently and the candidate that satisfies that same
    condition is returned. A degenerate hardware side collapses to `sim_zero`.
    """
    v = float(value)
    if abs(v - hw_zero) < 1e-12:
        return sim_zero

    if hw_ul != hw_zero:
        upper = sim_zero + (v - hw_zero) * (sim_ul - sim_zero) / (hw_ul - hw_zero)
        if upper > sim_zero:
            return upper

    if hw_zero != hw_ll:
        lower = sim_ll + (v - hw_ll) * (sim_zero - sim_ll) / (hw_zero - hw_ll)
        if lower <= sim_zero:
            return lower

    return sim_zero


def _inverse_uniform_offset_map(value: float, hw_zero: float, inverted: bool) -> float:
    """Map a hardware encoder angle to a 0-centered sim angle with 1:1 scale."""
    if inverted:
        return hw_zero - value
    return value - hw_zero


def map_hardware_to_sim(
    hardware_value: List[float],
    sim_limits: dict[str, list[float]],
    hardware_limits: dict[str, list[float]],
) -> List[float]:
    """
    Map hardware encoder angles to sim joint angles.

    Exact inverse of `map_sim_to_hardware`: the same per-joint test selects
    between the constant-offset map (with optional sign flip) and the
    piecewise-linear fallback anchored at lower / zero / upper.
    """
    out: list[float] = []
    for i, v in enumerate(hardware_value):
        sim_ll = float(sim_limits["ll"][i])
        sim_ul = float(sim_limits["ul"][i])
        sim_zero = float(sim_limits["zero"][i])
        hw_ll = float(hardware_limits["ll"][i])
        hw_ul = float(hardware_limits["ul"][i])
        hw_zero = float(hardware_limits["zero"][i])

        if abs(sim_zero) < 1e-9 and _has_uniform_scale(
            sim_ll, sim_zero, sim_ul, hw_ll, hw_zero, hw_ul
        ):
            out.append(_inverse_uniform_offset_map(float(v), hw_zero, hw_ll > hw_ul))
        else:
            out.append(
                _inverse_piecewise_map(v, sim_ll, sim_zero, sim_ul, hw_ll, hw_zero, hw_ul)
            )
    return out


class ConvertHardwareToSim(Node):
    def __init__(self):
        super().__init__("convert_hardware_to_sim")
        self.declare_parameter("hardware_topic", "leap_state")
        self.declare_parameter("sim_topic", "leap_state_sim")

        hardware_topic = str(self.get_parameter("hardware_topic").value)
        sim_topic = str(self.get_parameter("sim_topic").value)

        self.pub = self.create_publisher(JointState, sim_topic, 10)
        self.sub = self.create_subscription(JointState, hardware_topic, self._callback, 10)

        joint_config = load_joint_config()
        self.joint_names, self.idx = get_joint_names(joint_config)
        leap_xela = joint_config["leapXela"]
        self.hardware_joint_ranges = get_joint_ranges(
            self.joint_names, leap_xela["hardware"]
        )
        self.sim_joint_ranges = get_joint_ranges(
            self.joint_names, leap_xela["sim"]
        )

    def _callback(self, msg):
        ordered_joint_positions = remap_joint_commands(
            self.joint_names, msg.name, msg.position
        )
        ordered_joint_positions = map_hardware_to_sim(
            ordered_joint_positions,
            self.sim_joint_ranges,
            self.hardware_joint_ranges,
        )
        self.get_logger().debug(
            f"hardware_joint_positions: {msg.position}\n"
            f"sim_joint_positions: {ordered_joint_positions}"
        )

        out = JointState()
        out.header = msg.header
        out.name = list(self.joint_names)
        out.position = list(ordered_joint_positions)
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    convert_hardware_to_sim = ConvertHardwareToSim()
    rclpy.spin(convert_hardware_to_sim)
    convert_hardware_to_sim.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
