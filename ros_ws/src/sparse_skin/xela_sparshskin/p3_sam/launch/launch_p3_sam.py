"""Launch the RealSense camera, P3-SAM, and the RViz viewer."""

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
    """Start the camera, the point-cloud segmenter, and RViz."""

    def str_arg(name: str) -> ParameterValue:
        return ParameterValue(LaunchConfiguration(name), value_type=str)

    def int_arg(name: str) -> ParameterValue:
        return ParameterValue(LaunchConfiguration(name), value_type=int)

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "cloud_topic",
                default_value="/camera/aligned_depth_to_color/color/points",
                description="RealSense point cloud to segment",
            ),
            DeclareLaunchArgument(
                "ckpt_path",
                default_value="",
                description="p3sam.safetensors; empty downloads from Hugging Face",
            ),
            DeclareLaunchArgument(
                "upstream_root",
                default_value="",
                description="Hunyuan3D-Part checkout; empty uses ~/.cache/p3_sam",
            ),
            DeclareLaunchArgument(
                "point_num", default_value="20000", description="Points kept from each cloud"
            ),
            DeclareLaunchArgument(
                "prompt_num", default_value="80", description="Point prompts"
            ),
            DeclareLaunchArgument(
                "prompt_bs", default_value="8", description="Prompt batch size"
            ),
            DeclareLaunchArgument("seed", default_value="42", description="Sampling seed"),
            DeclareLaunchArgument(
                "topic_prefix", default_value="/p3_sam", description="Topic prefix"
            ),
            DeclareLaunchArgument(
                "camera",
                default_value="true",
                description="Start the RealSense driver",
            ),
            DeclareLaunchArgument(
                "view",
                default_value="true",
                description="Open RViz on the part cloud",
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
                package="p3_sam",
                executable="p3_sam_node",
                name="p3_sam",
                output="screen",
                parameters=[
                    {
                        "cloud_topic": str_arg("cloud_topic"),
                        "ckpt_path": str_arg("ckpt_path"),
                        "upstream_root": str_arg("upstream_root"),
                        "point_num": int_arg("point_num"),
                        "prompt_num": int_arg("prompt_num"),
                        "prompt_bs": int_arg("prompt_bs"),
                        "seed": int_arg("seed"),
                        "topic_prefix": str_arg("topic_prefix"),
                    }
                ],
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                name="p3_sam_viewer",
                output="screen",
                arguments=[
                    "-d",
                    PathJoinSubstitution(
                        [FindPackageShare("p3_sam"), "rviz", "p3_sam.rviz"]
                    ),
                ],
                condition=IfCondition(LaunchConfiguration("view")),
            ),
        ]
    )
