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
        self.pub_hand = self.create_publisher(JointState, '/cmd_ones', 10) 
        self.pub_xela = self.create_publisher(JointState, '/cmd_xela', 10)

    def send_request(self):
        self.future = self.cli.call_async(self.req)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()

def main(args=None):
    rclpy.init(args=args)
    minimal_client = MinimalClientAsync()
    x = list(np.zeros(16))
    y = 0.025
    while True:
        response = minimal_client.send_request()
        print(f"response: {response}")  ##Receive

        pose = lhu.LEAPhand_to_LEAPsim(response.position)
        print(f"pose: {pose}")

        time.sleep(0.05)
        stater = JointState()
        x[0] = x[0] + y
        if x[0] > 0.1:
            y = - 0.025
        if x[0] < -1:
            y = 0.025
        stater.position = [0.0] * 16  ## You can set the position this way  
        #minimal_client.pub_hand.publish(stater)  # Choose the right embodiment here
        minimal_client.pub_xela.publish(stater)
    minimal_client.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()