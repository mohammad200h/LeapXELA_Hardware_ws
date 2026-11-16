"""The reward models' inference services used by record_demonstration's Reward tab
(``rank2reward_inference`` and ``sarm_inference``). The training action servers
(``<method>_train``) and ``coupled_local_global_inference`` are run by hand when needed."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    wandb = ParameterValue(LaunchConfiguration("wandb"), value_type=bool)
    return LaunchDescription([
        DeclareLaunchArgument(
            "wandb",
            default_value="false",
            description="Log each evaluation to W&B (off: the Reward tab evaluates every "
            "recording it shows)",
        ),
        *[
            Node(package="reward_models", executable=name, name=name, output="screen",
                 parameters=[{"wandb": wandb}])
            for name in ("rank2reward_inference", "sarm_inference")
        ],
    ])
