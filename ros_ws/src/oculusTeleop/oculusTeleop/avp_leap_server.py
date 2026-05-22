#!/usr/bin/env python3
"""
Quest / AVP hand tracking -> PyBullet IK -> LEAP Hand joint angles.

Based on https://github.com/Improbable-AI/VisionProTeleop and
https://github.com/leap-hand/Bidex_VisionPro_Teleop

ROS 2 node publishes the 16-D LEAP joint vector after IK on a JointState topic
(default: cmd_xela, compatible with leaphand_node).
"""

from __future__ import annotations

import os
import time

import numpy as np
import pybullet as p
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

from oculusTeleop.client import QuestHeadsetStreamer

# 16-D LEAP Hand joint order (matches leaphand_node / LEAP Hand API).
LEAP_JOINT_NAMES = [
    "joint1",
    "joint2",
    "joint3",
    "joint4",
    "joint5",
    "joint6",
    "joint7",
    "joint8",
    "joint9",
    "joint10",
    "joint11",
    "joint12",
    "joint13",
    "joint14",
    "joint15",
    "joint16",
]


def _decode_pybullet_name(name):
    if isinstance(name, bytes):
        return name.decode("utf-8")
    return name


def get_name_off_ee(robot_id, ee_index):
    """Return the URDF link name for a PyBullet link index (IK end-effector index).

    PyBullet uses -1 for the base link and 0..getNumJoints()-1 for child links;
    link index i is the child link of joint i (see getJointInfo / getLinkState).
    """
    if ee_index == -1:
        return _decode_pybullet_name(p.getBodyInfo(robot_id)[1])
    num_joints = p.getNumJoints(robot_id)
    if ee_index < 0 or ee_index >= num_joints:
        raise ValueError(
            f"Invalid end-effector link index {ee_index} for body {robot_id} "
            f"(valid: -1 or 0..{num_joints - 1})"
        )
    return _decode_pybullet_name(p.getJointInfo(robot_id, ee_index)[12])


def get_ee_index_off_name(robot_id, link_name):
    """Return the PyBullet link index for a URDF link name."""
    if link_name == _decode_pybullet_name(p.getBodyInfo(robot_id)[1]):
        return -1
    for joint_index in range(p.getNumJoints(robot_id)):
        if _decode_pybullet_name(p.getJointInfo(robot_id, joint_index)[12]) == link_name:
            return joint_index
    raise ValueError(f"Link '{link_name}' not found on body {robot_id}")


