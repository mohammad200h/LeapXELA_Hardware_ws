from __future__ import annotations

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
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
                "zoom",
                default_value="2.0",
                description="Crop zoom: 1.0 is the full frame, 2.0 keeps half the width/height",
            ),
            DeclareLaunchArgument(
                "center_x",
                default_value="0.40",
                description="Horizontal centre of the crop, as a fraction of the frame width",
            ),
            DeclareLaunchArgument(
                "center_y",
                default_value="0.80",
                description="Vertical centre of the crop, as a fraction of the frame height",
            ),
            DeclareLaunchArgument(
                "threshold",
                default_value="0.5",
                description="Probability at or above which an event is marked fired",
            ),
            DeclareLaunchArgument(
                "rate_hz",
                default_value="5.0",
                description="How many frames per second are run through the model",
            ),
            DeclareLaunchArgument(
                "image_topic",
                default_value="/camera/color/image_raw",
                description="Camera image topic",
            ),
            DeclareLaunchArgument(
                "viewer",
                default_value="true",
                description="Open the Jev_Viewer window",
            ),
            DeclareLaunchArgument(
                "events_file",
                default_value="",
                description="Events JSON file (defaults to the installed events.json)",
            ),
            Node(
                package="jev_event_detector",
                executable="jev_laya_vision_detector",
                name="jev_laya_vision_detector",
                output="screen",
                parameters=[
                    {"zoom": float_arg("zoom")},
                    {"center_x": float_arg("center_x")},
                    {"center_y": float_arg("center_y")},
                    {"threshold": float_arg("threshold")},
                    {"rate_hz": float_arg("rate_hz")},
                    {"image_topic": str_arg("image_topic")},
                    {"events_file": str_arg("events_file")},
                ],
            ),
            Node(
                package="jev_event_detector",
                executable="jev_viewer",
                name="Jev_Viewer",
                output="screen",
                condition=IfCondition(LaunchConfiguration("viewer")),
            ),
        ]
    )
