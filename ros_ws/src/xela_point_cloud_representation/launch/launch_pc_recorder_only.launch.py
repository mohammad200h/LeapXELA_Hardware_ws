from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node


def generate_launch_description():
    dataset_root = LaunchConfiguration("dataset_root")
    scaled_root = LaunchConfiguration("scaled_root")

    sensor_value_publisher = Node(
        package="xela_point_cloud_representation",
        executable="sensor_value_publisher.py",
        name="sensor_value_publisher",
        output="screen",
        parameters=[
            {
                "dataset_root": dataset_root,
                "scaled_root": scaled_root,
            }
        ],
    )

    pointcloud_processor = Node(
        package="xela_point_cloud_representation",
        executable="process_hand_sensors_into_pointcloud",
        name="process_hand_sensors_into_pointcloud",
        output="screen",
        parameters=[
            {
                "joint_topic": "xela_joint_publisher",
                "sensor_topic": "sensor_values",
            }
        ],
    )

    pointcloud_recorder = Node(
        package="xela_point_cloud_representation",
        executable="point_cloud_dump.py",
        name="hand_touch_point_cloud_recorder",
        output="screen",
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            "dataset_root",
            default_value="/workspace/LeapXELA_Hardware_ws/ros_ws/src/xela_point_cloud_representation/pointcloud_calibration/ML_dataset",
            description="Root directory containing ML_dataset/contour/<dataset_type>/*.h5 files.",
        ),
        DeclareLaunchArgument(
            "scaled_root",
            default_value="interim",
            description="Directory name under pointcloud_calibration containing scaled tactile npy files.",
        ),

        sensor_value_publisher,
        pointcloud_processor,
        pointcloud_recorder,
    ])