class Leapv1PybulletIKPython:
    def __init__(
        self,
        *,
        is_left: bool = False,
        quest_ip: str | None = None,
        quest_port: int = 5006,
        use_gui: bool = True,
    ):
        self.vps = QuestHeadsetStreamer(quest_ip=quest_ip, port=quest_port)
        p.connect(p.GUI if use_gui else p.DIRECT)

        path_src = os.path.abspath(__file__)
        path_src = os.path.dirname(path_src)
        self.is_left = is_left
        self.glove_to_leap_mapping_scale = 1.6
        self.leapEndEffectorIndex = [3, 4, 8, 9, 13, 14, 18, 19]
        if self.is_left:
            path_src = os.path.join(path_src, "leap_hand_mesh_left/robot_pybullet.urdf")
            self.LeapId = p.loadURDF(
                path_src,
                [0.31, 0.01, 0.06],
                p.getQuaternionFromEuler([1.57, 0, 0]),
                useFixedBase=True,
            )
        else:
            path_src = os.path.join(path_src, "leap_hand_mesh_right/robot_pybullet.urdf")
            self.LeapId = p.loadURDF(
                path_src,
                [-0.22, 0.01, 0.03],
                p.getQuaternionFromEuler([1.57, 0, 3.14]),
                useFixedBase=True,
            )
            for ee_index in self.leapEndEffectorIndex:
                name = get_name_off_ee(self.LeapId, ee_index)
                print(f"EE {ee_index} name: {name}")

        self.numJoints = p.getNumJoints(self.LeapId)
        p.setGravity(0, 0, 0)
        p.setRealTimeSimulation(0)
        self.create_target_vis()

    def create_target_vis(self):
        small_ball_radius = 0.01
        ball_radius = 0.01
        ball_shape = p.createCollisionShape(p.GEOM_SPHERE, radius=ball_radius)
        baseMass = 0.001
        basePosition = [0.25, 0.25, 0]

        self.ballMbt = []
        for _ in range(4):
            self.ballMbt.append(
                p.createMultiBody(
                    baseMass=baseMass,
                    baseCollisionShapeIndex=ball_shape,
                    basePosition=basePosition,
                )
            )
            no_collision_group = 0
            no_collision_mask = 0
            p.setCollisionFilterGroupMask(
                self.ballMbt[-1], -1, no_collision_group, no_collision_mask
            )
        p.changeVisualShape(self.ballMbt[0], -1, rgbaColor=[1, 0, 0, 1])
        p.changeVisualShape(self.ballMbt[1], -1, rgbaColor=[0, 1, 0, 1])
        p.changeVisualShape(self.ballMbt[2], -1, rgbaColor=[0, 0, 1, 1])
        p.changeVisualShape(self.ballMbt[3], -1, rgbaColor=[1, 1, 1, 1])

    def update_target_vis(self, hand_pos):
        _, current_orientation = p.getBasePositionAndOrientation(self.ballMbt[0])
        p.resetBasePositionAndOrientation(self.ballMbt[0], hand_pos[3], current_orientation)
        _, current_orientation = p.getBasePositionAndOrientation(self.ballMbt[1])
        p.resetBasePositionAndOrientation(self.ballMbt[1], hand_pos[2], current_orientation)
        _, current_orientation = p.getBasePositionAndOrientation(self.ballMbt[2])
        p.resetBasePositionAndOrientation(self.ballMbt[2], hand_pos[7], current_orientation)
        _, current_orientation = p.getBasePositionAndOrientation(self.ballMbt[3])
        p.resetBasePositionAndOrientation(self.ballMbt[3], hand_pos[1], current_orientation)

    def get_glove_data(self, hand_pos):
        hand_pos[4][1] = hand_pos[4][1] + 0.002
        hand_pos[6][1] = hand_pos[6][1] + 0.002
        output = self.compute_IK(hand_pos)
        self.update_target_vis(hand_pos)
        return output

    def get_avp_data(self):
        r = self.vps.get_latest()
        if r is None:
            return None

        if self.is_left:
            hand_pose = np.asarray(r["left_fingers"]).astype(float)
        else:
            hand_pose = np.asarray(r["right_fingers"]).astype(float)
        indices = [3, 4, 8, 9, 13, 14, 18, 19, 23, 24]
        hand_pos = hand_pose[indices, :3, 3]
        for i in range(10):
            hand_pos[i][0] = hand_pos[i][0] * 1.35 * 1.5
            hand_pos[i][1] = hand_pos[i][1] * 1.5
            hand_pos[i][2] = hand_pos[i][2] * 1.5
        output = self.compute_IK(hand_pos)
        self.update_target_vis(hand_pos)
        return output

    def compute_IK(self, hand_pos):
        p.stepSimulation()

        rightHandIndex_middle_pos = hand_pos[2]
        rightHandIndex_pos = hand_pos[3]

        rightHandMiddle_middle_pos = hand_pos[4]
        rightHandMiddle_pos = hand_pos[5]

        rightHandRing_middle_pos = hand_pos[6]
        rightHandRing_pos = hand_pos[7]

        rightHandThumb_middle_pos = hand_pos[0]
        rightHandThumb_pos = hand_pos[1]

        leapEndEffectorPos = [
            rightHandIndex_middle_pos,
            rightHandIndex_pos,
            rightHandMiddle_middle_pos,
            rightHandMiddle_pos,
            rightHandRing_middle_pos,
            rightHandRing_pos,
            rightHandThumb_middle_pos,
            rightHandThumb_pos,
        ]

        jointPoses = p.calculateInverseKinematics2(
            self.LeapId,
            self.leapEndEffectorIndex,
            leapEndEffectorPos,
            solver=p.IK_DLS,
            maxNumIterations=50,
            residualThreshold=0.0001,
        )

        combined_jointPoses = (
            jointPoses[0:4]
            + (0.0,)
            + jointPoses[4:8]
            + (0.0,)
            + jointPoses[8:12]
            + (0.0,)
            + jointPoses[12:16]
            + (0.0,)
        )
        combined_jointPoses = list(combined_jointPoses)

        for i in range(20):
            p.setJointMotorControl2(
                bodyIndex=self.LeapId,
                jointIndex=i,
                controlMode=p.POSITION_CONTROL,
                targetPosition=combined_jointPoses[i],
                targetVelocity=0,
                force=500,
                positionGain=0.3,
                velocityGain=1,
            )

        real_robot_hand_q = np.array([float(0.0) for _ in range(16)])
        real_robot_hand_q[0:4] = jointPoses[0:4]
        real_robot_hand_q[4:8] = jointPoses[4:8]
        real_robot_hand_q[8:12] = jointPoses[8:12]
        real_robot_hand_q[12:16] = jointPoses[12:16]
        real_robot_hand_q[0:2] = real_robot_hand_q[0:2][::-1]
        real_robot_hand_q[4:6] = real_robot_hand_q[4:6][::-1]
        real_robot_hand_q[8:10] = real_robot_hand_q[8:10][::-1]
        return [float(i) for i in real_robot_hand_q]

    def close(self) -> None:
        self.vps.close()


