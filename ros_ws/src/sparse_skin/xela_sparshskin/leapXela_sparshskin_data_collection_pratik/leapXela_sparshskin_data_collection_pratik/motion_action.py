#!/usr/bin/env python3
"""ROS 2 action server that plays named hand motions on oculus_teleop_joint_commands."""

from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET

import numpy as np
import rclpy
from ament_index_python.packages import get_package_share_directory
from leapxela_sparshskin_msgs.action import ExecuteMotion
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState

from leapXela_sparshskin_data_collection_pratik.motion import (
    GraspProfile,
    close_hand,
    load_hand_pose,
    motion_generator,
    pregrip_targets,
)

PROFILE_MOTIONS = frozenset({"squeeze", "regrasp", "tap", "shear", "hold", "pulse"})
_ACTUATED_JOINT_TYPES = frozenset({"revolute", "prismatic", "continuous"})


def get_joint_limit_from_robot_description(
    path: str,
) -> tuple[np.ndarray, list[str]]:
    """Parse actuated joint limits and names from a URDF, preserving XML order.

    Returns:
        ctrlrange: (N, 2) array of [lower, upper] limits
        joint_names: joint names in the same order as ctrlrange rows
    """
    with open(path, "r", encoding="utf-8") as f:
        # Generated URDFs may have leading whitespace before the XML declaration.
        root = ET.fromstring(f.read().lstrip())

    names: list[str] = []
    limits: list[list[float]] = []
    for joint in root.findall("joint"):
        joint_type = joint.get("type", "")
        if joint_type not in _ACTUATED_JOINT_TYPES:
            continue
        name = joint.get("name")
        if not name:
            continue
        limit = joint.find("limit")
        if limit is None:
            lower, upper = 0.0, 0.0
        else:
            lower = float(limit.get("lower", "0.0"))
            upper = float(limit.get("upper", "0.0"))
        names.append(name)
        limits.append([lower, upper])

    if not names:
        raise ValueError(f"No actuated joints found in URDF: {path}")
    return np.asarray(limits, dtype=float), names


