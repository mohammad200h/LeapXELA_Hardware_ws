from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    object_type = LaunchConfiguration("object_type")
    size = LaunchConfiguration("size")
    friction = LaunchConfiguration("friction")
    adhesion = LaunchConfiguration("adhesion")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "object_type",
                default_value="box",
                description="Object geom type: box|cube|sphere|cylinder|capsule|ellipsoid",
            ),
            DeclareLaunchArgument(
                "size",
                default_value="0.05",
                description=(
                    "Geom size: one float (uniform) or three floats "
                    "'sx sy sz' (box half-extents / sphere radius / etc.)"
                ),
            ),
            DeclareLaunchArgument(
                "friction",
                default_value="10.0 1.0 0.5",
                description="Friction coefficients: slide [roll spin]",
            ),
            DeclareLaunchArgument(
                "adhesion",
                default_value="5.0",
                description="Adhesive contact force in Newtons",
            ),
            Node(
                package="objests_description",
                executable="plane_scene_node",
                name="plane_scene_node",
                output="screen",
                arguments=[
                    "--object-type",
                    object_type,
                    "--size",
                    size,
                    "--friction",
                    friction,
                    "--adhesion",
                    adhesion,
                ],
            ),
        ]
    )
