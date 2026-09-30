from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

import yaml


def _launch_setup(context, *args, **kwargs):
    joint_topic = LaunchConfiguration("joint_topic").perform(context)
    render_hz = int(LaunchConfiguration("render_hz").perform(context))
    object_arg = LaunchConfiguration("object").perform(context)
    object_mass = float(LaunchConfiguration("object_mass").perform(context))
    object_size = yaml.safe_load(LaunchConfiguration("object_size").perform(context))
    object_pos = yaml.safe_load(LaunchConfiguration("object_pos").perform(context))

    if object_size is None:
        object_size = [0.025, 0.025, 0.025]
    if isinstance(object_size, (int, float)):
        object_size = [float(object_size)]
    if not isinstance(object_size, list):
        object_size = list(object_size)
    if object_pos is None:
        object_pos = []
    if not isinstance(object_pos, list):
        object_pos = list(object_pos)

    params = {
        "joint_topic": joint_topic,
        "render_hz": render_hz,
        "object": object_arg,
        "object_size": [float(v) for v in object_size],
        "object_mass": object_mass,
    }
    # Empty lists are rejected by launch_ros parameter type inference.
    if object_pos:
        params["object_pos"] = [float(v) for v in object_pos]

    return [
        Node(
            package="xela_sparshskin_sim",
            executable="hand_controller.py",
            name="hand_controller",
            output="screen",
        ),
        Node(
            package="xela_sparshskin_sim",
            executable="taxel_pertubation.py",
            name="taxel_pertubation",
            output="screen",
        ),
        Node(
            package="xela_sparshskin_sim",
            executable="process_hand_sensors_into_pointcloud",
            name="process_hand_sensors_into_pointcloud",
            output="screen",
            parameters=[params],
        ),
    ]


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "joint_topic",
                default_value="xela_joint_publisher",
                description="JointState topic published by hand_controller and consumed by the simulator.",
            ),
            DeclareLaunchArgument(
                "render_hz",
                default_value="60",
                description="MuJoCo viewer render rate (Hz).",
            ),
            DeclareLaunchArgument(
                "object",
                default_value="",
                description=(
                    "If set (e.g. cube|box|sphere|cylinder|capsule|ellipsoid), spawn that "
                    "free object in the scene. Empty string = no object."
                ),
            ),
            DeclareLaunchArgument(
                "object_size",
                default_value="[0.025, 0.025, 0.025]",
                description="Object size (one float or [sx, sy, sz] MuJoCo geom sizes).",
            ),
            DeclareLaunchArgument(
                "object_mass",
                default_value="0.1",
                description="Object mass (kg).",
            ),
            DeclareLaunchArgument(
                "object_pos",
                default_value="[]",
                description="Optional spawn pose [x, y, z]. Empty = default spawn.",
            ),
            OpaqueFunction(function=_launch_setup),
        ]
    )
