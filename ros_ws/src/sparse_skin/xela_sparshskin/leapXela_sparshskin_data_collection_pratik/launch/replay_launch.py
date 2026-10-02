from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    server_port = ParameterValue(LaunchConfiguration("server_port"), value_type=int)

    fk_taxels = Node(
        package="leapXela_taxels_forewardkinematic",
        executable="fk_taxels",
        name="fk_taxels",
        output="screen",
    )

    fk_taxels_viewer = Node(
        package="leapXela_taxels_forewardkinematic",
        executable="fk_taxels_viewer",
        name="fk_taxels_viewer",
        output="screen",
    )

    replay_node = Node(
        package="leapXela_sparshskin_data_collection_pratik",
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
            fk_taxels,
            fk_taxels_viewer,
            replay_node,
        ]
    )

