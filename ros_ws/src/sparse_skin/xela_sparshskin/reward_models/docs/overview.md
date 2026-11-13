# How reward_models works

This page follows one press of **Train** and one press of **Evaluate** through the code. The
other pages go deeper into each step.

## The pieces

```
record_demonstration (GUI)                          reward_models nodes
┌──────────────────────────────┐   TrainReward    ┌──────────────────────────────┐
│ Reward Design ▸ <method>     │ ───── goal ────▶ │ <method>_train               │
│   Train tab                  │ ◀── feedback ─── │   run_training()             │
│                              │ ◀─── result ──── │     data.load_clips()        │
│                              │                  │     <method>.train()         │
│   Visualize tab              │                  │   ──▶ run folder + W&B       │
│     reads the run folder ◀───┼──────────────────┼── <recordings>/reward_models │
│     Evaluate ───────────────▶│  EvaluateReward  │ <method>_inference           │
│                       ◀──────┼───── response ── │   Model(run)(clip) ──▶ W&B   │
└──────────────────────────────┘                  └──────────────────────────────┘
```

`<method>` is `rank2reward` or `coupled_local_global`. `launch_record_demonstration.py`
starts all four nodes, so they are running whenever the app is.

More methods are available to the offline comparison script
[compare.py](../reward_models/compare.py), but not yet to the GUI nodes: `timerewarder`,
`progressor`, `reds`, and SARM as `sarm` and `sarm_failures` ([sarm.md](sarm.md)). The script
trains every method on Sparsh-skin and on joint state for several seeds, then scores them on
the same held-out recordings:

```
python3 -m reward_models.compare --recordings-dir <recordings> [--methods …] [--seeds 0 1 2]
```

## Pressing Train

1. **The GUI sends a goal.** `RewardTrainPanel._train_or_cancel` in `record_demonstration.py`
   fills a `TrainReward` goal from the form: recordings folder, epochs, batch size, learning
   rate, validation share, step rate, seed, and the W&B settings. It sends
   the goal to `/<method>_train/train` with the action client the GUI node made at start-up
   (`LeapStateListener.reward_train`).
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
   metric. The GUI plots them.
8. **The result comes back.** The action ends with `SUCCEEDED`, `ABORTED` (for example, too
   few successes) or `CANCELED`. The result carries the run folder and W&B URL, and the
   Visualize tab then selects the new run.

## Pressing Evaluate

1. The Visualize tab sends an `EvaluateReward` request with the selected run's folder and
   the chosen recording to `/<method>_inference/evaluate`.
2. [`RewardInferenceServer`](../reward_models/inference_node.py#L38) loads the run's
   `model.pt` into `<method>.Model`. It keeps the model until a newer `model.pt` replaces
   it. It then loads the recording's Sparsh-skin episode at the run's step rate. A run
   trained on camera frames by an earlier version of this package is refused with a message
   to retrain.
3. The model returns the reward per step and its terms: `progress` and `discriminator` for
   Rank2Reward, `global` and `local` for Coupled Local Global. The node logs the evaluation
   to its W&B inference run and answers.
4. The GUI plots the reward (white) and its terms over time from `episode_start`.

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
