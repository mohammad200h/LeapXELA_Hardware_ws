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
                "use_gui",
                default_value="true",
                description="Use PyBullet GUI",
            ),
            DeclareLaunchArgument(
                "hardware_topic",
                default_value="leap_state",
                description="Hardware JointState topic (convert_hardware_to_sim subscribes)",
            ),
            DeclareLaunchArgument(
                "sim_topic",
                default_value="leap_state_sim",
                description="Sim JointState topic (convert_hardware_to_sim publishes)",
            ),
            Node(
                package="conversions",
                executable="convert_hardware_to_sim",
                name="convert_hardware_to_sim",
                output="screen",
                parameters=[
                    {"hardware_topic": LaunchConfiguration("hardware_topic")},
                    {"sim_topic": LaunchConfiguration("sim_topic")},
                ],
            ),
            Node(
                package="conversions",
                executable="sim_joint_viewer",
                name="sim_joint_viewer",
                output="screen",
                parameters=[
                    {
                        "urdf_path": LaunchConfiguration("urdf_path"),
                        "use_gui": ParameterValue(
                            LaunchConfiguration("use_gui"), value_type=bool
                        ),
                        "sim_topic": LaunchConfiguration("sim_topic"),
                    }
                ],
            ),
        ]
    )
