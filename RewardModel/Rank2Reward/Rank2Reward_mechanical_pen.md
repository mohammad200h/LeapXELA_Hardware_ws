# Rank2Reward on the mechanical pen

How Rank2Reward works, how it was trained on the mechanical-pen demonstrations, and what it learned.

- **Paper:** Yang, Tjia, Berg, Damen, Agrawal, Gupta. *Rank2Reward: Learning Shaped Reward Functions from Passive Video.* ICRA 2024. [arXiv 2404.14735](https://arxiv.org/abs/2404.14735). The PDF is in this folder.
- **Code here:** [rank2reward.py](../../ros_ws/src/sparse_skin/xela_sparshskin/reward_models/reward_models/rank2reward.py), with the package doc [docs/rank2reward.md](../../ros_ws/src/sparse_skin/xela_sparshskin/reward_models/docs/rank2reward.md).
- **Experiment:** `ros_ws/demonstrations/compose_playbacks/reward_models/comparison/run_20261112_1020/`, run 12–13 Nov 2026.
- **Full comparison with the other methods:** `LEQ_DV3/eval/mechanical_pen/reports/reward_models/index.html`.
- **Companion report:** [SARM on the mechanical pen](../SARM/SARM_mechanical_pen.md).

## Summary

- Rank2Reward learns **two separate scores**:
  - a **ranker**, which says how far through the task a state is, trained only on successful recordings;
  - a **discriminator**, which says whether a state looks like a success or a failure, trained on both.
- **Progress through a success is learned almost perfectly.** On held-out successes, the ranker puts 99.7% of step pairs in the right time order.
- **The progress term barely tells successes from failures.** The ranker never sees a failure. A failed press looks to it like a nearly finished success until the last step or two. On progress made before the final second, a success beats a failure only **70%** of the time on Sparsh-skin (90% on proprio).
- **The discriminator does almost all the separating.** Some of that comes from cues present before the task starts: at step 0 it already ranks a success above a failure 79% of the time.
- **Overall it is the runner-up to SARM** in a comparison of seven reward models.

## 1. How the algorithm works

### The assumption

A demonstration makes steady progress, so a later state is closer to the goal than an earlier one. Rank2Reward learns a score that orders states in time. It then uses that score as a dense reward.

### The ranker: progress from time order

The ranker is a network $u_\theta(s)$ that gives each state one number. It is trained on **pairs of states from the same successful demonstration** with a Bradley–Terry (logistic) loss: the later state should score higher.

$$
p(s_j \succ s_i) = \sigma\big(u_\theta(s_j) - u_\theta(s_i)\big), \qquad \mathcal L_\text{rank} = \text{BCE}\big(u_\theta(s_j) - u_\theta(s_i),\ [\,j > i\,]\big)
$$

Progress is $p(s) = \sigma(u_\theta(s))$. It reads as "the chance that $s$ is further along than the start".

The ranker only learns **order**, not distance. It knows that state B comes after state A, but not by how much.

### The discriminator: staying on the demonstrations

A ranker trained only on good demonstrations can give a high score to a state it has never seen. A policy would then exploit those states. To stop that, a classifier $D_\phi(s)$ is trained to tell demonstration states from other states. Its logit is added to the reward:

$$
r(s) = \log p(s) + \alpha\,\big(\log D_\phi(s) - \log(1 - D_\phi(s))\big)
$$

In the paper, the "other" states are the policy's own states, collected during RL. That is like GAIL, and the authors call it *progress-weighted GAIL*.

### Inference

Each step is scored **on its own**: one state in, one reward out. Rank2Reward has no memory and no window of earlier steps.

## 2. How the pen data was used

### The recordings

| | |
| --- | --- |
| Recordings | 564 labelled "Play on hand" episodes of the thumb clicking a mechanical pen: **181 successes, 383 failures** |
| Episode | From the confirmed `episode_start` to the confirmed `terminal` (the click, or giving up) |
| Step rate | 10 Hz, from the 100 Hz Sparsh-skin episodes (the last step, at `terminal`, is always kept) |
| Split | Per seed, by recording and per label: **451 training (145 successes), 113 held out (36 successes)**. Every method and input uses the same split for a given seed. |

### The inputs

Each method was trained twice, once per input:

- **Sparsh-skin:** 368 taxels × 6 values per step: the preprocessed Xela force (x, y, z, baseline-subtracted) and the taxel's forward-kinematics position (x, y, z) in the hand frame. Forces are z-scored with LEQ_DV3's Sparsh-skin statistics; positions with the training set's.
- **Proprio:** 64 values: sin and cos of each of the 16 joint angles, joint velocity and effort. Each step takes the newest joint reading at or before it.

No camera images and no microphone are used.

### What goes into each network

| Network | Training data | Target |
| --- | --- | --- |
| Ranker | Two random steps $i \neq j$ of **one successful training recording** | 1 if $j$ is later, 0 if earlier |
| Ranker, anchor term (ours) | The first and last steps of the same successful recording | Progress 0 on the first, 1 on the last, weight 0.1 |
| Discriminator | Random steps from successful recordings (label 1) and failed recordings (label 0), half each | Success or failure |

**Failures never reach the ranker.** They are used only by the discriminator. In the paper, the discriminator's negatives are policy rollouts. We have no policy yet, so the failed demonstrations stand in for them.

### Network and training

- **Encoders:** the ranker and the discriminator each have their own encoder. The encoder flattens the z-scored step (2208 values for Sparsh-skin, 64 for proprio) and passes it through an MLP: Linear 512 → LayerNorm → SiLU → Linear 256 → LayerNorm → SiLU.
- **Head:** a 2-layer MLP (256 wide) gives one logit.
- **Augmentation:** Gaussian noise (std 0.05) is added to the z-scored inputs.
- **Optimiser:** AdamW, lr 3e-4, weight decay 1e-4, gradients clipped at 1.0.
- **Schedule:** 30 epochs × 200 steps, batch 64. Each batch has 64 ranking pairs and 64 + 64 discriminator steps.
- **Saved model:** the epoch with the best held-out ranking accuracy (around epoch 23 on average).
- **Runs:** 3 seeds × 2 inputs. A run takes 1.5–2 min on an RTX 4090.

### Differences from the paper

- **States instead of frames.** The paper ranks video frames; here each step is a Sparsh-skin or joint state.
- **Offline discriminator.** The paper trains the discriminator against the policy's own states during RL. Here it is trained once, against the failed demonstrations.
- **The anchor term is ours.** It makes progress read as a fraction of the task done: 0 at the start, 1 at the end.
- **No goal conditioning.** That is the paper's Ego4D variant, which isn't used here.

## 3. Results

All numbers are means over the 3 seeds, on each seed's held-out recordings.

Many of the scores are **AUCs**: pick a random success and a random failure, and count how often the success gets the higher value. 1.0 separates them perfectly, 0.5 is a coin flip, and below 0.5 is backwards.

### What it learned about successes

| Score | Sparsh-skin | Proprio |
| --- | --- | --- |
| Ranking accuracy: step pairs of a held-out success in the right order | **0.997** | 0.976 |
| Progress vs time (Spearman), mean over held-out successes | **0.999** | 0.989 |
| Successes whose progress ends higher than it starts | 100% | 100% |

On successes, the ranker does exactly what it was trained to do.

### Telling successes from failures

| Score | Sparsh-skin | Proprio |
| --- | --- | --- |
| Discriminator, single steps (`disc_auc`) | 0.84 | 0.82 |
| Episode: average reward per step | 0.85 | 0.83 |
| Episode, ignoring the last 1 s | 0.85 | 0.82 |
| Single steps: full reward | 0.79 | 0.76 |
| Final progress: over the last 1 s | 0.98 | 1.00 |
| **Progress made before the end:** $p(\text{end} - 1\,\text{s}) - p(\text{start})$ | **0.70** | 0.90 |
| Reference: **episode length alone** (shorter = success) | 0.94 | 0.94 |

**Episode length is a trap.** Failures run longer (median 25 s, against 18 s), because an attempt is recorded until it is given up. A score that averages reward over an episode therefore partly measures length. Length alone scores 0.94, higher than Rank2Reward's episode score.

"Progress made before the end" doesn't depend on length, and it leaves out the final second where the outcome is already visible. On that score, Rank2Reward's progress term is weak: 0.70 on Sparsh-skin.

### The shape of its progress

Average progress over an episode, with time scaled to 0–1 (Sparsh-skin, held-out recordings):

- **Successes:**
  - Progress sits at its floor for the first ~28%.
  - It rises steadily from ~30% to ~75%, through the later grip and the thumb's first move (median 71% of a success).
  - It stays at its top for the rest.
- **Failures:**
  - Progress starts rising earlier (~22%). Failures also move the thumb earlier: median 54% of the episode.
  - It levels off just below the successes' top.
  - It only drops in the **last ~10%**, and collapses on the very last step: final progress 0.08, against 1.00 for successes.

Two consequences:

1. **A stalled press looks almost finished.** The ranker learned the order of states in a success: grip, then press, then click. A failure presses too, so its press states score high. Only the final state, without a click, gives it away. That's why final progress separates well (0.98), but progress made before the end doesn't (0.70).
2. **The first quarter earns no progress.** Progress stays flat at its floor for the first ~28% of a success, so the progress term gives a policy no signal while the hand settles on the pen.

### Where the separation comes from

**The discriminator does the work.** Take the held-out recordings the full reward ranks wrongly. Their progress term ($\log p$) is the same as for correctly ranked recordings of the same kind, within 0.2. What differs is the discriminator's logit, which flips sign:

| Group (Sparsh-skin, 284 held-out recordings over 3 seeds) | Count | Avg. $\log p$ | Avg. discriminator logit |
| --- | --- | --- | --- |
| Successes, ranked right | 83 | −6.3 | +3.5 |
| Successes, ranked wrong | 6 | −6.5 | −9.8 |
| Failures, ranked right | 178 | −5.4 | −9.1 |
| Failures, ranked wrong | 17 | −5.3 | +4.6 |

**Part of the discriminator's signal is there before the task starts.** In session 1, recordings 1–210 succeed about 5% of the time, and recordings 211+ about 50%. The discriminator picks up something that differs between those blocks, and between how the hand sits at the start:

| Check | Sparsh-skin | Proprio |
| --- | --- | --- |
| Reward at step 0 (should be 0.5) | 0.79 | 0.76 |
| Episode AUC, all held-out recordings | 0.85 | 0.83 |
| Episode AUC, recordings 211+ only | 0.78 | 0.73 |

Not all of this is an artefact. A linear classifier on the first tenth of an episode predicts the outcome with AUC 0.90 even within recordings 211+, so how the hand starts on the pen does matter.

### What it gets wrong

23 of the 284 held-out recordings are ranked wrongly (Sparsh-skin): 6 successes and 17 failures.

- **The failures it rewards look like good attempts until the last moment.**
  - 15 of the 17 are from recordings 211+.
  - They press harder than other failures: a thumb-tip force rise of 64, against 53.
  - Their reward follows the successes' curve until the last ~10% of the episode.
  - None is a click that was heard and then rejected; they pressed hard and never clicked.
- **The successes it under-rewards look like failures from the first step.**
  - Two come from settings it rarely saw: th_1_37 (from recordings 1–210) and th_3_11 (session 3).

The full list of recordings is in the comparison report.

### Compared with the other methods

On progress made before the end (Sparsh-skin):

| | Rank2Reward | SARM | TimeRewarder | PROGRESSOR | REDS | Coupled Local Global |
| --- | --- | --- | --- | --- | --- | --- |
| AUC | 0.70 | **0.99** | 0.97 | 0.97 | 0.89 | 0.79 |

On the episode score, Rank2Reward was second, behind SARM. Its discriminator helps it there, but that score is confounded by episode length.

## 4. Takeaways

- **Use it for "is this a demonstration-like state", not for "how far along is this attempt".** Its discriminator separates states well. Its ranker only knows the order of a success, so a failed press earns almost full progress.
- **The ranker is blind early in the grip.** For the first ~28% of an episode, a policy would get its signal from the discriminator alone.
- **Watch the discriminator's pre-task cues.** It rewards how a recording starts, not only what the hand does. This matters less online, where the paper retrains the discriminator against the policy's own states.
- **Possible fixes:**
  - Rank failure steps below the end of a success, so the ranker sees that a stalled press is not progress. Note that the same idea did not help SARM (see the companion report).
  - Add successes from recordings 1–210 and session 3, to reduce the block cue.
