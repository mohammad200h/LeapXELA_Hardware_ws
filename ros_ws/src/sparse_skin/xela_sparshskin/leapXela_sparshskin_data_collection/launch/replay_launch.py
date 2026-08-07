from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    server_port = ParameterValue(LaunchConfiguration("server_port"), value_type=int)

    fk_taxels_demo = Node(
        package="leapXela_taxels_forewardkinematic",
        executable="fk_taxels_demo",
        name="fk_taxels_demo",
        output="screen",
    )

    replay_node = Node(
        package="leapXela_sparshskin_data_collection",
        executable="replay",
        name="sparsh_skin_replay",
        output="screen",
        parameters=[
            {
                "server_port": server_port,
            }
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "server_port",
                default_value="7861",
                description="Gradio UI port for sparsh_skin_replay.",
            ),
            fk_taxels_demo,
            replay_node,
        ]
    )

