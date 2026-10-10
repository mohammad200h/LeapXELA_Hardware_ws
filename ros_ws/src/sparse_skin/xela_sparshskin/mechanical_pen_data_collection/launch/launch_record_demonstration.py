from __future__ import annotations

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare
from launch_xml.launch_description_sources import XMLLaunchDescriptionSource


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "joint_topic",
                default_value="leap_state",
                description="Hardware JointState topic published by leaphand_node",
            ),
            DeclareLaunchArgument(
                "sim_topic",
                default_value="leap_state_sim",
                description="Sim-frame JointState topic published by convert_hardware_to_sim",
            ),
            DeclareLaunchArgument(
                "cmd_topic",
                default_value="cmd_xela",
                description="JointState command topic of leaphand_node, used by Play",
            ),
            DeclareLaunchArgument(
                "image_topic",
                default_value="/camera/color/image_raw",
                description="Camera Image topic recorded with each take (empty disables the camera)",
            ),
            DeclareLaunchArgument(
                "camera",
                default_value="true",
                description="Start the RealSense camera (realsense_ros2_camera rs.launch.py)",
            ),
            DeclareLaunchArgument(
                "demo_dir",
                default_value="",
                description="Directory demonstrations are saved into "
                "(defaults to ros_ws/demonstrations)",
            ),
            DeclareLaunchArgument(
                "compliant",
                default_value="true",
                description="Low-gain LEAP hand so the fingers can be moved by hand",
            ),
            DeclareLaunchArgument(
                "xela",
                default_value="true",
                description="Start xela_server / xela_service (xela_server_ros2 service.launch)",
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
            DeclareLaunchArgument(
                "xela_topic",
                default_value="/xServTopic",
                description="SensStream topic of xela_service shown on the FK taxels "
                "(empty disables it)",
            ),
            DeclareLaunchArgument(
                "counts_per_unit",
                default_value="1000.0",
                description="Raw Xela counts per unit of taxel force in the FK taxel view",
            ),
            DeclareLaunchArgument(
                "events_file",
                default_value="",
                description="Events JSON for the Edit tab (defaults to the installed events.json)",
            ),
            IncludeLaunchDescription(
                XMLLaunchDescriptionSource(
                    PathJoinSubstitution([FindPackageShare("xela_server_ros2"), "service.launch"])
                ),
                launch_arguments={
                    "file": LaunchConfiguration("xela_config"),
                    "port": LaunchConfiguration("xela_port"),
                    "ip": LaunchConfiguration("xela_ip"),
                }.items(),
                condition=IfCondition(LaunchConfiguration("xela")),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("leap_hand"), "launch", "launch_leap.py"]
                    )
                ),
                launch_arguments={"compliant": LaunchConfiguration("compliant")}.items(),
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
                package="conversions",
                executable="convert_hardware_to_sim",
                name="convert_hardware_to_sim",
                output="screen",
                parameters=[
                    {"hardware_topic": LaunchConfiguration("joint_topic")},
                    {"sim_topic": LaunchConfiguration("sim_topic")},
                ],
            ),
            Node(
                package="mechanical_pen_data_collection",
                executable="record_demonstration",
                name="record_demonstration",
                output="screen",
                parameters=[
                    {
                        "joint_topic": ParameterValue(
                            LaunchConfiguration("joint_topic"), value_type=str
                        )
                    },
                    {"sim_topic": ParameterValue(LaunchConfiguration("sim_topic"), value_type=str)},
                    {"cmd_topic": ParameterValue(LaunchConfiguration("cmd_topic"), value_type=str)},
                    {
                        "image_topic": ParameterValue(
                            LaunchConfiguration("image_topic"), value_type=str
                        )
                    },
                    {"demo_dir": ParameterValue(LaunchConfiguration("demo_dir"), value_type=str)},
                    {"xela_topic": ParameterValue(LaunchConfiguration("xela_topic"), value_type=str)},
                    {
                        "events_file": ParameterValue(
                            LaunchConfiguration("events_file"), value_type=str
                        )
                    },
                    {
                        "counts_per_unit": ParameterValue(
                            LaunchConfiguration("counts_per_unit"), value_type=float
                        )
                    },
                ],
            ),
        ]
    )
