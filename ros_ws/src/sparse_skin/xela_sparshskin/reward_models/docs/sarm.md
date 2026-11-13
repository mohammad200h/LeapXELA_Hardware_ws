# SARM

Code: [sarm.py](../reward_models/sarm.py) and [sarm_failures.py](../reward_models/sarm_failures.py).
Paper: Chen et al., *SARM: Stage-Aware Reward Modeling for Long Horizon Robot Manipulation*,
ICLR 2026 (arXiv 2509.25358). Also in LeRobot as `--policy.type=sarm`.

The paper encodes **camera frames** (and joint states) with frozen CLIP. Here each step is a
`Clip.obs`: the **Sparsh-skin state** of the 368 taxels or the **joint state**, depending on
`TrainConfig.modality` (see [data.md](data.md)), through the package's
[`StateEncoder`](../reward_models/networks.py#L13).

There are two methods:

| Method | Trained on | Failed recordings |
| --- | --- | --- |
| `sarm` | Successful recordings only, as in the paper | Not used. Rewind augmentation is the only source of "progress going down". |
| `sarm_failures` | Successes and failures | Labelled with **flat progress in the press stage**: pressing without a click earns nothing. |

Neither is in the GUI's train/inference nodes yet. They run through the offline comparison
script, [compare.py](../reward_models/compare.py) (`--methods sarm sarm_failures`).

## The idea

Rank2Reward and TimeRewarder label progress by **time**: a step 40% of the way through a
recording is 40% done. For the pen, that is misleading. A slow success spends most of its time
gripping, and a fast one most of its time pressing, so the same hand state gets very different
labels.

SARM labels progress by **stage** instead. It asks two questions: which stage is the hand in,
and how far through that stage is it?

## Stages and labels

The stages are the same as in `reds` ([`stages`](../reward_models/sarm.py)):

| k | Stage | Steps |
| --- | --- | --- |
| 0 | grip | From `episode_start` to the thumb's first move (`Clip.thumb_onset`: a thumb joint more than 0.05 rad from where it started) |
| 1 | press | From the thumb's first move on |
| 2 | click | The last `click_window_s = 1.0` s of a **successful** recording |

[`stage_priors`](../reward_models/sarm.py) sets `alpha_k`, the mean share of a successful
training recording spent in stage k (the paper's Eq. 1). Their cumulative sums are
`P_k = alpha_0 + … + alpha_k`, with `P_-1 = 0`. They are logged as `prior/grip`, `prior/press`
and `prior/click`, and saved in the checkpoint.

Within a stage that runs from step `s` to step `e`, `tau_t = (t − s) / (e − s)`. The progress
label is the paper's Eq. 2:

```
y_t = P_{k-1} + alpha_k · tau_t        in [0, 1]
```

A success crosses `P_0` exactly when its thumb starts to move, however long it gripped first.

In `sarm_failures`, a failed recording's grip is labelled as in a success. Every one of its
press steps gets `tau = 0`: it stays at `P_0`, the start of the press.

## The network

[`SARMNet`](../reward_models/sarm.py):

```
window: the episode's first step + `frames` (8) steps `frame_gap` (5) apart ending at t
  (4 s at 10 Hz; the paper: 8 frames 1 s apart)
  ─▶ StateEncoder per step                      (B, 9, 256)
  ─▶ + learned bias on the first step only       (no other positional encoding, as in the paper)
  ─▶ TransformerEncoder, `layers` 2, `heads` 4   (the paper: 8 layers, 768 wide, 12 heads)
  ─▶ per step:  stage head  MLP → 3 logits
                tau head    MLP(feature ⊕ stage embedding) → sigmoid
```

The network is smaller than the paper's because there are about 145 training successes, not
hundreds of hours of video.

## Training step

Each step draws `batch_size` recordings, weighted by length, and a random step `t` in each.
It builds the window ending at `t`:

1. **Rewind** ([`rewind`](../reward_models/sarm.py)), with `rewind_prob = 0.5`: the last
   1–`rewind_max` (4) steps of the window are replaced by steps going **backwards** from the
   last one kept. Their labels are their own, lower progress values, so the model learns that
   progress can fall. This is the paper's augmentation, taken from ReWiND.
2. **Losses** on every step of the window except the first (the anchor):
   - `stage_ce`: cross-entropy of the stage head against k;
   - `tau_mse`: MSE of the tau head against `tau`, given the **true** stage. The paper
     doesn't say which stage it conditions on during training; at inference it uses the
     predicted one.

Total: `loss = stage_ce + tau_mse`. AdamW (weight decay 1e-3, the paper's), gradients clipped
at 1.0, Gaussian input noise `augment_noise = 0.05`.

## Progress and reward

At step `t`, [`score_clip`](../reward_models/sarm.py) takes the window ending at `t` and
predicts the stage `k̂` (argmax). It then predicts `tau` given `k̂`:

```
phi_t   = P_{k̂-1} + alpha_k̂ · tau_hat           (progress, the paper's Eq. 4)
reward_t = phi_t − phi_{t−1}                       (0 at the first step)
```

The reward is the **progress made** in the step: the paper's reward for policy learning
(`phi(t+Δ) − phi(t)`, Eq. 6) with Δ = one step. Summed over an episode it is the progress
the episode made, so stalling in the press earns nothing.

Setting `reward = "progress"` returns `phi_t` itself instead. That pays for *reaching* a stage
early and staying there, which is the trap REDS fell into on this data (see the comparison
report).

The model returns the reward and two terms: `progress` (`phi`) and `stage` (`k̂`).

## Validation metrics

| Metric | What it measures | Good |
| --- | --- | --- |
| `val/spearman` | **Main metric** (best epoch saved). Rank correlation of `phi` with time, mean over successful recordings. | → 1 |
| `val/stage_acc` | Share of steps whose predicted stage matches the label. | → 1 |
| `val/progress_mae` | Mean `abs(phi − y)` on successful recordings. Shown as the validation loss. | ↓ |
| `val/return_auc`, `val/final_progress_*`, … | The shared metrics of `common.summary_metrics`. | |

One caution about `return_auc` with this reward: the **mean** reward per step is the progress
made divided by the episode's length. Failures are longer (median 25 s against 18 s), so this
metric partly measures length. The final-progress metrics don't have that problem.

## Settings

`DEFAULTS` in `sarm.py` (`sarm_failures.py` changes only `failures`). Override any of them
through `TrainConfig.extra`.

| Setting | Default | Meaning |
| --- | --- | --- |
| `failures` | `"exclude"` (`sarm`), `"flat"` (`sarm_failures`) | Whether failed recordings are trained on, and how |
| `frames`, `frame_gap` | 8, 5 | Window: the first step + 8 steps 0.5 s apart at 10 Hz |
| `click_window_s` | 1.0 | Length of the click stage at the end of a success |
| `rewind_prob`, `rewind_max` | 0.5, 4 | Rewind augmentation |
| `layers`, `heads` | 2, 4 | Transformer size |
| `reward` | `"delta"` | `"delta"` (`phi_t − phi_{t−1}`) or `"progress"` (`phi_t`) |
| `augment_noise`, `plot_recordings` | 0.05, 6 | As in the other methods |

## Results on the pen data

From `compare.py` (30 epochs, 3 seeds, 10 Hz; full write-up in
`LEQ_DV3/eval/mechanical_pen/reports/reward_models/index.html`):

| Method | Input | Progress made before the end (AUC) | Progress vs time | Stage accuracy |
| --- | --- | --- | --- | --- |
| `sarm` | Sparsh-skin | 0.99 (1.00 in recordings 211+) | 0.999 | 0.89 |
| `sarm` | proprio | 0.99 | 0.997 | |
| `sarm_failures` | Sparsh-skin | 0.97 | 0.994 | |
| `sarm_failures` | proprio | 0.88 | 0.987 | |

The paper's version (`sarm`) is the best reward model in the comparison on this length-free
score. Learned stage shares: grip 0.70, press 0.24, click 0.06. A failure's progress rises
faster than a success's early on (failures start pressing sooner), levels off about
three-quarters of the way through and falls back over roughly the last 15%. A discounted policy could be paid for rushing into the press, so check that when
training a policy on this reward.

## Differences from the paper

- Sparsh-skin or joint state through the package encoder, instead of frozen CLIP on camera
  frames plus joint state. The Sparsh-skin model doesn't also see the joints, so all methods
  in the comparison get the same input.
- A smaller transformer, and the same epochs and learning rate as the other methods
  (30 × 200 steps, 3e-4) instead of 2 epochs at 5e-5.
- Stage boundaries come from the thumb's joint motion and the end of the recording, not from
  human annotation.
- `sarm_failures` is our addition. The paper excludes demonstrations with mistakes.
- Reward-aligned behaviour cloning (the paper's use of the reward) is not implemented. The
  reward here is meant for the DV3 world model's policy training.
