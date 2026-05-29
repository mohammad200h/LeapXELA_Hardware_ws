#!/usr/bin/env python3

import json
import os
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from threading import RLock
from typing import Any

from ament_index_python.packages import get_package_share_directory

from leap_hand_utils.dynamixel_client import DynamixelClient
import leap_hand_utils.leap_hand_utils as lhu
from leap_hand.srv import LeapPosition, LeapVelocity, LeapEffort, LeapState
from base import LeapXelaBase


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

def get_joint_names(joint_config: dict[str, Any]) -> list[str]:
    map = joint_config["leapXela"]["hardware"]["map"]
    joint_names = []
    idx = []

    for finger in ["th", "if", "mf", "rf"]:
        for key, value in map[finger].items():
            idx.append(int(key))
            joint_names.append(f"{finger}_{value}")

    print(f"get_joint_names:: joint_names: {joint_names} \n idx: {idx}")
    print(f"get_joint_names:: joint_names::len:: {len(joint_names)} \n idx::len {len(idx)}")
    return joint_names, idx





def clamp_the_joint_commands(joint_commands):
    # TODO implement this function
    pass

class LeapXELANode(Node):
    def __init__(self):
        super().__init__('leaphand_node')

        joint_config = load_joint_config()
        self.joint_names, self.idx = get_joint_names(joint_config)

        # Guards all reads/writes to the hand hardware so they never overlap.
        self._hw_mutex = RLock()

        # Creates services that can give information about the hand out
        self.create_service(LeapPosition, 'leap_position', self.pos_srv)
        self.create_service(LeapVelocity, 'leap_velocity', self.vel_srv)
        self.create_service(LeapEffort, 'leap_effort', self.eff_srv)
        self.create_service(LeapState, 'leap_state', self.state_srv)

        self._leapXela = LeapXelaBase()
        self.create_subscription(JointState, 'cmd_xela', self._receive_pose, 10)

        self.pub = self.create_publisher(JointState, 'leap_state', 10)
        self.timer = self.create_timer(0.1, self.publish_state)

    def publish_state(self):
        with self._hw_mutex:
            pos, vel, cur = self._leapXela.dxl_client.read_pos_vel_cur()
            msg = JointState()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.name = self.joint_names
            msg.position = pos.tolist()
            msg.velocity = vel.tolist()
            msg.effort = cur.tolist()
            self.pub.publish(msg)

    # Receive LEAP pose and directly control the robot
    def _receive_pose(self, msg):
        pose = msg.position
       
        self.curr_pos = np.array(pose)
        
        with self._hw_mutex:
            # self._leapXela.set_joints_degrees(self.curr_pos)
            self._leapXela.set_joints_radians(self.curr_pos)

    # Service that reads and returns the pos of the robot in regular LEAP Embodiment scaling.
    def pos_srv(self, request, response):
        with self._hw_mutex:
            response.position = self._leapXela.dxl_client.read_pos().tolist()
        return response

    # Service that reads and returns the vel of the robot in LEAP Embodiment
    def vel_srv(self, request, response):
        with self._hw_mutex:
            response.velocity = self._leapXela.dxl_client.read_vel().tolist()
        return response

    # Service that reads and returns the effort/current of the robot in LEAP Embodiment
    def eff_srv(self, request, response):
        with self._hw_mutex:
            response.effort = self._leapXela.dxl_client.read_cur().tolist()
        return response

    def state_srv(self, request, response):
        with self._hw_mutex:
            pos, vel, cur = self._leapXela.dxl_client.read_pos_vel_cur()

        response.position = pos.tolist()
        response.velocity = vel.tolist()
        response.effort = cur.tolist()
        return response


    def safe_disconnect(self):
        self._leapXela.safe_disconnect()

    def destroy_node(self):
        self.safe_disconnect()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    leaphand_node = LeapXELANode()
    try:
        rclpy.spin(leaphand_node)
    finally:
        leaphand_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
