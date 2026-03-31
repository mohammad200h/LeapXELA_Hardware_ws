#!/usr/bin/env python3

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String

from leap_hand_utils.dynamixel_client import DynamixelClient
import leap_hand_utils.leap_hand_utils as lhu
from leap_hand.srv import LeapPosition, LeapVelocity, LeapEffort
from base import LeapXelaBase



class LeapXELANode(Node):
    def __init__(self):
        super().__init__('leaphand_node')
        
        # Creates services that can give information about the hand out
        self.create_service(LeapPosition, 'leap_position', self.pos_srv)
        self.create_service(LeapVelocity, 'leap_velocity', self.vel_srv)
        self.create_service(LeapEffort, 'leap_effort', self.eff_srv)

        self._leapXela = LeapXelaBase()
        self.create_subscription(JointState, 'cmd_xela', self._receive_pose, 10)

        


    # Receive LEAP pose and directly control the robot
    def _receive_pose(self, msg):
        pose = msg.position
        self.curr_pos = np.array(pose)
        
        self._leapXela.set_joints_degrees(self.curr_pos)

    # Service that reads and returns the pos of the robot in regular LEAP Embodiment scaling.
    def pos_srv(self, request, response):
        response.position = self._leapXela.dxl_client.read_pos().tolist()
        return response

    # Service that reads and returns the vel of the robot in LEAP Embodiment
    def vel_srv(self, request, response):
        response.velocity = self._leapXela.dxl_client.read_vel().tolist()
        return response

    # Service that reads and returns the effort/current of the robot in LEAP Embodiment
    def eff_srv(self, request, response):
        response.effort = self._leapXela.dxl_client.read_cur().tolist()
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