class MotionActionServer(Node):
    """Accept motion goals and publish JointState commands."""

    def __init__(self) -> None:
        super().__init__("motion_action_server")

        self.declare_parameter("joint_topic", "repeator_joint_commands")
        self.declare_parameter("publish_rate_hz", 1.0)
        self.declare_parameter("action_name", "execute_motion")
        self.declare_parameter("profile_duration_s", 5.0)

        joint_topic = self.get_parameter("joint_topic").get_parameter_value().string_value
        action_name = self.get_parameter("action_name").get_parameter_value().string_value
        self._publish_rate_hz = (
            self.get_parameter("publish_rate_hz").get_parameter_value().double_value
        )
        if self._publish_rate_hz <= 0.0:
            self._publish_rate_hz = 30.0
        self._profile_duration_s = (
            self.get_parameter("profile_duration_s").get_parameter_value().double_value
        )
        if self._profile_duration_s < 0.0:
            self._profile_duration_s = 5.0

        self._joint_commands_publisher = self.create_publisher(JointState, joint_topic, 10)
        self._callback_group = ReentrantCallbackGroup()
        self._action_server = ActionServer(
            self,
            ExecuteMotion,
            action_name,
            self.execute_callback,
            callback_group=self._callback_group,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
        )

        self.get_logger().info(
            f"Motion action server ready (action: {action_name}, topic: {joint_topic})"
        )

        xela_share = get_package_share_directory("xela_description")
        motion_path = os.path.join(xela_share, "joint_config.json")
        self.hand_pose = load_hand_pose(motion_path)
        urdf_path = os.path.join(xela_share, "hand.urdf")
        self._ctrlrange, self._joint_names = get_joint_limit_from_robot_description(
            urdf_path
        )

    def goal_callback(self, goal_request: ExecuteMotion.Goal) -> GoalResponse:
        motion_name = goal_request.motion_name.strip()
        if not motion_name:
            self.get_logger().warn("Rejected goal: empty motion_name")
            return GoalResponse.REJECT

        self.get_logger().info(f"Accepted motion goal: {motion_name!r}")
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle) -> CancelResponse:
        self.get_logger().info(f"Cancel requested for motion: {goal_handle.request.motion_name!r}")
        return CancelResponse.ACCEPT

    def _positions_to_joint_state(self, positions) -> JointState:
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = list(self._joint_names)
        msg.position = [float(v) for v in positions]
        return msg

    def _default_profile(self, pattern: str) -> GraspProfile:
        return GraspProfile(
            pattern=pattern,
            grip_fraction=0.8,
            thumb_grip_fraction=0.6,
            pregrip_fraction=0.15,
            thumb_delay=0.2,
            pulse_hz=1.0,
            pulse_amplitude=0.1,
            shear_amplitude=0.05,
            squeeze_steps=4,
        )

    @staticmethod
    def _override_float(value: float, default: float) -> float:
        return default if value < 0.0 else float(value)

    @staticmethod
    def _override_int(value: int, default: int) -> int:
        return default if value < 0 else int(value)

    def _profile_from_goal(self, goal: ExecuteMotion.Goal, pattern: str) -> GraspProfile:
        """Build a GraspProfile, using goal fields when >= 0, else server defaults."""
        defaults = self._default_profile(pattern)
        return GraspProfile(
            pattern=pattern,
            grip_fraction=self._override_float(goal.grip_fraction, defaults.grip_fraction),
            thumb_grip_fraction=self._override_float(
                goal.thumb_grip_fraction, defaults.thumb_grip_fraction
            ),
            pregrip_fraction=self._override_float(
                goal.pregrip_fraction, defaults.pregrip_fraction
            ),
            thumb_delay=self._override_float(goal.thumb_delay, defaults.thumb_delay),
            pulse_hz=self._override_float(goal.pulse_hz, defaults.pulse_hz),
            pulse_amplitude=self._override_float(
                goal.pulse_amplitude, defaults.pulse_amplitude
            ),
            shear_amplitude=self._override_float(
                goal.shear_amplitude, defaults.shear_amplitude
            ),
            squeeze_steps=self._override_int(goal.squeeze_steps, defaults.squeeze_steps),
        )

    def _play_poses(self, goal_handle, motion_name: str, poses, steps: int, period: float):
        feedback = ExecuteMotion.Feedback()
        result = ExecuteMotion.Result()
        denom = float(max(steps, 1))

        for i, pose in enumerate(poses):
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                result.success = False
                result.message = f"Motion {motion_name!r} canceled"
                return result

            self._joint_commands_publisher.publish(self._positions_to_joint_state(pose))
            feedback.progress = min(i / denom, 1.0)
            feedback.status = f"running {motion_name}"
            goal_handle.publish_feedback(feedback)
            time.sleep(period)

        return None

    def execute_callback(self, goal_handle):
        motion_name = goal_handle.request.motion_name.strip()

        feedback = ExecuteMotion.Feedback()
        result = ExecuteMotion.Result()
        period = 1.0 / self._publish_rate_hz

        feedback.progress = 0.0
        feedback.status = f"started {motion_name}"
        goal_handle.publish_feedback(feedback)


        self.get_logger().info(f"Going to intial open pose")
        self._joint_commands_publisher.publish(self._positions_to_joint_state(pregrip_targets(self._ctrlrange, 0)))
        time.sleep(5.0)

        self.get_logger().info(f"Executing motion: {motion_name!r}")
    

        

        if motion_name == "close":
            steps = 10
            canceled = self._play_poses(
                goal_handle,
                motion_name,
                close_hand(self.hand_pose, number_of_steps=steps),
                steps,
                period,
            )
            if canceled is not None:
                return canceled

        elif motion_name in PROFILE_MOTIONS:
            dt = period
            duration = self._override_float(
                goal_handle.request.duration_s, self._profile_duration_s
            )
            profile = self._profile_from_goal(goal_handle.request, motion_name)
            self.get_logger().info(
                "Profile "
                f"grip={profile.grip_fraction:.3f} "
                f"thumb_grip={profile.thumb_grip_fraction:.3f} "
                f"pregrip={profile.pregrip_fraction:.3f} "
                f"thumb_delay={profile.thumb_delay:.3f} "
                f"pulse_hz={profile.pulse_hz:.3f} "
                f"pulse_amp={profile.pulse_amplitude:.3f} "
                f"shear_amp={profile.shear_amplitude:.3f} "
                f"squeeze_steps={profile.squeeze_steps} "
                f"duration_s={duration:.3f}"
            )
            steps = int(duration / dt)
            canceled = self._play_poses(
                goal_handle,
                motion_name,
                motion_generator(
                    self._ctrlrange,
                    list(self._joint_names),
                    profile,
                    duration=duration,
                    dt=dt,
                ),
                steps,
                period,
            )
            if canceled is not None:
                return canceled

        else:
            self.get_logger().warn(
                f"Boilerplate server: no trajectory loaded for {motion_name!r}; completing immediately"
            )

        feedback.progress = 1.0
        feedback.status = f"completed {motion_name}"
        goal_handle.publish_feedback(feedback)

        result.success = True
        result.message = f"Motion {motion_name!r} completed"
        goal_handle.succeed()
        return result


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MotionActionServer()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
