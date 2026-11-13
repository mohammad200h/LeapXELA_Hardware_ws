# Coupled Local Global: the reward models

Code: [coupled_local_global.py](../reward_models/coupled_local_global.py). Paper: Amigo,
Khorrambakht, Mansard, Righetti, *Coupled Local and Global World Models for Efficient First
Order RL*, CoRL 2026 ([arXiv](https://arxiv.org/abs/2602.06219)).

The paper's models work on **images**. Here every state is a **Sparsh-skin state** instead:
the `forces_local` and FK `positions` of the 368 taxels (see [data.md](data.md)).

## The method, and the part built here

In the paper a policy is trained with **first-order** gradients: the gradient of the reward
flows back through a learned world model into the policy. Two world models share the work:

- a large **global** model (a diffusion model) rolls the policy forward and gives realistic
  states. A **global reward head** scores those states;
- a small **local** model (a DreamerV3-style recurrent model) re-encodes each state of the
  global rollout. Its Jacobians stand in for the global model's in the backward pass, because
  the diffusion model is too heavy to differentiate through. It has its own reward head,
  fine-tuned to match the global reward.

**What this package builds:** the two **reward** parts. That is the global reward head, and
the local model with its reward head and a one-step dynamics head. **What it does not build:**
the global world model, and the policy optimisation (DMO-SAPO) that would use them. Those need
far more data and compute, and a policy running on the hand.

## Targets: what a step is worth

[`step_targets`](../reward_models/coupled_local_global.py#L101) labels each step the way the
paper labels its Push Cube / G1 reward data:

| Step | Target |
| --- | --- |
| In a successful recording, in the last `goal_window_s = 0.5` s before `terminal` (the click) | `goal_reward = 10` (the goal, as in the paper) |
| In a successful recording, earlier | `demo_reward = 1` (in the demonstration distribution) |
| In a failed recording | 0 |

## The global reward

[`GlobalReward`](../reward_models/coupled_local_global.py#L67): a `StateEncoder` (the same
z-score and MLP as Rank2Reward, see [rank2reward.md](rank2reward.md)) and an MLP with **255
outputs**.

The outputs are DreamerV3's **symlog two-hot** head ([`TwoHot`](../reward_models/networks.py#L63)).
The value is predicted as a distribution over 255 bins spread evenly in symlog space over
[−20, 20]. The loss is cross-entropy with the target spread over its two nearest bins. The
prediction is the expected bin value, mapped back with `symexp`. This head handles a target
of 10 on a few steps and 0–1 on the rest without the large values dominating, and it is what
the paper uses for its local reward head.

## The local model

[`LocalModel`](../reward_models/coupled_local_global.py#L77):

```
obs ─▶ encoder e_t (smaller StateEncoder: 2208→256→128)
(e_t, a_{t−1}) ─▶ GRUCell(256) ─▶ h_t            a: sim joint targets, standardised
latent l_t = (h_t, e_t)
  ├─▶ reward head R(l_t)        255-bin two-hot
  └─▶ dynamics head (l_t, a_t) ─▶ ê_{t+1}
```

The actions `a` are the episode's 16 `actions` (sim joint targets) at each step, standardised
with the training set's mean and std, which are saved in `model.pt`. They are **not** an
observation: a world model predicts the next state from the current state *and the action
taken*, so the local dynamics needs them. The reward heads see only `forces_local` and
`positions`.

## Training step

[`train`](../reward_models/coupled_local_global.py#L107), per step, with `B = batch_size`:

1. **Global loss.** `B` steps from all training recordings (successes and failures), two-hot
   loss against `step_targets`.
2. **Local losses**, on `B/4` windows of `seq_len = 16` consecutive steps (the paper's horizon
   H; 0.64 s at 25 Hz). The GRU runs over each window from h = 0:
   - `local_label_loss`: two-hot loss of `R(l_t)` against the step targets, as the paper
     pretrains its local reward on the dataset's labels;
   - `local_coupling_loss` (weight `coupling_weight = 1.0`): two-hot loss of `R(l_t)` against
     the **global reward's prediction** for the same step, with no gradient into the global
     model. This is the coupling: in the paper the local reward is fine-tuned on the global
     reward's predictions during RL;
   - `dyn_loss` (weight `dyn_weight = 1.0`): MSE between the dynamics head's prediction and
     the next step's encoding `e_{t+1}`, with no gradient into the target. The local model
     only needs to be accurate one step ahead, because its Jacobians are evaluated at the
     global model's states.

The four losses are summed and optimised together with AdamW (lr from the Train tab, weight
decay 1e-4, gradients clipped at 1.0, Gaussian input noise `augment_noise = 0.05`).
Recordings shorter than `seq_len + 1` steps are left out of training.

## The reward

The service returns **`reward = global`**, the reward the forward rollouts would score with.
It has two terms:

- `global`: the global reward per step;
- `local`: the local model run over the whole recording from its first step, which shows how
  closely it follows the global one.

## Validation metrics

[`evaluate`](../reward_models/coupled_local_global.py#L196):

| Metric | What it measures | Good |
| --- | --- | --- |
| `val/return_auc_global` | **Main metric** (best epoch saved). How well the episode's mean global reward separates successes from failures (ROC AUC). | → 1 |
| `val/return_auc_local` | The same for the local reward. | → 1 |
| `val/goal_auc` | How well the global reward picks out goal steps (last 0.5 s of a success) from all others. | → 1 |
| `val/local_global_corr` | Correlation of local and global reward over all validation steps: how tightly they are coupled. | → 1 |
| `val/global_loss` | MSE of the global reward to the targets. Shown as the validation loss. | ↓ |
| `val/dyn_loss` | One-step dynamics error of the local model. | ↓ |
| `val/return_success` / `_failure` | Mean global reward over an episode. | Success above failure |

A good run has a high `return_auc_global` and `goal_auc`, so the reward knows success and the
goal moment, together with a high `local_global_corr`, so the local model's gradients would
point the same way as the reward the rollouts score.

W&B also gets global and local reward curves for up to 6 validation recordings each epoch.

## Settings

| Setting | Default | Where |
| --- | --- | --- |
| epochs, batch size, learning rate, validation share, step rate, seed | 30, 64, 3e-4, 0.2, 25 Hz, 0 | Train tab |
| `steps_per_epoch` | 200 | Training node parameter |
| `demo_reward`, `goal_reward`, `goal_window_s` | 1, 10, 0.5 s | `DEFAULTS` in `coupled_local_global.py` |
| `seq_len`, `coupling_weight`, `dyn_weight`, `local_hidden`, `augment_noise` | 16, 1.0, 1.0, 256, 0.05 | `DEFAULTS` |
