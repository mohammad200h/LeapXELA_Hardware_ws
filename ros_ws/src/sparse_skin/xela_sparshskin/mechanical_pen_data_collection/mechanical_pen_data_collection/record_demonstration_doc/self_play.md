# Self-play with a pen

The **Self-play** tab lets a play policy move the hand with a pen in it, on its own, while
everything is recorded. It works like the self-play stage of *Dexterity from Supervised Play*
(the `play_policy` repo): there is no goal and no reward, only a policy that imitates the pen
demonstrations plus sampling noise to explore around them. The segments are data for a world
model or for the next policy.

The policy sees only the **Sparsh-skin state**: for each of the 368 taxels, the Xela force
(baseline subtracted, as in the Sparsh-skin episodes) and its FK position.

## 1. Train the policy

Run the Processing tab's Sparsh-skin transform at **30 Hz** first. That rate is the policy's
step rate and the tab's command rate. Then:

```bash
source ros_ws/install/setup.bash
export PYTHONPATH=ros_ws/src/sparse_skin/xela_sparshskin/reward_models:ros_ws/src/sparse_skin/xela_sparshskin/mechanical_pen_data_collection:$PYTHONPATH
cd play_policy
python -m play_policy.train --dataset leap_sparsh \
    --recordings_dir ../ros_ws/demonstrations/compose_playbacks --hz 30
```

- **Data:** every Play on hand episode, successes and failures, split by recording.
- **Chunks:** each chunk is 96 steps (3.2 s), and 24 of them (0.8 s) are run before the
  policy is asked again.
- **Output:** `runs/play_policy/<time>/` holds `ckpt_best.pt` and `leap_meta.json`. The JSON
  file has the start poses, the joint order, the step rate, the baseline the episodes used, and
  the range of the commands the episodes sent.

## 2. Run it

`launch_record_demonstration.py` starts `play_policy_node` (`play_policy:=true`). The node loads
the newest leap_sparsh checkpoint, or `play_policy_checkpoint:=<path>`. In the **Self-play** tab:

| Key | What it does |
|---|---|
| Space | Idle → the hand moves to a start pose (the first command of a random training episode). Put the pen in. |
| Space | Start self-play. Press again to pause or resume; while paused the hand holds. |
| S / F | End the segment as success / failure. It is saved and the hand opens. Re-seat the pen. |
| D | Discard the segment. The hand opens. |
| Esc | Hold (pause). |

Every 0.8 s, `play_policy_node` samples a chunk from the newest Xela reading and joint state.
This takes about 30 ms. The tab streams the chunk with every joint stiff. Two settings control
exploration:

- **eta:** 1 = stochastic sampling, 0 = deterministic.
- **Initial noise:** DSP uses 1.1.

**Sim only** sends the commands to the MuJoCo sim and saves nothing. Use it as a dry run.

## Safety

Nothing else limits the hand's commands, so the tab clips every command two ways:

- **To the range of commands the training episodes sent** (`leap_meta.json`). The joint
  limits in joint_config.json are not used: the demonstrations exceed them on th_ipl, if_pip
  and mf_pip, and the `*_rot` limits are reversed.
- **To the Max joint speed** (1.5 rad/s, about the 99th percentile of the demonstrations).

A segment pauses when the policy cannot be asked: no node, or a Xela or leap_state reading older
than 0.3 s. It ends as a truncated failure at the length limit. Leaving the tab stops
self-play and makes the hand compliant again.

## What is saved

Segments go to `<demo_dir>/self_play/self_play_<n>.npz`, in the same format as a Play on hand
recording: commands, joint states, raw Xela, clicks, camera and audio. Each `.npz` has a
`.label.json` with the label and confirmed `episode_start` / `terminal` events. The metadata
holds the checkpoint, the sampling settings, the pauses, every chunk's inference time and
state age, and how many steps were clipped or speed-limited.

The folder is kept apart from the demonstrations, so nothing trains on it by accident. Run
the Sparsh-skin transform on it (Processing tab, or `sparsh_processing.write_dataset`) and
`reward_models.data.load_clips(<demo_dir>/self_play, ...)` reads it like the demonstrations.
