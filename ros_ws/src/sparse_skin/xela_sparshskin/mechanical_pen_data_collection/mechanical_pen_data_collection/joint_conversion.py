"""Hardware Leap joints to sim joints, without ROS nodes or Qt (``conversions`` package)."""

from __future__ import annotations

import numpy as np


class HardwareToSim:
    """Hardware joints to sim joints, as ``convert_hardware_to_sim`` converts them."""

    def __init__(self) -> None:
        from conversions.hardware_to_sim_conversion import map_hardware_to_sim
        from conversions.sim_to_hardware_conversion import (
            get_joint_names,
            get_joint_ranges,
            load_joint_config,
            remap_joint_commands,
        )

        self._map = map_hardware_to_sim
        self._remap = remap_joint_commands
        config = load_joint_config()
        self.sim_names, _ = get_joint_names(config)
        leap = config["leapXela"]
        self._hw_ranges = get_joint_ranges(self.sim_names, leap["hardware"])
        self._sim_ranges = get_joint_ranges(self.sim_names, leap["sim"])

    def __call__(self, hw_joint_names: list[str], q_hw: np.ndarray) -> list[float]:
        """Sim angles (``sim_names`` order) of hardware joints ``q_hw`` (``hw_joint_names``)."""
        ordered = self._remap(self.sim_names, hw_joint_names, [float(v) for v in q_hw])
        return self._map(ordered, self._sim_ranges, self._hw_ranges)

    def to_hardware(self, sim_joint_names: list[str], q_sim: np.ndarray) -> list[float]:
        """Hardware angles (``sim_names`` order, the same joint names) of sim joints ``q_sim``
        (``sim_joint_names``), as ``convert_sim_to_hardware`` converts them."""
        from conversions.sim_to_hardware_conversion import map_sim_to_hardware

        ordered = self._remap(self.sim_names, sim_joint_names, [float(v) for v in q_sim])
        return map_sim_to_hardware(ordered, self._sim_ranges, self._hw_ranges)
