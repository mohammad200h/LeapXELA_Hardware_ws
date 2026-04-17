import os
import sys

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from leap_globals import (
    PID_KP,
    PID_KI,
    PID_KD,
    CURRENT_LIMIT_MA,
)

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='leap_hand',
            executable='leaphand_node.py',
            name='leaphand_node',
            emulate_tty=True,
            output='screen',
            parameters=[
                {'kP': PID_KP},
                {'kI': PID_KI},
                {'kD': PID_KD},
                {'curr_lim': CURRENT_LIMIT_MA}
            ]
        ),
        Node(
            package='leap_hand',
            executable='position_node.py',
            name='position_node',
            emulate_tty=True,
            output='screen',
        )
    ])