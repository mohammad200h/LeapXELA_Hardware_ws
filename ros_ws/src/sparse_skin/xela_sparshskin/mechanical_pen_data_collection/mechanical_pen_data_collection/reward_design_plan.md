# Reward design plan

This is the plan for the rewards behind the **Reward Design** tab of
[record_demonstration.py](record_demonstration.py) (`RewardDesignTab`). The tab has three
sub-tabs: **Manual**, **Reward2Rank** and **Coupled Local Global RL**. This file says what
each computes, what data it uses, and the order to build them in.

## Status

| Part | State |
| --- | --- |
| Manual | Not coded yet (section 2). |
| Reward2Rank | Built in the `reward_models` package (`rank2reward.py`). It trains through the action `/rank2reward_train/train` and serves inference at `/rank2reward_inference/evaluate`. The GUI has Train and Visualize tabs for it. |
| Coupled Local Global | Only its reward models are built: the global reward head, plus the local recurrent model with its reward and one-step dynamics heads (`coupled_local_global.py`). They use the same action / service / GUI as Reward2Rank. The world models and the first-order RL are still to do. |

The nodes start with the app (`launch_record_demonstration.py`, `reward_models:=false` to
leave them out). Both learned rewards use only the Sparsh-skin episodes'
`flex_taxel_fk/forces_local` and `positions`, with no camera images; see
`reward_models/docs/data.md`. Runs are saved to
`<recordings>/reward_models/<method>/<run>/` and logged to W&B, set up the same way as LEQ_DV3.
Each run folder holds `config.json`, `metrics.jsonl`, `model.pt` and `eval.json`.

Still open from the papers: Rank2Reward's exact reward formula and losses (arXiv
2404.14735). The code uses log progress plus the discriminator logit, with a 0/1 anchor on
progress. Also open: how the paper's global and local rewards combine in the policy loss.

References:

- Rank2Reward: D. Yang, D. Tjia, J. Berg, D. Damen, P. Agrawal, A. Gupta, *Rank2Reward:
  Learning Shaped Reward Functions from Passive Video*, ICRA 2024.
  <https://rank2reward.github.io/> (paper: arXiv 2404.14735).
- Coupled Local Global: J. Amigo, R. Khorrambakht, N. Mansard, L. Righetti, *Coupled Local and
  Global World Models for Efficient First Order RL*, CoRL 2026.
  <https://arxiv.org/abs/2602.06219> (project page: <https://coupled-global-local-wm-rl.pages.dev/>).

---

## 1. Goal and the data we already have

The task: Index, Middle and Ring hold the pen while the Thumb presses it until it clicks. A
reward should be high when the pen clicks, the grip holds and nothing slips, and low otherwise.

The app already records everything a reward needs:

| Source | What it gives |
| --- | --- |
| Takes, `<demo_dir>/fingers/<finger>/<name>.npz` | `t`, joints, `sim_hand_q`, `xela` (L, T, 3) with `xela_baseline`, camera `video` / `video_t`, pen box, and `events` (`episode_start`, `terminal`, `maintain_touch`, `click_press`, ...) |
| Play on hand recordings and `<box>_<n>.label.json` | success / fail, and the click press outcome: clicked / no click / kept sliding / no contact / other press |
| Click detector, `click_topic` (Int32) | 1 while a click is heard |
| `slip_detection.SlipDetector` | Slips on a fingertip from its live taxels |
| Fingertip taxel magnitudes | Contact force per finger: the change from the baseline (Baseline tab) divided by `counts_per_unit` |

Every reward will implement one interface so that all three sub-tabs can plot it the same
way (see section 5).

## 2. Manual

A hand-weighted sum of terms. It needs no training, so it is built first and becomes the
baseline the learned rewards are compared against.

Terms (each can be turned on or off and given a weight):

1. **Click**: a sparse bonus at the first click heard (`click_topic`), only once per episode.
2. **Thumb force**: −|F_thumb − F_target| while the Thumb is pressing, with the target taken
   from the click press settings.
