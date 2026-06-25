import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def load_yaml(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)

    with open(absolute_file_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)


def generate_launch_description():
    load_gripper = LaunchConfiguration('load_gripper')
    arm_id = LaunchConfiguration('arm_id')
    planning_group = LaunchConfiguration('planning_group')
    end_effector_link = LaunchConfiguration('end_effector_link')
    initial_positions = LaunchConfiguration('initial_positions')

    sim_moveit_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('franka_moveit_config'),
                'launch',
                'sim_moveit.launch.py',
            )
        ),
        launch_arguments={
            'load_gripper': load_gripper,
            'initial_positions': initial_positions,
        }.items(),
        condition=IfCondition(LaunchConfiguration('launch_sim')),
    )

    franka_xacro_file = os.path.join(
        get_package_share_directory('franka_description'),
        'robots', 'sim', 'panda_arm_sim.urdf.xacro')
    franka_semantic_xacro_file = os.path.join(
        get_package_share_directory('franka_moveit_config'),
        'srdf', 'panda_arm.srdf.xacro')

    robot_description = {
        'robot_description': Command([
            FindExecutable(name='xacro'), ' ', franka_xacro_file,
            ' arm_id:=', arm_id,
            ' hand:=', load_gripper,
        ])
    }
    robot_description_semantic = {
        'robot_description_semantic': Command([
            FindExecutable(name='xacro'), ' ', franka_semantic_xacro_file,
            ' hand:=', load_gripper,
        ])
    }

    kinematics_yaml = load_yaml('franka_moveit_config', 'config/kinematics.yaml')
    default_walls_config_file = os.path.join(
        get_package_share_directory('arm_server'),
        'script',
        'ws_table.json',
    )

    arm_action_server_node = Node(
        package='arm_server',
        executable='arm_action_server',
        output='screen',
        parameters=[
            robot_description,
            robot_description_semantic,
            kinematics_yaml,
            {
                'planning_group': planning_group,
                'end_effector_link': end_effector_link,
                'planning_frame': 'panda_link0',
            },
        ],
    )

    build_the_wall_node = Node(
        package='arm_server',
        executable='build_the_wall',
        output='screen',
        parameters=[{
            'config_file': LaunchConfiguration('walls_config_file'),
            'clear_existing': ParameterValue(
                LaunchConfiguration('clear_existing_walls'),
                value_type=bool,
            ),
        }],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'launch_sim',
            default_value='true',
            description='Launch MoveIt + MuJoCo sim via sim_moveit.launch.py.'),
        DeclareLaunchArgument(
            'arm_id',
            default_value='panda',
            description='Robot name prefix used in URDF/SRDF.'),
        DeclareLaunchArgument(
            'load_gripper',
            default_value='false',
            description='Match the gripper setting used by the running MoveIt launch.'),
        DeclareLaunchArgument(
            'initial_positions',
            default_value='"0.0 0 0.0 0 0.0 0 0"',
            description='Initial joint positions for MuJoCo sim. Must be quoted.'),
        sim_moveit_launch,
        DeclareLaunchArgument(
            'planning_group',
            default_value='panda_arm',
            description='MoveIt planning group. Use panda_manipulator when load_gripper is true.'),
        DeclareLaunchArgument(
            'end_effector_link',
            default_value='panda_link8',
            description='End-effector link. Use panda_hand_tcp when load_gripper is true.'),
        DeclareLaunchArgument(
            'build_walls',
            default_value='true',
            description='Load workspace walls into the MoveIt scene on startup.'),
        DeclareLaunchArgument(
            'walls_config_file',
            default_value=default_walls_config_file,
            description='JSON file describing walls to add to the planning scene.'),
        DeclareLaunchArgument(
            'clear_existing_walls',
            default_value='true',
            description='Remove previously added walls before loading the JSON scene.'),
        arm_action_server_node,
        TimerAction(
            period=2.0,
            actions=[build_the_wall_node],
            condition=IfCondition(LaunchConfiguration('build_walls')),
        ),
    ])
