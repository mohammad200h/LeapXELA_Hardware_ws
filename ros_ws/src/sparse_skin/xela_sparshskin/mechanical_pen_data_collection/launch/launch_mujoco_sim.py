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
                "model_path",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("xela_description"), "mjcf", "scene.xml"]
                ),
                description="MuJoCo MJCF scene loaded by mujoco_sim_node",
            ),
            DeclareLaunchArgument(
                "cmd_topic",
                default_value="leap_state_sim",
                description="Sim-frame JointState topic whose positions drive the actuators "
                "(empty disables it)",
            ),
            DeclareLaunchArgument(
                "state_topic",
                default_value="leap_state_mujoco",
                description="JointState topic the simulated joint states are published on",
            ),
            DeclareLaunchArgument(
                "contact_topic",
                default_value="finger_contacts",
                description="std_msgs/String JSON topic of the finger pairs touching each other "
                "(empty disables it)",
            ),
            DeclareLaunchArgument(
                "publish_rate",
                default_value="100.0",
                description="state_topic publish rate (Hz)",
            ),
            DeclareLaunchArgument(
                "viewer",
                default_value="true",
                description="Open the GLFW viewer window",
            ),
            DeclareLaunchArgument(
                "real_time_factor",
                default_value="1.0",
                description="Sim time per wall time",
            ),
            DeclareLaunchArgument(
                "min_contact_depth",
                default_value="0.0005",
                description="Finger-finger contacts shallower than this (m) are not counted",
            ),
            DeclareLaunchArgument(
                "contact_width",
                default_value="0.05",
                description="Radius of the drawn contact points (fraction of the mean body "
                "size)",
            ),
            DeclareLaunchArgument(
                "contact_height",
                default_value="0.02",
                description="Thickness of the drawn contact points (fraction of the mean body "
                "size)",
            ),
            DeclareLaunchArgument(
                "force_width",
                default_value="0.03",
                description="Width of the drawn contact force arrows (fraction of the mean "
                "body size)",
            ),
            Node(
                package="mechanical_pen_data_collection",
                executable="mujoco_sim_node",
                name="mujoco_sim_node",
                output="screen",
                parameters=[
                    {"model_path": ParameterValue(LaunchConfiguration("model_path"), value_type=str)},
                    {"cmd_topic": ParameterValue(LaunchConfiguration("cmd_topic"), value_type=str)},
                    {
                        "state_topic": ParameterValue(
                            LaunchConfiguration("state_topic"), value_type=str
                        )
                    },
                    {
                        "contact_topic": ParameterValue(
                            LaunchConfiguration("contact_topic"), value_type=str
                        )
                    },
                    {
                        "publish_rate": ParameterValue(
                            LaunchConfiguration("publish_rate"), value_type=float
                        )
                    },
                    {"viewer": ParameterValue(LaunchConfiguration("viewer"), value_type=bool)},
                    {
                        "real_time_factor": ParameterValue(
                            LaunchConfiguration("real_time_factor"), value_type=float
                        )
                    },
                    *[
                        {name: ParameterValue(LaunchConfiguration(name), value_type=float)}
                        for name in (
                            "min_contact_depth", "contact_width", "contact_height", "force_width"
                        )
                    ],
                ],
            ),
        ]
    )
