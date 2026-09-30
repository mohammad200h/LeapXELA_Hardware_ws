from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    joint_topic = LaunchConfiguration("joint_topic")
    repeator_topic = LaunchConfiguration("repeator_topic")
    hardware_topic = LaunchConfiguration("hardware_topic")
    publish_rate_hz = LaunchConfiguration("publish_rate_hz")
    action_name = LaunchConfiguration("action_name")

    leap_hand = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("leap_hand"), "launch", "launch_leap.py"]
            )
        )
    )

    convert_sim_to_hardware = Node(
        package="oculusTeleop",
        executable="convert_sim_to_hardware",
        name="convert_sim_to_hardware",
        output="screen",
        parameters=[
            {"teleop_topic": joint_topic},
            {"hardware_topic": hardware_topic},
        ],
    )

    command_repeator = Node(
        package="leapXela_sparshskin_data_collection",
        executable="command_repeator",
        name="command_repeator",
        output="screen",
        parameters=[
            {"input_topic": repeator_topic},
            {"joint_topic": joint_topic},
            {"publish_rate_hz": ParameterValue(publish_rate_hz, value_type=float)},
        ],
    )

    motion_action_server = Node(
        package="leapXela_sparshskin_data_collection",
        executable="motion_action",
        name="motion_action_server",
        output="screen",
        parameters=[
            {"joint_topic": repeator_topic},
            {"publish_rate_hz": ParameterValue(publish_rate_hz, value_type=float)},
            {"action_name": action_name},
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "joint_topic",
                default_value="oculus_teleop_joint_commands",
                description="JointState topic for sim/teleop hand commands (repeator output).",
            ),
            DeclareLaunchArgument(
                "repeator_topic",
                default_value="repeator_joint_commands",
                description="JointState topic from motion_action into the command repeator.",
            ),
            DeclareLaunchArgument(
                "hardware_topic",
                default_value="cmd_xela",
                description="Hardware JointState topic from convert_sim_to_hardware.",
            ),
            DeclareLaunchArgument(
                "publish_rate_hz",
                default_value="10.0",
                description="Joint command publish rate for motion playback and repeator (Hz).",
            ),
            DeclareLaunchArgument(
                "action_name",
                default_value="execute_motion",
                description="ExecuteMotion action server name.",
            ),
            leap_hand,
            convert_sim_to_hardware,
            command_repeator,
            motion_action_server,
        ]
    )
