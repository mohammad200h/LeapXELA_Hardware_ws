from __future__ import annotations

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

EVENTS_TOPIC = "/jev_omni_events"
CROP_TOPIC = "/jev_omni_crop"


def generate_launch_description() -> LaunchDescription:
    def arg(name: str, value_type: type) -> ParameterValue:
        return ParameterValue(LaunchConfiguration(name), value_type=value_type)

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "num_frames",
                default_value="8",
                description="Frames per clip given to Jev-Omni (1 to 16)",
            ),
            DeclareLaunchArgument(
                "frame_rate_hz",
                default_value="4.0",
                description="Rate frames are sampled into the clip (length = num_frames / rate)",
            ),
            DeclareLaunchArgument(
                "rate_hz",
                default_value="1.0",
                description="Maximum rate clips are evaluated (slower if inference takes longer)",
            ),
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
                "device_map",
                default_value="auto",
                description="Transformers device_map: auto splits the model across all GPUs",
            ),
            DeclareLaunchArgument(
                "image_topic",
                default_value="/camera/color/image_raw",
                description="Camera image topic",
            ),
            DeclareLaunchArgument(
                "events_file",
                default_value="",
                description="Events JSON file (defaults to the installed events.json)",
            ),
            DeclareLaunchArgument(
                "viewer",
                default_value="true",
                description="Open the Jev_Viewer window",
            ),
            Node(
                package="jev_event_detector",
                executable="jev_omni_event_detector",
                name="jev_omni_event_detector",
                output="screen",
                parameters=[
                    {"num_frames": arg("num_frames", int)},
                    {"frame_rate_hz": arg("frame_rate_hz", float)},
                    {"rate_hz": arg("rate_hz", float)},
                    {"zoom": arg("zoom", float)},
                    {"center_x": arg("center_x", float)},
                    {"center_y": arg("center_y", float)},
                    {"threshold": arg("threshold", float)},
                    {"device_map": arg("device_map", str)},
                    {"image_topic": arg("image_topic", str)},
                    {"events_file": arg("events_file", str)},
                    {"events_topic": EVENTS_TOPIC},
                    {"crop_topic": CROP_TOPIC},
                ],
            ),
            Node(
                package="jev_event_detector",
                executable="jev_viewer",
                name="Jev_Viewer",
                output="screen",
                parameters=[{"events_topic": EVENTS_TOPIC}, {"crop_topic": CROP_TOPIC}],
                condition=IfCondition(LaunchConfiguration("viewer")),
            ),
        ]
    )
