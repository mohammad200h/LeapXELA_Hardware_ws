from __future__ import annotations

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    def float_arg(name: str) -> ParameterValue:
        return ParameterValue(LaunchConfiguration(name), value_type=float)

    def int_arg(name: str) -> ParameterValue:
        return ParameterValue(LaunchConfiguration(name), value_type=int)

    def str_arg(name: str) -> ParameterValue:
        return ParameterValue(LaunchConfiguration(name), value_type=str)

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "image_topic",
                default_value="/camera/color/image_raw",
                description="Camera image topic",
            ),
            DeclareLaunchArgument(
                "crop_file",
                default_value="",
                description="Crop tasks JSON file (defaults to the installed crop.json)",
            ),
            DeclareLaunchArgument(
                "model_path",
                default_value="Qwen/Qwen2.5-VL-3B-Instruct",
                description="Qwen2.5-VL grounding model (3B or 7B Instruct, or a local path)",
            ),
            DeclareLaunchArgument(
                "max_pixels",
                default_value="1003520",
                description="Pixel budget the image is resized to before Qwen sees it",
            ),
            DeclareLaunchArgument(
                "expand",
                default_value="true",
                description="Grow small boxes by CropVLM's area-percentile factors",
            ),
            DeclareLaunchArgument(
                "rate_hz",
                default_value="1.0",
                description="How many frames per second are run through the model",
            ),
            DeclareLaunchArgument(
                "device",
                default_value="",
                description="Torch device (empty picks cuda if available, else cpu)",
            ),
            DeclareLaunchArgument(
                "camera",
                default_value="true",
                description="Start the RealSense driver (set false when playing a bag)",
            ),
            DeclareLaunchArgument(
                "viewer",
                default_value="true",
                description="Open the CropVLM_Viewer window",
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("realsense_ros2_camera"), "launch", "rs.launch.py"]
                    )
                ),
                condition=IfCondition(LaunchConfiguration("camera")),
            ),
            Node(
                package="jev_event_detector",
                executable="crop_vlm",
                name="crop_vlm",
                output="screen",
                parameters=[
                    {"image_topic": str_arg("image_topic")},
                    {"crop_file": str_arg("crop_file")},
                    {"model_path": str_arg("model_path")},
                    {"max_pixels": int_arg("max_pixels")},
                    {"expand": ParameterValue(LaunchConfiguration("expand"), value_type=bool)},
                    {"rate_hz": float_arg("rate_hz")},
                    {"device": str_arg("device")},
                ],
            ),
            Node(
                package="jev_event_detector",
                executable="crop_vlm_viewer",
                name="CropVLM_Viewer",
                output="screen",
                parameters=[{"image_topic": str_arg("image_topic")}],
                condition=IfCondition(LaunchConfiguration("viewer")),
            ),
        ]
    )
