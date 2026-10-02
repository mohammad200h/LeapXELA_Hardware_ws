from __future__ import annotations

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch_xml.launch_description_sources import XMLLaunchDescriptionSource


def generate_launch_description() -> LaunchDescription:
    hardware_topic = LaunchConfiguration("hardware_topic")
    sim_topic = LaunchConfiguration("sim_topic")
    teleop_topic = LaunchConfiguration("teleop_topic")
    taxel_frames_topic = LaunchConfiguration("taxel_frames_topic")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "fk_viewer",
                default_value="false",
                description="Launch the Open3D taxel FK viewer",
            ),
            DeclareLaunchArgument(
                "hardware_topic",
                default_value="leap_state",
                description="Hardware JointState topic published by leaphand_node",
            ),
            DeclareLaunchArgument(
                "sim_topic",
                default_value="leap_state_sim",
                description="Sim-frame JointState topic (convert_hardware_to_sim output, fk_taxels input)",
            ),
            DeclareLaunchArgument(
                "teleop_topic",
                default_value="oculus_teleop_joint_commands",
                description="Sim-frame joint commands consumed by convert_sim_to_hardware",
            ),
            DeclareLaunchArgument(
                "taxel_frames_topic",
                default_value="taxel_frames",
                description="TaxelFrames topic published by fk_taxels",
            ),
            DeclareLaunchArgument(
                "xela_config",
                default_value="/etc/xela/xServ.ini",
                description="xela_server config file",
            ),
            DeclareLaunchArgument(
                "xela_port",
                default_value="5000",
                description="xela_server port",
            ),
            DeclareLaunchArgument(
                "xela_ip",
                default_value="127.0.0.1",
                description="xela_server IP",
            ),
            IncludeLaunchDescription(
                XMLLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("xela_server_ros2"), "service.launch"]
                    )
                ),
                launch_arguments={
                    "file": LaunchConfiguration("xela_config"),
                    "port": LaunchConfiguration("xela_port"),
                    "ip": LaunchConfiguration("xela_ip"),
                }.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("leap_hand"), "launch", "launch_leap.py"]
                    )
                )
            ),
            Node(
                package="conversions",
                executable="convert_hardware_to_sim",
                name="convert_hardware_to_sim",
                output="screen",
                parameters=[
                    {"hardware_topic": hardware_topic},
                    {"sim_topic": sim_topic},
                ],
            ),
            Node(
                package="conversions",
                executable="convert_sim_to_hardware",
                name="convert_sim_to_hardware",
                output="screen",
                parameters=[
                    {"teleop_topic": teleop_topic},
                    # leaphand_node subscribes to this fixed topic.
                    {"hardware_topic": "cmd_xela"},
                ],
            ),
            Node(
                package="leapXela_taxels_forewardkinematic",
                executable="fk_taxels",
                name="fk_taxels",
                output="screen",
                parameters=[
                    {"joint_topic": sim_topic},
                    {"taxel_frames_topic": taxel_frames_topic},
                ],
            ),
            Node(
                package="leapXela_taxels_forewardkinematic",
                executable="fk_taxels_viewer",
                name="fk_taxels_viewer",
                output="screen",
                parameters=[{"taxel_frames_topic": taxel_frames_topic}],
                condition=IfCondition(LaunchConfiguration("fk_viewer")),
            ),
            Node(
                package="mechanical_pen_data_collection",
                executable="sparsh_skin_data_processor",
                name="sparsh_skin_data_processor",
                output="screen",
                parameters=[
                    {"taxel_fk_topic": taxel_frames_topic},
                    {"xela_topic": "xServTopic"},
                ],
            ),
        ]
    )
