import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import numpy as np
import csv
import time
import os

class PositionNode(Node):
    def __init__(self):
        super().__init__('position_node')
        self.pub = self.create_publisher(JointState, 'cmd_xela', 10)
        self.joint_positions = self.load_csv(os.path.join(os.path.dirname(__file__), 'leap_state_output.csv'))
        self.sample_and_publish()

    def load_csv(self, path):
        with open(path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            data = [np.array([float(x) for x in row]) for row in reader]
        return data

    def sample_and_publish(self):
        sampled = self.joint_positions[::20]
        for i in range(len(sampled) - 1):
            start = sampled[i]
            end = sampled[i + 1]
            # Interpolate 5 equidistant poses (including start, excluding end)
            for j in range(1, 6):
                alpha = j / 6.0  # 1/6, 2/6, ..., 5/6
                interp = start + (end - start) * alpha
                msg = JointState()
                msg.position = interp.tolist()
                self.pub.publish(msg)
                time.sleep(0.1)  # Adjust as needed

def main(args=None):
    rclpy.init(args=args)
    position_node = PositionNode()
    rclpy.spin(position_node)
    position_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()