import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    joint_topic = LaunchConfiguration("joint_topic")
    render_hz = LaunchConfiguration("render_hz")
    mode = LaunchConfiguration("mode")
    server_port = ParameterValue(LaunchConfiguration("server_port"), value_type=int)

    sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("xela_sparshskin_sim"),
                "launch",
                "xela_sparshskin_sim_launch.py",
            )
        ),
        launch_arguments={
            "joint_topic": joint_topic,
            "render_hz": render_hz,
        }.items(),
    )

    fk_taxels_demo = Node(
        package="leapXela_taxels_forewardkinematic",
        executable="fk_taxels_demo",
        name="fk_taxels_demo",
        output="screen",
    )

    sparsh_skin_demonstration = Node(
        package="leapXela_sparshskin_data_collection",
        executable="sparsh_skin_demonstration",
        name="sparsh_skin_demonstration",
        output="screen",
        parameters=[
            {
                "mode": mode,
                "server_port": server_port,
            }
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "joint_topic",
                default_value="xela_joint_publisher",
                description="JointState topic for the simulator / hand controller.",
            ),
            DeclareLaunchArgument(
                "render_hz",
                default_value="60",
                description="MuJoCo viewer render rate (Hz).",
            ),
            DeclareLaunchArgument(
                "mode",
                default_value="sim",
                description="Data collection mode: 'sim' or 'real'.",
            ),
            DeclareLaunchArgument(
                "server_port",
                default_value="7860",
                description="Gradio UI port for sparsh_skin_demonstration.",
            ),
            sim_launch,
            fk_taxels_demo,
            sparsh_skin_demonstration,
        ]
    )