3. **Grip**: a bonus while Index / Middle / Ring stay inside the `maintain_touch` force band,
   and a penalty when one loses contact.
4. **Slip**: a penalty for each slip `SlipDetector` reports.
5. **Smoothness**: a penalty on the joint command rate (Δq / Δt).
6. **Terminal**: ±1 at the end of the episode from the recording's success / fail label.

UI to come: a table of term / enable / weight, a recording picker, and a plot of each term
and of the total reward over the recording, with the events marked. The weights are saved
with the other settings, using a dataclass and `apply_saved_hold_settings`, the same way as
`AvoidSlipSettings`.

## 3. Reward2Rank

The paper learns a progress reward from action-free demonstration video. Here the
observation is the Sparsh-skin taxel state instead of a frame.

- **Data** (as built): the Sparsh-skin episodes (`forces_local` and `positions` of the 368
  taxels) between `episode_start` and `terminal`, at 25 Hz by default. The ranker trains on
  the successful ones; the failed ones are the discriminator's negatives.
- **Ranking net** R(o): two steps o_i, o_j are sampled from the same demonstration with
  i < j, and a Bradley–Terry / logistic loss is trained so that R ranks o_j above o_i.
  R's sigmoid output is the progress, in [0, 1].
- **Discriminator** D(o): it separates demonstration frames from policy frames. This keeps
  the policy from reaching states the ranker scores high but that no demonstration visits.
- **RL reward**: log-progress plus the discriminator term.
- **Open**: check the exact losses and the reward formula against the paper
  (arXiv 2404.14735) before coding. This includes whether the goal-conditioned variant is
  needed for us (one goal, the click, so probably not).

Steps:

1. A dataset builder that turns takes and recordings into frame sequences with progress
   indices.
2. A training script, offline and outside the GUI.
3. An evaluation: plot the predicted progress over held-out successes and over failures.
   It should rise on successes and stall on "no click" / "kept sliding".
4. The GUI page: a model path, Train (in the background), and the reward overlaid on a
   picked recording.

## 4. Coupled Local Global RL

This is first-order (DMO-SAPO) policy optimisation through learned world models:

- A **global** model, an image-space diffusion world model, rolls the policy forward. A
  global reward head scores each frame.
- A **local** model, a DreamerV3 RSSM with its own reward head, is used for the backward
  pass. Its Jacobians, evaluated at re-encodings of the global model's frames, stand in for
  the global model's. It is fine-tuned during RL with the global reward predictions as
  targets.

For us:

- **Global reward head**: a per-step model trained on the recordings' success / fail labels
  and the click / `terminal` events. Steps at the click get the goal label.
- **Observations**: the Sparsh-skin `forces_local` and `positions` take the place of the
  paper's images; the local dynamics also takes the sim joint targets as its action.
- **Data**: unstructured play on the hand, plus "patching" rounds in which a policy that
  exploits model or reward errors is run on the hand to collect targeted data. The paper
  uses 4–21 h of data.
- **Starting hyperparameters** (from the paper): horizon H = 16, γ = 0.99, λ = 0.95, an
  ensemble of 10 critics, AdamW, actor LR 2e-3, critic LR 5e-4.
- **Missing in this repo**: the world models, the training infrastructure (GPU, data
  pipeline) and a policy interface to the hand. This is the largest piece of work.
- **Open**: check the reward-head architecture and how the global and local rewards relate in
  the policy loss against the PDF and the project page.

## 5. Order of work and shared pieces

1. A `reward_design.py` module with a `RewardFn` interface:
   `evaluate(recording) -> (t, r)` (plus per-term values when there are any), and loaders
   for takes and recordings with their labels and events.
2. Manual: its terms, its settings and its plot on the Manual sub-tab.
3. Reward2Rank: the dataset, the training, the evaluation and its sub-tab.
4. Coupled Local Global RL: the reward head first (it can be checked on the recordings
   alone), then the world models and the RL.

All three sub-tabs share one view: pick a recording, then plot its reward over time with its
events and label. That lets the learned rewards be compared to the Manual one on the same
recordings.
