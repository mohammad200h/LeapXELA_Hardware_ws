from __future__ import annotations

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare
from launch_xml.launch_description_sources import XMLLaunchDescriptionSource


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "joint_topic",
                default_value="leap_state",
                description="Hardware JointState topic published by leaphand_node",
            ),
            DeclareLaunchArgument(
                "sim_topic",
                default_value="leap_state_sim",
                description="Sim-frame JointState topic published by convert_hardware_to_sim",
            ),
            DeclareLaunchArgument(
                "cmd_topic",
                default_value="cmd_xela",
                description="JointState command topic of leaphand_node, used by Play",
            ),
            DeclareLaunchArgument(
                "sim_cmd_topic",
                default_value="sim_command",
                description="Sim-frame JointState topic Test in sim sends to mujoco_sim_node",
            ),
            DeclareLaunchArgument(
                "finger_contact_topic",
                default_value="finger_contacts",
                description="Finger-finger contacts published by mujoco_sim_node, shown by "
                "Test in sim",
            ),
            DeclareLaunchArgument(
                "image_topic",
                default_value="/camera/color/image_raw",
                description="Camera Image topic recorded with each take (empty disables the camera)",
            ),
            DeclareLaunchArgument(
                "camera",
                default_value="true",
                description="Start the RealSense camera (realsense_ros2_camera rs.launch.py)",
            ),
            DeclareLaunchArgument(
                "demo_dir",
                default_value="",
                description="Directory demonstrations are saved into "
                "(defaults to ros_ws/demonstrations)",
            ),
            DeclareLaunchArgument(
                "compliant",
                default_value="true",
                description="Low-gain LEAP hand so the fingers can be moved by hand",
            ),
            DeclareLaunchArgument(
                "state_rate",
                default_value="10.0",
                description="leap_state publish rate of leaphand_node (Hz)",
            ),
            DeclareLaunchArgument(
                "xela",
                default_value="true",
                description="Start xela_server / xela_service (xela_server_ros2 service.launch)",
            ),
            DeclareLaunchArgument(
                "xela_config",
                default_value="/etc/xela/xServ.ini",
                description="xela_server config file",
            ),
            DeclareLaunchArgument(
                "xela_port",
                default_value="5000",
                description="xela_server port",
            ),
            DeclareLaunchArgument(
                "xela_ip",
                default_value="127.0.0.1",
                description="xela_server IP",
            ),
            DeclareLaunchArgument(
                "xela_topic",
                default_value="/xServTopic",
                description="SensStream topic of xela_service shown on the FK taxels "
                "(empty disables it)",
            ),
            DeclareLaunchArgument(
                "counts_per_unit",
                default_value="1000.0",
                description="Raw Xela counts per unit of taxel force in the FK taxel view",
            ),
            DeclareLaunchArgument(
                "events_file",
                default_value="",
                description="Events JSON for the Edit tab (defaults to the installed events.json)",
            ),
            DeclareLaunchArgument(
                "sam",
                default_value="true",
                description="Start bounding_box_sam (mask and box for the matching camera frame)",
            ),
            DeclareLaunchArgument(
                "sam_prefix",
                default_value="/bounding_box_sam",
                description="Prefix of the SAM annotated image, mask, and boxes topics",
            ),
            DeclareLaunchArgument(
                "click_detector",
                default_value="true",
                description="Start the pen click detector "
                "(push_button_pen_click_detection launch_click_detector.py)",
            ),
            DeclareLaunchArgument(
                "min_contact_depth",
                default_value="0.0005",
                description="Finger-finger contacts shallower than this (m) are not counted, by "
                "the sim and by the Compose tab's combination check",
            ),
            DeclareLaunchArgument(
                "click_topic",
                default_value="/pen_click",
                description="Int32 click detector topic (1 while a click is heard), used by the "
                "click setting search and its light (empty disables it)",
            ),
            IncludeLaunchDescription(
                XMLLaunchDescriptionSource(
                    PathJoinSubstitution([FindPackageShare("xela_server_ros2"), "service.launch"])
                ),
                launch_arguments={
                    "file": LaunchConfiguration("xela_config"),
                    "port": LaunchConfiguration("xela_port"),
                    "ip": LaunchConfiguration("xela_ip"),
                }.items(),
                condition=IfCondition(LaunchConfiguration("xela")),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("leap_hand"), "launch", "launch_leap.py"]
                    )
                ),
                launch_arguments={
                    "compliant": LaunchConfiguration("compliant"),
                    "state_rate": LaunchConfiguration("state_rate"),
                }.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("realsense_ros2_camera"), "launch", "rs.launch.py"]
                    )
                ),
                condition=IfCondition(LaunchConfiguration("camera")),
            ),
            # Scoped: its camera:=false / viewer:=false would otherwise leak into the includes
            # below (included launch arguments are not scoped) and start the sim headless.
            GroupAction(
                [
                    IncludeLaunchDescription(
                        PythonLaunchDescriptionSource(
                            PathJoinSubstitution([
                                FindPackageShare("bounding_box_sam"),
                                "launch",
                                "launch_bounding_box_sam.py",
                            ])
                        ),
                        launch_arguments={
                            "camera": "false",
                            "viewer": "false",
                            "image_topic": LaunchConfiguration("image_topic"),
                            "topic_prefix": LaunchConfiguration("sam_prefix"),
                        }.items(),
                    ),
                ],
                scoped=True,
                condition=IfCondition(LaunchConfiguration("sam")),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([
                        FindPackageShare("push_button_pen_click_detection"),
                        "launch",
                        "launch_click_detector.py",
                    ])
                ),
                launch_arguments={"output_topic": LaunchConfiguration("click_topic")}.items(),
                condition=IfCondition(LaunchConfiguration("click_detector")),
            ),
            # The MuJoCo sim is always started (Compose tab: Test in sim, Play on sim).
            # Scoped: the include's cmd_topic would otherwise replace the hand's for the nodes
            # below (included launch arguments are not scoped).
            GroupAction(
                [
                    IncludeLaunchDescription(
                        PythonLaunchDescriptionSource(
                            PathJoinSubstitution([
                                FindPackageShare("mechanical_pen_data_collection"),
                                "launch",
                                "launch_mujoco_sim.py",
                            ])
                        ),
                        launch_arguments={
                            "cmd_topic": LaunchConfiguration("sim_cmd_topic"),
                            "contact_topic": LaunchConfiguration("finger_contact_topic"),
                            "min_contact_depth": LaunchConfiguration("min_contact_depth"),
                            "viewer": "true",  # always with its window
                        }.items(),
                    ),
                ],
                scoped=True,
            ),
            Node(
                package="conversions",
                executable="convert_hardware_to_sim",
                name="convert_hardware_to_sim",
                output="screen",
                parameters=[
                    {"hardware_topic": LaunchConfiguration("joint_topic")},
                    {"sim_topic": LaunchConfiguration("sim_topic")},
                ],
            ),
            Node(
                package="mechanical_pen_data_collection",
                executable="record_demonstration",
                name="record_demonstration",
                output="screen",
                parameters=[
                    {
                        "joint_topic": ParameterValue(
                            LaunchConfiguration("joint_topic"), value_type=str
                        )
                    },
                    {"sim_topic": ParameterValue(LaunchConfiguration("sim_topic"), value_type=str)},
                    {"cmd_topic": ParameterValue(LaunchConfiguration("cmd_topic"), value_type=str)},
                    {
                        "sim_cmd_topic": ParameterValue(
                            LaunchConfiguration("sim_cmd_topic"), value_type=str
                        )
                    },
                    {
                        "finger_contact_topic": ParameterValue(
                            LaunchConfiguration("finger_contact_topic"), value_type=str
                        )
                    },
                    {
                        "image_topic": ParameterValue(
                            LaunchConfiguration("image_topic"), value_type=str
                        )
                    },
                    {"demo_dir": ParameterValue(LaunchConfiguration("demo_dir"), value_type=str)},
                    {
                        "sam_prefix": ParameterValue(
                            LaunchConfiguration("sam_prefix"), value_type=str
                        )
                    },
                    {"xela_topic": ParameterValue(LaunchConfiguration("xela_topic"), value_type=str)},
                    {
                        "click_topic": ParameterValue(
                            LaunchConfiguration("click_topic"), value_type=str
                        )
                    },
                    {
                        "events_file": ParameterValue(
                            LaunchConfiguration("events_file"), value_type=str
                        )
                    },
                    {
                        "counts_per_unit": ParameterValue(
                            LaunchConfiguration("counts_per_unit"), value_type=float
                        )
                    },
                    {
                        "min_contact_depth": ParameterValue(
                            LaunchConfiguration("min_contact_depth"), value_type=float
                        )
                    },
                ],
            ),
        ]
    )
