# How reward_models works

This page follows one training goal and one Reward tab prediction through the code. The
other pages go deeper into each step.

## The pieces

```
record_demonstration (GUI)                          reward_models nodes
┌──────────────────────────────┐                  ┌──────────────────────────────┐
│ Reward tab (a player)        │  EvaluateReward  │ rank2reward_inference        │
│   Rank2Reward graph ────────▶│ ──── request ──▶ │ sarm_inference               │
│   SARM graph (+ stages)  ◀───┼──── response ─── │   Model(run)(clip)           │
└──────────────────────────────┘                  └──────────────────────────────┘
                                                   <method>_train (run by hand)
                                                     TrainReward goal ──▶ run folder + W&B
```

`launch_record_demonstration.py` starts `rank2reward_inference` and `sarm_inference`, so they
are running whenever the app is. The training action servers (`<method>_train`) and
`coupled_local_global_inference` are started by hand when needed; the sections on Train
below describe what a `TrainReward` goal does.

More methods are available to the offline comparison script
[compare.py](../reward_models/compare.py), but have no GUI node: `timerewarder`,
`progressor`, `reds` and `sarm_failures` (SARM itself is served by `sarm_inference`, [sarm.md](sarm.md)). The script
trains every method on Sparsh-skin and on joint state for several seeds, then scores them on
the same held-out recordings:

```
python3 -m reward_models.compare --recordings-dir <recordings> [--methods …] [--seeds 0 1 2]
```

## Sending a TrainReward goal

1. **A goal is sent** to `/<method>_train/train` (by hand, e.g. `ros2 action send_goal`):
   recordings folder, epochs, batch size, learning rate, validation share, step rate, seed,
   and the W&B settings.
2. **The node accepts one goal at a time.**
   [`RewardTrainServer`](../reward_models/train_node.py#L48) rejects a second goal while it
   is training. It fills the goal's zero / empty fields from its ROS parameters
   (`_config`) and calls [`run_training`](../reward_models/training.py#L173) on its own
   thread.
3. **The episodes are loaded.** [`data.load_clips`](../reward_models/data.py#L160) picks
   the labelled recordings and reads each one's Sparsh-skin episode
   (`sparsh_skin/episode_<recording>.npz`). It turns each into a `Clip`: the
   `forces_local` and `positions` of the 368 taxels from `episode_start` to `terminal`, at
   the step rate, with the sim joint targets. All 564 load in a few seconds. Feedback during
   this stage has `stage: loading` and fills the first 15% of the bar. See [data.md](data.md).
4. **The recordings are split.** [`data.split_clips`](../reward_models/data.py#L193) holds
   out `val_fraction` of the successes and of the failures, by recording, so no step of a
   validation recording is trained on. The per-channel normalisation is set: forces from
   `sparsh_stats.json`, positions from the training episodes.
5. **The run folder and logger are made.**
   `<recordings>/reward_models/<method>/<run name>/` gets a `config.json`, and
   [`RunLogger`](../reward_models/logging_utils.py#L44) opens `metrics.jsonl` and, if
   enabled, a W&B run.
6. **The method trains.** `rank2reward.train` or `coupled_local_global.train` runs
   `steps_per_epoch` gradient steps per epoch on batches drawn from a
   [`StepBank`](../reward_models/training.py#L106), with all steps on the GPU. After each
   epoch it scores every validation recording and logs the metrics. It then yields an
   `EpochResult`. See [rank2reward.md](rank2reward.md) and
   [coupled_local_global.md](coupled_local_global.md).
7. **The best epoch is kept.** When an epoch's main validation metric beats the best so far,
   the driver overwrites `model.pt` and `eval.json` (the first epoch is always saved). Every
   epoch sends one feedback message with `stage: training`, the epoch, the losses and the
   metric.
8. **The result comes back.** The action ends with `SUCCEEDED`, `ABORTED` (for example, too
   few successes) or `CANCELED`. The result carries the run folder and W&B URL; the Reward
   tab lists the new run after **Refresh**.

## A Reward tab prediction

1. The Reward tab sends an `EvaluateReward` request with the run picked above each graph and
   the recording being played to `/<method>_inference/evaluate`.
2. [`RewardInferenceServer`](../reward_models/inference_node.py#L38) loads the run's
   `model.pt` into `<method>.Model`. It keeps the model until a newer `model.pt` replaces
   it. It then loads the recording's Sparsh-skin episode at the run's step rate. A run
   trained on camera frames by an earlier version of this package is refused with a message
   to retrain.
3. The model returns the reward per step and its terms: `progress` and `discriminator` for
   Rank2Reward, `progress` and `stage` for SARM, `global` and `local` for Coupled Local Global.
   The node logs the evaluation to its W&B inference run (when its `wandb` parameter is on)
   and answers.
4. The GUI plots the reward (white) and its terms on the recording's time axis, under the
   play bar's cursor; SARM's stages are shaded on its graph and on the play bar.

## Design choices that apply to both methods

- **The only observations are the Sparsh-skin `forces_local` and `positions`** of the 368
  taxels. Both papers learn rewards from images; here the taxel state takes the image's
  place, using the same preprocessing as the LEQ_DV3 world model. Coupled Local Global's
  local dynamics also takes the sim joint targets as its action input.
- **One step is one Sparsh-skin step at the step rate**: 25 Hz by default, every 4th of the
  episode's 100 Hz steps, always including the last (`terminal`) step.
- **Failed recordings stand in for policy data.** Both papers compare demonstrations with
  what a policy does. There is no policy yet, so failed Play on hand attempts are used as
  the examples a reward should score low.
- **Validation is by recording, stratified by label**, so the metrics show how a reward
  scores attempts it has never seen.
