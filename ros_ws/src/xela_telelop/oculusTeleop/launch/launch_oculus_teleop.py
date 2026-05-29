from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    joint_topic_arg = DeclareLaunchArgument(
        "joint_topic",
        default_value="cmd_xela",
        description="JointState topic (avp_leap_server publishes, leap_xela_client subscribes)",
    )
    quest_ip_arg = DeclareLaunchArgument(
        "quest_ip",
        # default_value="192.168.2.48",  # UCL IP
        default_value="192.168.1.65",  # Home IP
        description="Quest / AVP headset IP for UDP tracking",
    )
    quest_port_arg = DeclareLaunchArgument(
        "quest_port",
        default_value="5006",
        description="UDP port for Quest tracking stream",
    )
    use_gui_arg = DeclareLaunchArgument(
        "use_gui",
        default_value="true",
        description="Enable PyBullet GUI in both nodes",
    )

    avp_leap_server = Node(
        package="oculusTeleop",
        executable="avp_leap_server",
        name="avp_leap_server",
        output="screen",
        parameters=[
            {"joint_topic": LaunchConfiguration("joint_topic")},
            {"quest_ip": LaunchConfiguration("quest_ip")},
            {"quest_port": ParameterValue(LaunchConfiguration("quest_port"), value_type=int)},
            {"use_gui": ParameterValue(LaunchConfiguration("use_gui"), value_type=bool)},
        ],
    )

    leap_xela_client = Node(
        package="oculusTeleop",
        executable="leap_xela_client",
        name="leap_xela_client",
        output="screen",
        parameters=[
            {"joint_topic": LaunchConfiguration("joint_topic")},
            {"use_gui": ParameterValue(LaunchConfiguration("use_gui"), value_type=bool)},
        ],
    )

    return LaunchDescription(
        [
            joint_topic_arg,
            quest_ip_arg,
            quest_port_arg,
            use_gui_arg,
            avp_leap_server,
            leap_xela_client,
        ]
    )
