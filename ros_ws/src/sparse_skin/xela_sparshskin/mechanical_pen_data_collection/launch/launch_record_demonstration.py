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
                ],
            ),
        ]
    )
