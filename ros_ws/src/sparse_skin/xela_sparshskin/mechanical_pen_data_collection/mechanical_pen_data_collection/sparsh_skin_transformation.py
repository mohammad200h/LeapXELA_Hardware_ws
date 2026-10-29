#!/usr/bin/env python3
"""Sparsh-skin transformation of the Play on hand episodes for the LEQ_DV3 world model.

Service ``~/transform`` (leapxela_sparshskin_msgs/SparshSkinTransform): preprocesses the
labelled episodes of ``recordings_dir`` as Sparsh-skin does (``sparsh_processing``), with the
no-contact baseline of ``baseline_file`` (a Baseline tab recording), and writes them to
``output_dir`` as LEQ_DV3 ``data/leap/convert_episodes.py`` input. Called by
record_demonstration's Process tab (Sparsh-skin transform); it answers when every episode is
written, logging each one and publishing its progress on ``~/progress`` (std_msgs/String, JSON
``{"done", "total", "text"}``) for the tab's progress bar.

ROS parameters:
  - freq (float, default 100.0): step rate used when a request has none
"""

from __future__ import annotations

import json
import os

import rclpy
from leapxela_sparshskin_msgs.srv import SparshSkinTransform
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String

from mechanical_pen_data_collection import sparsh_processing
from mechanical_pen_data_collection.joint_conversion import HardwareToSim


class SparshSkinTransformation(Node):
    def __init__(self) -> None:
        super().__init__("sparsh_skin_transformation")
        self._freq = float(self.declare_parameter("freq", sparsh_processing.FREQ).value)
        self._to_sim = HardwareToSim()
        self._progress = self.create_publisher(String, "~/progress", 10)
        self.create_service(
            SparshSkinTransform, "~/transform", self._on_transform,
            callback_group=MutuallyExclusiveCallbackGroup(),
        )
        self.get_logger().info(f"Serving {self.get_fully_qualified_name()}/transform")

    def _report(self, done: int, total: int, text: str) -> None:
        """Logs a recording done and publishes the progress."""
        if done:
            self.get_logger().info(text)
        self._progress.publish(String(data=json.dumps(
            {"done": done, "total": total, "text": text}
        )))

    def _on_transform(self, request, response):
        recordings_dir = request.recordings_dir
        if not os.path.isdir(recordings_dir):
            response.success = False
            response.message = f"{recordings_dir!r} is not a directory"
            return response
        out_dir = request.output_dir or os.path.join(
            recordings_dir, sparsh_processing.DEFAULT_OUTPUT_NAME
        )
        freq = float(request.freq) if request.freq > 0 else self._freq
        baseline = request.baseline_file
        if baseline and not os.path.isfile(baseline):
            response.success = False
            response.message = f"baseline {baseline!r} is not a file"
            return response
        self.get_logger().info(
            f"Transforming {recordings_dir} -> {out_dir} at {freq:g} Hz, baseline "
            f"{baseline or 'of each recording'}"
        )
        try:
            manifest = sparsh_processing.write_dataset(
                recordings_dir, out_dir, self._to_sim, list(request.recordings), freq,
                bool(request.overwrite), progress=self._report,
                baseline_file=baseline,
            )
        except Exception as e:  # noqa: BLE001 - reported to the caller
            response.success = False
            response.message = str(e)
            return response
        failed = sum(why.startswith("failed") for why in manifest["skipped"].values())
        response.success = True
        response.written = len(manifest["written"])
        response.kept = len(manifest["kept"])
        response.skipped = len(manifest["skipped"])
        response.files = manifest["written"] + manifest["kept"]
        response.xela_mean = [float(v) for v in manifest["xela_mean"]]
        response.xela_std = [float(v) for v in manifest["xela_std"]]
        response.message = (
            f"{response.written} episodes written, {response.kept} kept, "
            f"{response.skipped} skipped ({failed} failed) in {out_dir}, baseline "
            f"{os.path.basename(baseline) if baseline else 'of each recording'}"
        )
        self.get_logger().info(response.message)
        return response


def main(args=None):
    rclpy.init(args=args)
    node = SparshSkinTransformation()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
