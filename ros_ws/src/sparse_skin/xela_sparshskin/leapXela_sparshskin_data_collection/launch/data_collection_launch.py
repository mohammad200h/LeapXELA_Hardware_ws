import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    joint_topic = LaunchConfiguration("joint_topic")
    render_hz = LaunchConfiguration("render_hz")
    mode = LaunchConfiguration("mode")
    server_port = ParameterValue(LaunchConfiguration("server_port"), value_type=int)

    is_sim = PythonExpression(["'", mode, "' == 'sim'"])
    is_hardware = PythonExpression(["'", mode, "' == 'hardware'"])

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
        condition=IfCondition(is_sim),
    )

    # Sim: joints from hand_controller, sensors from MuJoCo HandSensors.
    fk_taxels_demo_sim = Node(
        package="leapXela_taxels_forewardkinematic",
        executable="fk_taxels_demo",
        name="fk_taxels_demo",
        output="screen",
        parameters=[
            {
                "joint_topic": joint_topic,
                "hand_sensors_topic": "hand_sensors",
            }
        ],
        condition=IfCondition(is_sim),
    )

    # Hardware: joints from leap_state (forces stay unused; SensStream ≠ HandSensors).
    fk_taxels_demo_hardware = Node(
        package="leapXela_taxels_forewardkinematic",
        executable="fk_taxels_demo",
        name="fk_taxels_demo",
        output="screen",
        parameters=[
            {
                "joint_topic": "leap_state",
            }
        ],
        condition=IfCondition(is_hardware),
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
                description="JointState topic for the simulator / hand controller (sim mode).",
            ),
            DeclareLaunchArgument(
                "render_hz",
                default_value="60",
                description="MuJoCo viewer render rate (Hz).",
            ),
            DeclareLaunchArgument(
                "mode",
                default_value="sim",
                description=(
                    "Data collection mode: 'sim' (MuJoCo) or 'hardware' "
                    "(record /cmd_xela, /leap_state, /oculus_teleop_joint_commands, /xServTopic)."
                ),
            ),
            DeclareLaunchArgument(
                "server_port",
                default_value="7860",
                description="Gradio UI port for sparsh_skin_demonstration.",
            ),
            sim_launch,
            fk_taxels_demo_sim,
            fk_taxels_demo_hardware,
            sparsh_skin_demonstration,
        ]
    )
