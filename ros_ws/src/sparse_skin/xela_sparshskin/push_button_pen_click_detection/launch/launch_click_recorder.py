from __future__ import annotations

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    def str_arg(name: str) -> ParameterValue:
        return ParameterValue(LaunchConfiguration(name), value_type=str)

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "device",
                default_value="08bb:2902",
                description="USB id (vid:pid), name substring or index of the microphone",
            ),
            DeclareLaunchArgument(
                "template_dir",
                default_value=os.path.expanduser("~/.ros/pen_click_templates"),
                description="Directory the cleaned click recordings are saved to",
            ),
            DeclareLaunchArgument(
                "output_device",
                default_value="",
                description="Name substring or index of the speaker/headphone output "
                "(empty = system default); also selectable in the window",
            ),
            Node(
                package="push_button_pen_click_detection",
                executable="click_recorder",
                name="click_recorder",
                output="screen",
                parameters=[
                    {"device": str_arg("device")},
                    {"template_dir": str_arg("template_dir")},
                    {"output_device": str_arg("output_device")},
                ],
            ),
        ]
    )
