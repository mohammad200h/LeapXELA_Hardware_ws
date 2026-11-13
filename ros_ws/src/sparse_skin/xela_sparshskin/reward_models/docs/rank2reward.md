# Rank2Reward

Code: [rank2reward.py](../reward_models/rank2reward.py). Paper: Yang, Tjia, Berg, Damen,
Agrawal, Gupta, *Rank2Reward: Learning Shaped Reward Functions from Passive Video*, ICRA 2024
([site](https://rank2reward.github.io/), arXiv 2404.14735).

The paper ranks **video frames**. Here each step is a **Sparsh-skin state** instead: the
`forces_local` and FK `positions` of the 368 taxels (see [data.md](data.md)). The method is
otherwise the same.

## The idea

A successful demonstration makes progress: each step is a little further into the task than
the one before it. If a network learns to say **which of two steps comes later**, its score
measures progress. A reward built from that score is **shaped**: it rises steadily through
the task instead of paying out only at the click.

A progress score alone can be fooled. A policy might reach a state the ranker scores high but
that no demonstration ever visits. A **discriminator** that recognises demonstration-like
states guards against that.

## The networks

There are two networks. Each is a [`StateScore`](../reward_models/rank2reward.py#L60): its
own [`StateEncoder`](../reward_models/networks.py#L13) followed by an MLP with one output.
They share no weights.

```
obs (368 taxels × [force x,y,z, position x,y,z])
  ─▶ z-score per channel (stats stored in the encoder), clip ±20
  ─▶ flatten in FK order (2208)
  ─▶ Linear 2208→512, LayerNorm, SiLU ─▶ Linear 512→256, LayerNorm, SiLU
  ─▶ MLP 256→256→256 ─▶ 1 logit
```

Flattening in FK order means each input position is always the same taxel, so the network
can learn which taxels matter (for example the Thumb's tip at the click).

- **Ranker** `u(o)`: a logit per step. `progress p(o) = sigmoid(u(o))`.
- **Discriminator** `d(o)`: a logit per step. `D(o) = sigmoid(d(o))` is the probability that
  the step comes from a successful recording.

## Training step

[`train`](../reward_models/rank2reward.py#L90) runs `steps_per_epoch` steps per epoch. Each
step draws a batch of `B = batch_size`:

1. **Ranking loss.** Pick `B` successful recordings, weighted by length. From each, pick two
   different steps `i` and `j`. Then
   `rank_loss = BCE(u(o_j) − u(o_i), [j > i])`.
   This is the Bradley–Terry / logistic ranking loss: it pushes a later step's score above an
   earlier one's. Only **successful** recordings are used, because a failed attempt has no
   reliable order to learn.
2. **Anchor loss** (our addition, weight `anchor_weight = 0.1`). The ranking loss sets only
   differences between scores, so `sigmoid(u)` could sit anywhere. This loss pulls the first
   step of each picked recording towards `p = 0` and the last (the click) towards `p = 1`, so
   `p` reads as a fraction of the task done.
3. **Discriminator loss.** `B` steps from successful recordings with label 1 and `B` steps
   from failed recordings with label 0, `BCE`. In the paper the negatives are the policy's own
   states during RL; offline, the failed attempts stand in for them. If the training set has
   no failures, this loss is skipped and the reward uses progress only.

Total: `loss = rank_loss + anchor_weight · anchor_loss + disc_loss_weight · disc_loss`.
AdamW optimises it (weight decay 1e-4, gradients clipped at 1.0). As augmentation, Gaussian
noise (std `augment_noise = 0.05`) is added to the z-scored inputs during training.

## The reward

[`reward_terms`](../reward_models/rank2reward.py#L76):

```
reward(o) = log p(o) + disc_weight · d(o)        (d = log D − log(1 − D), the logit)
```

- `log p` is about 0 near the end of a success and very negative at the start, so it rises
  through the task;
- the discriminator logit adds to states that look like successes and subtracts from states
  that look like failures (`disc_weight = 1.0`).

This is the formula the code uses. The paper's exact formula and weights still need to be
checked against arXiv 2404.14735; this is listed in `reward_design_plan.md`.

The inference service returns the reward and two terms: `progress` (`p`) and `discriminator`
(`D`).

## Validation metrics

After each epoch, [`evaluate`](../reward_models/rank2reward.py#L164) scores every validation
recording:

| Metric | What it measures | Good |
| --- | --- | --- |
| `val/rank_acc` | **Main metric** (best epoch saved). Share of random step pairs from successful recordings that the ranker puts in the right order. | → 1. 0.5 is chance. |
| `val/rank_loss` | The ranking loss on those pairs. Shown as the validation loss. | ↓ |
| `val/spearman` | Rank correlation of the ranker's score with time, mean over successful recordings. | → 1 |
| `val/final_progress_success` / `_failure` | Mean progress at the last step. | Success near 1; failure lower |
| `val/disc_auc` | How well `D` separates success steps from failure steps (ROC AUC). | → 1 |
| `val/return_success` / `_failure` | Mean reward over an episode. | Success above failure |
| `val/return_auc` | How well the episode's mean reward separates successes from failures. | → 1 |

`rank_acc` and `spearman` say whether the progress is right. `disc_auc` and `return_auc` say
whether the reward tells a good attempt from a bad one. A reward that scores well on the
first two and badly on the last two is shaped, but would pay a failed attempt as much as a
success.

W&B also gets, each epoch, progress and reward curves for up to 6 validation recordings
(`plot_recordings`), half successes and half failures.

## Settings

| Setting | Default | Where |
| --- | --- | --- |
| epochs, batch size, learning rate, validation share, step rate, seed | 30, 64, 3e-4, 0.2, 25 Hz, 0 | Train tab (the action goal) |
| `steps_per_epoch` | 200 | Training node parameter |
| `anchor_weight`, `disc_loss_weight`, `disc_weight`, `augment_noise`, `val_pairs`, `plot_recordings` | 0.1, 1.0, 1.0, 0.05, 4000, 6 | `DEFAULTS` in `rank2reward.py` |