class AvpLeapServerNode(Node):
    def __init__(self) -> None:
        super().__init__("avp_leap_server")

        self.declare_parameter("quest_ip", "192.168.2.48")
        self.declare_parameter("quest_port", 5006)
        self.declare_parameter("is_left", False)
        self.declare_parameter("use_gui", True)
        self.declare_parameter("publish_rate_hz", 30.0)
        self.declare_parameter("joint_topic", "cmd_xela")
        self.declare_parameter("wait_for_tracking_sec", 30.0)

        quest_ip = self.get_parameter("quest_ip").get_parameter_value().string_value
        if not quest_ip.strip():
            quest_ip = None
        quest_port = int(self.get_parameter("quest_port").value)
        is_left = bool(self.get_parameter("is_left").value)
        use_gui = bool(self.get_parameter("use_gui").value)
        rate_hz = float(self.get_parameter("publish_rate_hz").value)
        joint_topic = str(self.get_parameter("joint_topic").value)
        wait_sec = float(self.get_parameter("wait_for_tracking_sec").value)

        self.get_logger().info(
            f"Starting AVP/Quest IK teleop (hand={'left' if is_left else 'right'}, "
            f"quest_ip={quest_ip!r}, gui={use_gui})"
        )
        self._ik = Leapv1PybulletIKPython(
            is_left=is_left,
            quest_ip=quest_ip,
            quest_port=quest_port,
            use_gui=use_gui,
        )

        if wait_sec > 0.0:
            self.get_logger().info(f"Waiting up to {wait_sec}s for first tracking packet...")
            deadline = time.time() + wait_sec
            while time.time() < deadline:
                if self._ik.vps.latest is not None:
                    self.get_logger().info("Tracking stream active.")
                    break
                time.sleep(0.05)
            else:
                self.get_logger().warn(
                    "No tracking received yet; node will publish once packets arrive."
                )

        self._joint_pub = self.create_publisher(JointState, joint_topic, 10)
        self._joint_msg = JointState()
        self._joint_msg.name = list(LEAP_JOINT_NAMES)

        period = 1.0 / max(rate_hz, 1.0)
        self._timer = self.create_timer(period, self._on_timer)

        self.get_logger().info(
            f"Publishing {len(LEAP_JOINT_NAMES)}-D LEAP joints on '{joint_topic}' at {rate_hz:.1f} Hz."
        )

    def _on_timer(self) -> None:
        joints = self._ik.get_avp_data()
        if joints is None:
            return

        self._joint_msg.header.stamp = self.get_clock().now().to_msg()
        self._joint_msg.position = [float(x) for x in joints]
        self._joint_pub.publish(self._joint_msg)

    def destroy_node(self) -> None:
        if hasattr(self, "_ik"):
            self._ik.close()
        super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = AvpLeapServerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
