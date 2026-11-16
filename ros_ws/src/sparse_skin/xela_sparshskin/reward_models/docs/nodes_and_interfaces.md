# Nodes, interfaces, run folders and W&B

## Launching

[launch/reward_models.launch.py](../launch/reward_models.launch.py) starts four nodes.
`mechanical_pen_data_collection`'s `launch_record_demonstration.py` includes it, so they start
with the app. Pass `reward_models:=false` to leave them out.

| Node | Serves | Type |
| --- | --- | --- |
| `rank2reward_train` | `/rank2reward_train/train` | action `leapxela_sparshskin_msgs/action/TrainReward` |
| `coupled_local_global_train` | `/coupled_local_global_train/train` | action `TrainReward` |
| `rank2reward_inference` | `/rank2reward_inference/evaluate` | service `leapxela_sparshskin_msgs/srv/EvaluateReward` |
| `sarm_inference` | `/sarm_inference/evaluate` | service `EvaluateReward` (terms `progress`, `stage`) |
| `coupled_local_global_inference` | `/coupled_local_global_inference/evaluate` | service `EvaluateReward` |

The nodes cost little while idle. A training node does nothing until it gets a goal, and an
inference node loads a model onto the GPU only at its first request.

## The training action: `TrainReward`

### Goal

Zero or empty fields mean "use the node's parameter".

| Field | Meaning |
| --- | --- |
| `recordings_dir` | Play on hand recordings to train on |
| `output_dir` | Runs go to `<output_dir>/<run name>/`; empty means `<recordings_dir>/reward_models/<method>` |
| `epochs`, `batch_size`, `learning_rate`, `val_fraction`, `seed` | Training settings |
| `step_hz` | The Sparsh-skin episodes (100 Hz) are taken at this rate: every `round(100 / step_hz)` steps, plus the last |
| `wandb`, `wandb_project`, `wandb_name` | Whether to log to W&B, the project, and the run name (empty means `<method>_<time>`) |

### Feedback

Sent while loading and once per epoch:

| Field | Meaning |
| --- | --- |
| `stage` | `loading` or `training` |
| `progress` | 0 to 1 over the whole run; loading takes the first 0.15 |
| `epoch`, `epochs` | Current epoch and the total |
| `train_loss`, `val_loss`, `val_metric`, `val_metric_name` | The epoch's numbers |
| `status` | A line of text, for example `epoch 3/30 (best, saved)` |

### Result

`success`, `message`, `run_dir`, `wandb_url`, plus the last `train_loss` / `val_loss` and the
best `val_metric` with its `val_metric_name`.

### Behaviour

- **One goal at a time per node.** A second goal is rejected. The two methods have separate
  nodes, so they can train at the same time; both share the GPU.
- **Cancel** stops after the current gradient step. The best epoch so far stays in the run
  folder, and the action ends `CANCELED`.
- It ends `ABORTED` with a message when, for example, there are fewer than 2 successes with
  a Sparsh-skin episode to train on.

You can also train from a terminal:

```bash
ros2 action send_goal --feedback /rank2reward_train/train \
  leapxela_sparshskin_msgs/action/TrainReward "{epochs: 30, step_hz: 25.0, wandb: true}"
```

### Training node parameters

Used for empty goal fields:

| Parameter | Default |
| --- | --- |
| `recordings_dir` | `<ws>/demonstrations/compose_playbacks` |
| `output_dir` | `""`, meaning `<recordings_dir>/reward_models/<method>` |
| `epochs`, `steps_per_epoch`, `batch_size`, `learning_rate`, `val_fraction`, `step_hz`, `seed` | 30, 200, 64, 3e-4, 0.2, 25.0, 0 |
| `device` | `cuda`; falls back to the CPU when there is no GPU |
| `wandb_project` | `reward_models` |
| `wandb_env_file` | `/workspace/LeapXELA_Hardware_ws/LEQ_DV3/.env` |

`steps_per_epoch` is only a parameter, not a goal field. One epoch is 200 gradient steps,
not one pass over the data.

## The inference service: `EvaluateReward`

| Request | |
| --- | --- |
| `run_dir` | A run folder; empty means the newest run in the node's `runs_dir` |
| `recording` | The recording's `.npz` |

| Response | |
| --- | --- |
| `success`, `message` | |
| `run_dir`, `label` | The run used and the recording's label |
| `t` | Recording time of each episode step used |
| `reward` | The reward at each `t` |
| `term_names`, `terms` | The reward's parts, flattened term by term (`len(term_names) × len(t)`) |

From a terminal:

```bash
ros2 service call /rank2reward_inference/evaluate leapxela_sparshskin_msgs/srv/EvaluateReward \
  "{recording: '/workspace/LeapXELA_Hardware_ws/ros_ws/demonstrations/compose_playbacks/th_1_1.npz'}"
```

Inference node parameters:

| Parameter | Default |
| --- | --- |
| `runs_dir` | `<ws>/demonstrations/compose_playbacks/reward_models/<method>` |
| `device` | `cuda` |
| `wandb` | `true` |
| `wandb_project` | `reward_models` |
| `wandb_env_file` | LEQ_DV3's `.env` |

## The run folder

```
<recordings>/reward_models/
├── rank2reward/
│   ├── rank2reward_20261105_120244/
│   │   ├── config.json        settings, counts, W&B URL, train / val / skipped recordings
│   │   ├── metrics.jsonl      one {"step", "time", ...metrics} line per epoch
│   │   ├── model.pt           checkpoint of the best epoch
│   │   ├── eval.json          that epoch's validation results: per recording t, reward, terms
│   │   └── wandb/             W&B's local files
│   └── _inference/            the inference node's W&B runs
└── coupled_local_global/ ...
```

`model.pt` holds the method, the full `TrainConfig` (with the step rate and the six
normalisation means / stds), the networks' weights (their encoders keep the same stats), the
epoch and its metrics. Coupled Local Global also saves the action mean / std. Only folders with a
`model.pt` count as runs.

## Weights & Biases

[logging_utils.py](../reward_models/logging_utils.py) sets up W&B the same way as LEQ_DV3
(`dreamerv3/main.py`):

- **API key:** `WANDB_API_KEY` from the environment, otherwise from `LEQ_DV3/.env`
  (`KEY=VALUE` lines; values already in the environment win), otherwise the cached
  `wandb login`.
- **Overrides:** `WANDB_PROJECT` and `WANDB_NAME` replace the project and run name.
  `WANDB_ENABLE=False` turns W&B off everywhere.
- **If W&B fails to start**, for example with no network or key, training goes on and logs
  only to `metrics.jsonl`. The node logs a warning.

What gets logged:

| Run | Logged |
| --- | --- |
| Training (`job_type: train`, one per Train) | The config and data counts; every train / validation metric per epoch; reward and term curves for up to 6 validation recordings per epoch; summary `best/<metric>`, `best/epoch` |
| Inference (`job_type: inference`, one per node, started at its first request) | Per evaluation: `inference/return` (mean reward), `inference/final_reward`, `inference/success`; a plot `inference/<recording>` of the reward and its terms; the table `inference/evaluations` (recording, label, run, return) |

`metrics.jsonl` always has the same scalars as W&B, which is what the GUI's former Visualize tab
plots.
