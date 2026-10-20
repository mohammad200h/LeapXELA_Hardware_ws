"""
Classify sounds with pretrained models: one sound_classifier_<model> node per model.

  ros2 launch push_button_pen_click_detection launch_sound_classifier.py             # CLAP
  ros2 launch push_button_pen_click_detection launch_sound_classifier.py models:=clap,ast

If click_detector's launch is running, it already runs audio_publisher (which holds
the mic): add ``start_audio_publisher:=false``.
"""

from __future__ import annotations

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def _classifiers(context):
    models = [m.strip() for m in LaunchConfiguration("models").perform(context).split(",")]
    params = {
        "audio_topic": LaunchConfiguration("audio_topic").perform(context),
        "threshold": float(LaunchConfiguration("threshold").perform(context)),
        "gate": float(LaunchConfiguration("gate").perform(context)),
    }
    return [
        Node(
            package="push_button_pen_click_detection",
            executable="sound_classifier",
            arguments=["--model", model],
            output="screen",
            parameters=[params],
        )
        for model in models if model
    ]


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "models", default_value="clap",
                description="Comma-separated models to run: clap, ast or clap,ast",
            ),
            DeclareLaunchArgument(
                "start_audio_publisher", default_value="true",
                description="Start audio_publisher; false if another launch already runs it",
            ),
            DeclareLaunchArgument(
                "device", default_value="08bb:2902",
                description="USB id (vid:pid), name substring or index of the microphone",
            ),
            DeclareLaunchArgument("audio_topic", default_value="/audio"),
            DeclareLaunchArgument(
                "threshold", default_value="0.5",
                description="Top-label probability needed to publish detected = 1",
            ),
            DeclareLaunchArgument(
                "gate", default_value="4.0",
                description="Loudness over the noise floor that counts as a sound",
            ),
            Node(
                package="push_button_pen_click_detection",
                executable="audio_publisher",
                name="audio_publisher",
                output="screen",
                condition=IfCondition(LaunchConfiguration("start_audio_publisher")),
                parameters=[
                    {"device": ParameterValue(LaunchConfiguration("device"), value_type=str)},
                    {"topic": LaunchConfiguration("audio_topic")},
                ],
            ),
            OpaqueFunction(function=_classifiers),
        ]
    )
