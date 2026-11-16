# reward_models

This package learns reward functions for the mechanical pen task: Index, Middle and Ring hold
the pen while the Thumb presses it until it clicks. The models learn from the labelled Play on
hand recordings' **Sparsh-skin episodes**: the `flex_taxel_fk/forces_local` and
`flex_taxel_fk/positions` of the 368 taxels. They use no camera images. Run the Process tab's
Sparsh-skin transform first so the episodes exist.

Two methods are implemented:

| Method | Paper | What it learns |
| --- | --- | --- |
| `rank2reward` | Yang et al., *Rank2Reward: Learning Shaped Reward Functions from Passive Video*, ICRA 2024 ([site](https://rank2reward.github.io/)) | A progress score per taxel state, learned by ranking the steps of successful recordings in time. A discriminator stops a policy from exploiting it. |
| `coupled_local_global` | Amigo et al., *Coupled Local and Global World Models for Efficient First Order RL*, CoRL 2026 ([arXiv](https://arxiv.org/abs/2602.06219)) | The two reward models of that method: a global per-step reward head trained on the labels, and a small local recurrent model whose reward follows the global one and whose one-step dynamics would give policy gradients. The world models and RL themselves are not built yet. |

Each method has two ROS nodes:

- a **training action server**, `/<method>_train/train`. You press Train in the GUI and get
  progress back as feedback;
- an **inference service**, `/<method>_inference/evaluate`. It returns the reward over a
  recording.

Training and inference both log to Weights & Biases, set up the same way as LEQ_DV3.

## Quick start

The nodes start with the app. Nothing needs to be launched by hand:

```bash
cd /workspace/LeapXELA_Hardware_ws/ros_ws
colcon build --packages-select leapxela_sparshskin_msgs mechanical_pen_data_collection reward_models
source install/setup.bash
ros2 launch mechanical_pen_data_collection launch_record_demonstration.py   # reward_models:=false leaves them out
```

Then open the **Reward** tab and pick a processed recording. It plays like the
Demonstration tab, with a **Rank2Reward** and a **SARM** graph of the trained models'
predictions in the middle (SARM's grip / press / click stages shaded on its graph and on the
play bar). Pick another trained run above either graph to compare.

To run only the reward nodes, without the app:
`ros2 launch reward_models reward_models.launch.py`.

## Documentation

| Page | Read it for |
| --- | --- |
| [docs/overview.md](docs/overview.md) | How the pieces fit together, from a recording to a reward on screen. |
| [docs/data.md](docs/data.md) | Which episodes are used, what is taken from each, step rate, normalisation, and the train / validation split. |
| [docs/rank2reward.md](docs/rank2reward.md) | The Rank2Reward networks, losses, reward and validation metrics. |
| [docs/coupled_local_global.md](docs/coupled_local_global.md) | The global and local reward models, their targets, losses and metrics. |
| [docs/nodes_and_interfaces.md](docs/nodes_and_interfaces.md) | The action, the service, node parameters, the run folder and W&B logging. |
| [docs/gui.md](docs/gui.md) | The Reward tab: playing a recording with the Rank2Reward and SARM predictions. |

## Package layout

| File | What it does |
| --- | --- |
| [reward_models/data.py](reward_models/data.py) | Sparsh-skin episodes → `Clip`s (`forces_local` and `positions` per taxel, plus actions), normalisation stats and a stratified split. |
| [reward_models/networks.py](reward_models/networks.py) | `StateEncoder` (z-score + MLP over the 368 taxels), the MLP, the symlog two-hot head, AUC / Spearman. |
| [reward_models/training.py](reward_models/training.py) | `TrainConfig`, the `StepBank` of steps on the GPU, checkpoints, and the run driver `run_training`. |
| [reward_models/rank2reward.py](reward_models/rank2reward.py) | The Rank2Reward method: `train`, `evaluate`, `Model`. |
| [reward_models/coupled_local_global.py](reward_models/coupled_local_global.py) | The Coupled Local Global reward models: `train`, `evaluate`, `Model`. |
| [reward_models/logging_utils.py](reward_models/logging_utils.py) | `RunLogger`: `metrics.jsonl` and W&B. |
| [reward_models/train_node.py](reward_models/train_node.py) | The training action servers. |
| [reward_models/inference_node.py](reward_models/inference_node.py) | The inference services (`rank2reward`, `sarm`, `coupled_local_global`). |
| [launch/reward_models.launch.py](launch/reward_models.launch.py) | Starts `rank2reward_inference` and `sarm_inference` (`wandb:=true` logs each evaluation). `launch_record_demonstration.py` includes it. |

The interfaces live in `leapxela_sparshskin_msgs`: `action/TrainReward.action` and
`srv/EvaluateReward.srv`. The GUI side is in `record_demonstration.py` (`RewardTab`,
`RewardPredictionPlot`). The plan for the parts not built yet, including
the Manual reward, is in `mechanical_pen_data_collection/reward_design_plan.md`.

## Requirements

`torch` and `wandb` come from the system Python (pip), not rosdep. A CUDA GPU is used when
there is one; otherwise the nodes run on the CPU. W&B reads `WANDB_API_KEY` from the
environment or from `LEQ_DV3/.env`.
