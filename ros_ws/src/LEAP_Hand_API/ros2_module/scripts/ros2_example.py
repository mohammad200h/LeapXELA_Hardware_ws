#!/usr/bin/env python3

import sys
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from leap_hand.srv import LeapPosition
import time
import numpy as np
import leap_hand_utils.leap_hand_utils as lhu

class MinimalClientAsync(Node):

    def __init__(self):
        super().__init__('minimal_client_async')
        self.cli = self.create_client(LeapPosition, '/leap_position')
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not available, waiting again...')
        self.req = LeapPosition.Request()
        self.pub_hand = self.create_publisher(JointState, '/cmd_xela', 10) 
        
    def send_request(self):
        self.future = self.cli.call_async(self.req)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()

def main(args=None):
    rclpy.init(args=args)
    minimal_client = MinimalClientAsync()
    initial_joint_degrees = [
        180,  # : 
        180,  
        180,  # Thumb: th_mcp_active
        90,  # Thumb: th_ipl_act
        265,
        180,
        180,
        180,  # Middle finger
        265,
        180,
        180,
        180,  # Ring finger
        265,
        180,
        180,
        180,  # Thumb (indices 12..15)
    ]
    while True:
        
        # JointState fields require a Python sequence of Python floats (numpy scalars fail ROS type checks).
        stater.position = [float(x) for x in initial_joint_degrees]
        #minimal_client.pub_hand.publish(stater)  # Choose the right embodiment here
        minimal_client.pub_hand.publish(stater)
    minimal_client.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()