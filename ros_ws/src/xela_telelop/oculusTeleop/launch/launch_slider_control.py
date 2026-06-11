from __future__ import annotations

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "urdf_path",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("xela_description"), "hand.urdf"]
                ),
                description="URDF path (default: xela_description/hand.urdf)",
            ),
            DeclareLaunchArgument(
                "joint_config_path",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("xela_description"), "joint_config.json"]
                ),
                description="Joint config JSON path (default: xela_description/joint_config.json)",
            ),
            DeclareLaunchArgument(
                "use_gui",
                default_value="true",
                description="Use PyBullet GUI",
            ),
            DeclareLaunchArgument(
                "joint_topic",
                default_value="oculus_teleop_joint_commands",
                description="JointState topic for slider joint commands",
            ),
            DeclareLaunchArgument(
                "publish_rate_hz",
                default_value="30.0",
                description="JointState publish rate (Hz)",
            ),
            DeclareLaunchArgument(
                "hardware_topic",
                default_value="cmd_xela",
                description="Hardware topic (convert_sim_to_hardware publishes)",
            ),
            Node(
                package="oculusTeleop",
                executable="slider_control",
                name="slider_control",
                output="screen",
                parameters=[
                    {
                        "urdf_path": LaunchConfiguration("urdf_path"),
                        "joint_config_path": LaunchConfiguration("joint_config_path"),
                        "use_gui": ParameterValue(
                            LaunchConfiguration("use_gui"), value_type=bool
                        ),
                        "joint_topic": LaunchConfiguration("joint_topic"),
                        "publish_rate_hz": ParameterValue(
                            LaunchConfiguration("publish_rate_hz"), value_type=float
                        ),
                    }
                ],
            ),
            Node(
                package="oculusTeleop",
                executable="convert_sim_to_hardware",
                name="convert_sim_to_hardware",
                output="screen",
                parameters=[
                    {"teleop_topic": LaunchConfiguration("joint_topic")},
                    {"hardware_topic": LaunchConfiguration("hardware_topic")},
                ],
            ),
        ]
    )
