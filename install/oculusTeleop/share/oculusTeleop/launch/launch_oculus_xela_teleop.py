from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    joint_topic_arg = DeclareLaunchArgument(
        "joint_topic",
        default_value="oculus_teleop_joint_commands",
        description=(
            "Sim/teleop JointState topic (avp_leap_xela_server publishes, "
            "leap_xela_client and convert_sim_to_hardware subscribe)"
        ),
    )
    quest_ip_arg = DeclareLaunchArgument(
        "quest_ip",
        default_value="192.168.2.48",  # UCL IP
        # default_value="192.168.1.65",  # Home IP
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
    is_left_arg = DeclareLaunchArgument(
        "is_left",
        default_value="false",
        description="Use left-hand tracking and IK mapping",
    )
    publish_rate_hz_arg = DeclareLaunchArgument(
        "publish_rate_hz",
        default_value="30.0",
        description="JointState publish rate (Hz)",
    )
    wait_for_tracking_sec_arg = DeclareLaunchArgument(
        "wait_for_tracking_sec",
        default_value="30.0",
        description="Seconds to wait for first tracking packet at startup",
    )
    hardware_topic_arg = DeclareLaunchArgument(
        "hardware_topic",
        default_value="cmd_xela",
        description="Hardware topic (convert_sim_to_hardware publishes)",
    )

    avp_leap_xela_server = Node(
        package="oculusTeleop",
        executable="avp_leap_xela_server",
        name="avp_leap_xela_server",
        output="screen",
        parameters=[
            {"joint_topic": LaunchConfiguration("joint_topic")},
            {"quest_ip": LaunchConfiguration("quest_ip")},
            {"quest_port": ParameterValue(LaunchConfiguration("quest_port"), value_type=int)},
            {"use_gui": ParameterValue(LaunchConfiguration("use_gui"), value_type=bool)},
            {"is_left": ParameterValue(LaunchConfiguration("is_left"), value_type=bool)},
            {
                "publish_rate_hz": ParameterValue(
                    LaunchConfiguration("publish_rate_hz"), value_type=float
                )
            },
            {
                "wait_for_tracking_sec": ParameterValue(
                    LaunchConfiguration("wait_for_tracking_sec"), value_type=float
                )
            },
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

    leap_xela_sim_to_hardware_conversion = Node(
        package="oculusTeleop",
        executable="convert_sim_to_hardware",
        name="convert_sim_to_hardware",
        output="screen",
        parameters=[
            {"teleop_topic": LaunchConfiguration("joint_topic")},
            {"hardware_topic": LaunchConfiguration("hardware_topic")},
        ],
    )

    # add launch_leap.py from ros2_module under LEAP_Hand_API package

    return LaunchDescription(
        [
            joint_topic_arg,
            quest_ip_arg,
            quest_port_arg,
            use_gui_arg,
            is_left_arg,
            publish_rate_hz_arg,
            wait_for_tracking_sec_arg,
            hardware_topic_arg,
            avp_leap_xela_server,
            leap_xela_client,
            leap_xela_sim_to_hardware_conversion
        ]
    )
