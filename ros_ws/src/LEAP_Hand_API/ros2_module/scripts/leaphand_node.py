#!/usr/bin/env python3

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from threading import RLock
import sys
import os

from leap_hand.srv import LeapPosition, LeapVelocity, LeapEffort, LeapState
from base import LeapXelaBase
from std_msgs.msg import Float64MultiArray

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from leap_globals import (
    COMMAND_QUEUE_DEPTH,
    COMMAND_TOPIC,
    LEAPHAND_STATE_PUBLISH_PERIOD_SEC,
    STATE_QUEUE_DEPTH,
    STATE_TOPIC,
)

class LeapXELANode(Node):
    def __init__(self):
        super().__init__('leaphand_node')

        # Guards all reads/writes to the hand hardware so they never overlap.
        self._hw_mutex = RLock()

        # Creates services that can give information about the hand out
        self.create_service(LeapPosition, 'leap_position', self.pos_srv)
        self.create_service(LeapVelocity, 'leap_velocity', self.vel_srv)
        self.create_service(LeapEffort, 'leap_effort', self.eff_srv)
        self.create_service(LeapState, 'leap_state', self.state_srv)

        self._leapXela = LeapXelaBase()
        self.create_subscription(
            JointState,
            COMMAND_TOPIC,
            self._receive_pose,
            COMMAND_QUEUE_DEPTH,
        )

        self.pub = self.create_publisher(Float64MultiArray, STATE_TOPIC, STATE_QUEUE_DEPTH)
        self.timer = self.create_timer(LEAPHAND_STATE_PUBLISH_PERIOD_SEC, self.publish_state)

    def publish_state(self):
        with self._hw_mutex:
            pos, vel, cur = self._leapXela.read_pos_vel_cur()

        msg = Float64MultiArray()
        msg.data = pos.tolist()
        self.pub.publish(msg)

    # Receive LEAP pose and directly control the robot
    def _receive_pose(self, msg):
        pose = msg.position
        self.curr_pos = np.array(pose)
        
        # with self._hw_mutex:
        self._leapXela.set_joints_degrees(self.curr_pos)

    # Service that reads and returns the pos of the robot in regular LEAP Embodiment scaling.
    def pos_srv(self, request, response):
        with self._hw_mutex:
            response.position = self._leapXela.read_pos().tolist()
        return response

    # Service that reads and returns the vel of the robot in LEAP Embodiment
    def vel_srv(self, request, response):
        with self._hw_mutex:
            response.velocity = self._leapXela.read_vel().tolist()
        return response

    # Service that reads and returns the effort/current of the robot in LEAP Embodiment
    def eff_srv(self, request, response):
        with self._hw_mutex:
            response.effort = self._leapXela.read_cur().tolist()
        return response

    def state_srv(self, request, response):
        with self._hw_mutex:
            pos, vel, cur = self._leapXela.read_pos_vel_cur()

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
