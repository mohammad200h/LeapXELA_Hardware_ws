"""Launch the RealSense driver and the SAM 3 pen bounding-box node."""

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
    """Start the camera (optional) and the bounding-box node."""

    def float_arg(name: str) -> ParameterValue:
        return ParameterValue(LaunchConfiguration(name), value_type=float)

    def str_arg(name: str) -> ParameterValue:
        return ParameterValue(LaunchConfiguration(name), value_type=str)

    def bool_arg(name: str) -> ParameterValue:
        return ParameterValue(LaunchConfiguration(name), value_type=bool)

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "image_topic",
                default_value="/camera/color/image_raw",
                description="RealSense color image topic",
            ),
            DeclareLaunchArgument(
                "depth_topic",
                default_value="/camera/aligned_depth_to_color/image_raw",
                description="Aligned depth image topic",
            ),
            DeclareLaunchArgument(
                "prompt",
                default_value="pen",
                description="SAM 3 text prompt",
            ),
            DeclareLaunchArgument(
                "rate_hz",
                default_value="3.0",
                description="How many frames per second are run through SAM 3",
            ),
            DeclareLaunchArgument(
                "conf",
                default_value="0.25",
                description="SAM 3 confidence threshold",
            ),
            DeclareLaunchArgument(
                "model",
                default_value="sam3.pt",
                description="Path to sam3.pt (Hugging Face gated weights)",
            ),
            DeclareLaunchArgument(
                "device",
                default_value="",
                description="Torch device (empty lets Ultralytics pick cuda/cpu)",
            ),
            DeclareLaunchArgument(
                "use_depth",
                default_value="true",
                description="Refine the SAM mask with aligned depth",
            ),
            DeclareLaunchArgument(
                "publish_mask",
                default_value="true",
                description="Publish the best instance mask",
            ),
            DeclareLaunchArgument(
                "min_depth",
                default_value="0.15",
                description="Minimum valid depth in metres",
            ),
            DeclareLaunchArgument(
                "max_depth",
                default_value="1.5",
                description="Maximum valid depth in metres",
            ),
            DeclareLaunchArgument(
                "camera",
                default_value="true",
                description="Start the RealSense driver (set false when playing a bag)",
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
                package="bounding_box",
                executable="bounding_box_node",
                name="bounding_box",
                output="screen",
                parameters=[
                    {"image_topic": str_arg("image_topic")},
                    {"depth_topic": str_arg("depth_topic")},
                    {"prompt": str_arg("prompt")},
                    {"rate_hz": float_arg("rate_hz")},
                    {"conf": float_arg("conf")},
                    {"model": str_arg("model")},
                    {"device": str_arg("device")},
                    {"use_depth": bool_arg("use_depth")},
                    {"publish_mask": bool_arg("publish_mask")},
                    {"min_depth": float_arg("min_depth")},
                    {"max_depth": float_arg("max_depth")},
                ],
            ),
        ]
    )
