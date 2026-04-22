import os
import sys

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import RegisterEventHandler, EmitEvent
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown


def generate_launch_description():
    leaphand_node = Node(
        package='leap_hand',
        executable='leaphand_node.py',
        name='leaphand_node',
        emulate_tty=True,
        output='screen',
        parameters=[
            {'kP': 500},
            {'kI': 0},
            {'kD': 300},
            {'curr_lim': 550}
        ]
    )
 
    position_node = Node(
        package='leap_hand',
        executable='position_node.py',
        name='position_node',
        emulate_tty=True,
        output='screen',
    )
 
    shutdown_when_position_exits = RegisterEventHandler(
        OnProcessExit(
            target_action=position_node,
            on_exit=[
                EmitEvent(
                    event=Shutdown(
                        reason='position_node completed trajectory replay'
                    )
                )
            ],
        )
    )
 
    return LaunchDescription([
        leaphand_node,
        position_node,
        shutdown_when_position_exits,
    ])

 