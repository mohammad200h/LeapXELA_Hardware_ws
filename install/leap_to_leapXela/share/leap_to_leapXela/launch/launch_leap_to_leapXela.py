from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    joint_topic_arg = DeclareLaunchArgument(
        "joint_topic",
        default_value="leap_joint",
        description="JointState topic (leap_publisher publishes, leap_xela_subscriber subscribes)",
    )
    use_gui_arg = DeclareLaunchArgument(
        "use_gui",
        default_value="true",
        description="Enable PyBullet GUI in both nodes",
    )
    sim_hz_arg = DeclareLaunchArgument(
        "sim_hz",
        default_value="240",
        description="PyBullet simulation step rate (Hz)",
    )
    publish_hz_arg = DeclareLaunchArgument(
        "publish_hz",
        default_value="50",
        description="JointState publish rate for leap_publisher (Hz)",
    )

    leap_publisher = Node(
        package="leap_to_leapXela",
        executable="leap_publisher",
        name="leap_publisher",
        output="screen",
        parameters=[
            {"joint_topic": LaunchConfiguration("joint_topic")},
            {"use_gui": ParameterValue(LaunchConfiguration("use_gui"), value_type=bool)},
            {"sim_hz": ParameterValue(LaunchConfiguration("sim_hz"), value_type=int)},
            {"publish_hz": ParameterValue(LaunchConfiguration("publish_hz"), value_type=int)},
        ],
    )

    leap_xela_subscriber = Node(
        package="leap_to_leapXela",
        executable="leap_xela_subscriber",
        name="leap_xela_subscriber",
        output="screen",
        parameters=[
            {"joint_topic": LaunchConfiguration("joint_topic")},
            {"use_gui": ParameterValue(LaunchConfiguration("use_gui"), value_type=bool)},
            {"sim_hz": ParameterValue(LaunchConfiguration("sim_hz"), value_type=int)},
        ],
    )

    return LaunchDescription(
        [
            joint_topic_arg,
            use_gui_arg,
            sim_hz_arg,
            publish_hz_arg,
            leap_publisher,
            leap_xela_subscriber,
        ]
    )
