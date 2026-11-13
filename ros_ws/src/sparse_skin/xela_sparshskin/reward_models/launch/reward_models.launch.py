"""The reward models' training action servers and inference services."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    nodes = [
        "rank2reward_train",
        "coupled_local_global_train",
        "rank2reward_inference",
        "coupled_local_global_inference",
    ]
    return LaunchDescription([
        Node(package="reward_models", executable=name, name=name, output="screen")
        for name in nodes
    ])
