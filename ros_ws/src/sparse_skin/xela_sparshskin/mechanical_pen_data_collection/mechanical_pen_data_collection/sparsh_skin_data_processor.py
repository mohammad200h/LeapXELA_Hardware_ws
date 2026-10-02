#!/usr/bin/env python3
"""Combine Xela hardware readings with taxel forward kinematics.

Subscribes:
  - leapxela_sparshskin_msgs/TaxelFrames on ``taxel_frames`` (fk_taxels)
  - xela_server_ros2/SensStream on ``xServTopic`` (xela_service)
"""

from __future__ import annotations

import threading

import numpy as np

import rclpy
from rclpy.node import Node
from leapxela_sparshskin_msgs.msg import TaxelFrames
from xela_server_ros2.msg import SensStream


def taxel_frames_to_arrays(msg: TaxelFrames) -> dict[str, np.ndarray]:
    """Unpack TaxelFrames into (N, ...) arrays in FK flatten order."""
    n = len(msg.taxel_ids)
    out = {
        "taxel_ids": np.asarray(msg.taxel_ids, dtype=np.int32),
        "patch_ids": np.asarray(msg.patch_ids, dtype=np.uint8),
        "positions": np.asarray(msg.positions, dtype=np.float32).reshape(n, 3),
        "rotations": np.asarray(msg.rotations, dtype=np.float32).reshape(n, 3, 3),
    }
    if msg.forces_world:
        out["forces_world"] = np.asarray(msg.forces_world, dtype=np.float32).reshape(n, 3)
    if msg.forces_local:
        out["forces_local"] = np.asarray(msg.forces_local, dtype=np.float32).reshape(n, 3)
    return out


def sens_stream_to_arrays(msg: SensStream) -> dict[str, np.ndarray]:
    """Flatten SensStream into arrays indexed by hardware taxel id.

    Sensors are concatenated in ``sensor_pos`` order. ``forces`` is empty when
    xela_server does not provide calibrated values.
    """
    sensors = sorted(msg.sensors, key=lambda s: int(s.sensor_pos))
    taxels = [[t.x, t.y, t.z] for s in sensors for t in s.taxels]
    forces = [[f.x, f.y, f.z] for s in sensors for f in s.forces]
    return {
        "taxels": np.asarray(taxels, dtype=np.uint16).reshape(-1, 3),
        "forces": np.asarray(forces, dtype=np.float32).reshape(-1, 3),
    }


class SparshSkinDataProcessor(Node):
    """Cache the latest FK taxel frames and Xela readings and process them together."""

    def __init__(self) -> None:
        super().__init__("sparsh_skin_data_processor")

        taxel_fk_topic = self.declare_parameter("taxel_fk_topic", "taxel_frames").value
        xela_topic = self.declare_parameter("xela_topic", "xServTopic").value

        self._lock = threading.Lock()
        self._taxel_fk: dict[str, np.ndarray] | None = None
        self._xela: dict[str, np.ndarray] | None = None

        self.create_subscription(TaxelFrames, taxel_fk_topic, self._on_taxel_fk, 10)
        self.create_subscription(SensStream, xela_topic, self._on_xela, 10)

        self.get_logger().info(
            f"Listening for taxel FK on '{taxel_fk_topic}' "
            f"and SensStream on '{xela_topic}'"
        )

    def _on_taxel_fk(self, msg: TaxelFrames) -> None:
        frames = taxel_frames_to_arrays(msg)
        with self._lock:
            self._taxel_fk = frames

    def _on_xela(self, msg: SensStream) -> None:
        xela = sens_stream_to_arrays(msg)
        with self._lock:
            self._xela = xela
            frames = self._taxel_fk
        if frames is None:
            self.get_logger().info("Waiting for TaxelFrames...", throttle_duration_sec=2.0)
            return
        self.process(frames, xela)

    def process(self, frames: dict[str, np.ndarray], xela: dict[str, np.ndarray]) -> None:
        """Handle one Xela reading paired with the latest FK frames.

        ``frames`` entries are in FK flatten order; ``xela`` entries are indexed
        by hardware taxel id, so ``xela["taxels"][frames["taxel_ids"]]`` aligns
        the raw readings with ``frames["positions"]``.
        """
        n_hw = xela["taxels"].shape[0]
        if n_hw <= int(frames["taxel_ids"].max()):
            self.get_logger().warn(
                f"Xela stream has {n_hw} taxels, FK expects "
                f"{frames['taxel_ids'].shape[0]}",
                throttle_duration_sec=2.0,
            )
            return
        raw_fk_order = xela["taxels"][frames["taxel_ids"]]
        self.get_logger().info(
            f"Paired xela taxels {raw_fk_order.shape} (forces {xela['forces'].shape}) "
            f"with FK positions {frames['positions'].shape}",
            throttle_duration_sec=1.0,
        )


def main(args=None):
    rclpy.init(args=args)
    node = SparshSkinDataProcessor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
