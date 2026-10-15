from __future__ import annotations

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    def float_arg(name: str) -> ParameterValue:
        return ParameterValue(LaunchConfiguration(name), value_type=float)

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
                description="Directory of click templates saved by click_recorder",
            ),
            DeclareLaunchArgument(
                "threshold",
                default_value="0.7",
                description="Template similarity at or above which a click is detected",
            ),
            DeclareLaunchArgument(
                "energy_gate",
                default_value="3.0",
                description="Audio must be this many times above the noise floor to be matched",
            ),
            DeclareLaunchArgument(
                "hold_s",
                default_value="0.15",
                description="Seconds the output stays 1 after the last match",
            ),
            DeclareLaunchArgument(
                "rate_hz",
                default_value="100.0",
                description="How many times per second the output is published",
            ),
            DeclareLaunchArgument(
                "audio_topic",
                default_value="/audio",
                description="Topic audio_publisher streams the mic on (it holds the mic; the "
                "click detector and other nodes listen to the topic)",
            ),
            DeclareLaunchArgument(
                "output_topic",
                default_value="/pen_click",
                description="Int32 topic: 1 while a click is heard, 0 otherwise",
            ),
            Node(
                package="push_button_pen_click_detection",
                executable="audio_publisher",
                name="audio_publisher",
                output="screen",
                parameters=[
                    {"device": str_arg("device")},
                    {"topic": str_arg("audio_topic")},
                ],
            ),
            Node(
                package="push_button_pen_click_detection",
                executable="click_detector",
                name="click_detector",
                output="screen",
                parameters=[
                    {"device": str_arg("device")},
                    {"template_dir": str_arg("template_dir")},
                    {"threshold": float_arg("threshold")},
                    {"energy_gate": float_arg("energy_gate")},
                    {"hold_s": float_arg("hold_s")},
                    {"rate_hz": float_arg("rate_hz")},
                    {"output_topic": str_arg("output_topic")},
                    {"audio_topic": str_arg("audio_topic")},
                ],
            ),
        ]
    )
