# SARM on the mechanical pen

How SARM works, how it was trained on the mechanical-pen demonstrations, and what it learned.

- **Paper:** Chen et al. *SARM: Stage-Aware Reward Modeling for Long Horizon Robot Manipulation.* ICLR 2026. [arXiv 2509.25358](https://arxiv.org/abs/2509.25358). Also in LeRobot as `--policy.type=sarm`.
- **Code here:** [sarm.py](../../ros_ws/src/sparse_skin/xela_sparshskin/reward_models/reward_models/sarm.py) and [sarm_failures.py](../../ros_ws/src/sparse_skin/xela_sparshskin/reward_models/reward_models/sarm_failures.py), with the package doc [docs/sarm.md](../../ros_ws/src/sparse_skin/xela_sparshskin/reward_models/docs/sarm.md).
- **Experiment:** `ros_ws/demonstrations/compose_playbacks/reward_models/comparison/run_20261112_1020/`, run 13 Nov 2026.
- **Full comparison with the other methods:** `LEQ_DV3/eval/mechanical_pen/reports/reward_models/index.html`.
- **Companion report:** [Rank2Reward on the mechanical pen](../Rank2Reward/Rank2Reward_mechanical_pen.md).

## Summary

- SARM predicts **which stage** the hand is in (grip, press, click) and **how far through that stage** it is. Its reward is the progress made in each step.
- **It is the best of the seven reward models compared.**
  - **Successes:** progress rises steadily through every held-out success (Spearman with time 0.999).
  - **Successes vs failures:** on progress made before the final second, a success beats a failure **99%** of the time on both Sparsh-skin and proprio, and **100%** within the balanced recordings 211+ (Sparsh-skin).
- **It was never shown a failure,** but it still recognises one. A failure's progress rises, levels off, and falls back near the end. The rewind augmentation taught it what going backwards looks like.
- **Adding failures to training made it worse:** 0.97 on Sparsh-skin and 0.88 on proprio.
- **Training takes 45 s per run.**

## 1. How the algorithm works

### The problem with time-based progress

Rank2Reward and TimeRewarder label progress by **time**: a state 40% of the way through a demonstration is 40% done. That breaks when demonstrations move at different speeds. A slow pen success spends most of its time gripping, and a fast one most of its time pressing. The same hand state then gets very different labels.

### Stages and stage-aware labels

SARM splits every demonstration into **stages**. In the paper these are annotated by people.

**Stage shares.** For each stage $k$, $\bar\alpha_k$ is its average share of a demonstration (the paper's Eq. 1), and $P_k = \bar\alpha_0 + \dots + \bar\alpha_k$ is the cumulative share, with $P_{-1} = 0$.

**Labels.** Inside a stage that runs from step $s$ to step $e$, the within-stage progress is $\tau_t = (t - s)/(e - s)$. The progress label is the paper's Eq. 2:

$$
y_t = P_{k-1} + \bar\alpha_k\,\tau_t \qquad \in [0, 1]
$$

Every demonstration crosses $P_k$ exactly when it finishes stage $k$, however long the stage took. The label depends on where the hand is in the task, not on the clock.

### The network

- **Input:** a short window of frames, plus the episode's first frame as an anchor.
- **Encoder:** a transformer turns each frame of the window into a feature.
- **Two heads:**
  - a **stage head**, which classifies the stage $k$;
  - a **$\tau$ head**, which predicts within-stage progress given a stage. During training it is given the true stage.
- **At inference:**

$$
\hat k = \arg\max \text{stage head}, \qquad \phi_t = P_{\hat k - 1} + \bar\alpha_{\hat k}\,\hat\tau
$$

### Rewind augmentation

SARM trains only on good demonstrations, so it would never see progress go down. **Rewind** fixes that; it is taken from ReWiND.

- **What it does:** with some probability, the last few frames of a training window are replaced by frames going **backwards**.
- **Their labels:** each of those frames keeps its own, lower progress label.
- **The effect:** the model learns that a window which moves forward and then back has lost progress. It doesn't just assume progress keeps rising.

### Reward

The paper's reward for policy learning is the **progress made** (Eq. 6): $r = \phi(t + \Delta) - \phi(t)$. Summed over an episode, this is how far the episode got. Sitting in a stage earns nothing more.

That matters. If the progress **level** were the reward, an attempt that reached "press" early and stayed there would collect a lot of reward. That is exactly what broke REDS on this data.

## 2. How the pen data was used

### The recordings

| | |
| --- | --- |
| Recordings | 564 labelled "Play on hand" episodes of the thumb clicking a mechanical pen: **181 successes, 383 failures** |
| Episode | From the confirmed `episode_start` to the confirmed `terminal` (the click, or giving up) |
| Step rate | 10 Hz, from the 100 Hz Sparsh-skin episodes (the last step, at `terminal`, is always kept) |
| Split | Per seed, by recording and per label: **451 training (145 successes), 113 held out (36 successes)**. Every method and input uses the same split for a given seed. |

### The inputs

Instead of camera frames through frozen CLIP, each step is one of:

- **Sparsh-skin:** 368 taxels × 6 values: the preprocessed Xela force (x, y, z, baseline-subtracted) and the taxel's forward-kinematics position (x, y, z) in the hand frame.
- **Proprio:** 64 values: sin and cos of each of the 16 joint angles, joint velocity and effort.

Each step goes through the same MLP encoder as in the other methods: z-scored and flattened, then 512 → 256. The Sparsh-skin model sees no joint state, so every method in the comparison gets the same input.

### The pen's stages

Nobody annotated stages, so they come from the recording itself:

| k | Stage | Steps | Average share of a success, $\bar\alpha_k$ | Progress range |
| --- | --- | --- | --- | --- |
| 0 | **grip** | From `episode_start` until a thumb joint first moves more than 0.05 rad from where it started | 0.70 | 0 → 0.70 |
| 1 | **press** | From the thumb's first move on | 0.24 | 0.70 → 0.94 |
| 2 | **click** | The last 1 s of a **successful** recording | 0.06 | 0.94 → 1.00 |

These are the same stages REDS uses. The thumb's joint motion was chosen as the marker, rather than thumb-taxel force, because successful clicks press lightly: only 36% of successes show a force rise above 10 units.

The shares $\bar\alpha$ are measured from the training successes. They came out the same for every seed.

### Two variants

| Method | Trained on | Failed recordings |
| --- | --- | --- |
| `sarm` | **Successes only**, as in the paper (145 per seed) | Not used. Rewind is the only source of "progress going down". |
| `sarm_failures` (ours) | Successes and failures | The grip is labelled as in a success. The whole press stage is held at $\tau = 0$ (progress 0.70): pressing without a click earns nothing. |

### Training step

1. **Draw recordings:** 64 training recordings, weighted by length, and a random step $t$ in each.
2. **Build a window ending at $t$:** the episode's first step, plus 8 steps 5 apart (0.5 s apart at 10 Hz, so 4 s of history). Steps before the start are clamped to the first step. The paper uses 8 frames 1 s apart.
3. **Rewind:** with probability 0.5, the last 1–4 steps of the window are replaced by steps going backwards from the last one kept.
4. **Encode:** each step goes through the encoder. A learned bias is added to the first (anchor) step only; there is no other positional encoding, as in the paper.
5. **Transformer:** 2 layers, 4 heads, 256 wide. The paper's is 8 layers, 768 wide, 12 heads; ours is smaller because there are ~145 training successes, not hours of video.
6. **Losses,** on every step of the window except the anchor:
   - cross-entropy of the stage head against $k$;
   - MSE of the $\tau$ head against $\tau$, given the true stage.

Settings:
- **Optimiser:** AdamW, lr 3e-4, weight decay 1e-3 (the paper's), gradients clipped at 1.0, input noise std 0.05.
- **Schedule:** 30 epochs × 200 steps, batch 64. These are the same for all methods in the comparison; the paper uses 2 epochs at 5e-5 on far more data.
- **Saved model:** the epoch whose held-out progress correlates best with time (around epoch 11).
- **Runs:** 3 seeds × 2 inputs × 2 variants. Each takes about 45 s on an RTX 4090.

### Inference

Every step $t$ is scored from the window ending at $t$ (no rewind):

$$
\phi_t = P_{\hat k - 1} + \bar\alpha_{\hat k}\,\hat\tau, \qquad r_t = \phi_t - \phi_{t-1}, \qquad r_0 = 0
$$

The reward is the progress made in the step: the paper's Eq. 6 with $\Delta$ = one step (0.1 s).

## 3. Results

All numbers are means over the 3 seeds, on each seed's held-out recordings.

Many of the scores are **AUCs**: pick a random success and a random failure, and count how often the success gets the higher value. 1.0 separates them perfectly, 0.5 is a coin flip, and below 0.5 is backwards.

### What it learned about successes

| Score | `sarm` Sparsh-skin | `sarm` proprio | `sarm_failures` Sparsh-skin | `sarm_failures` proprio |
| --- | --- | --- | --- | --- |
| Progress vs time (Spearman), held-out successes | **0.999** | 0.997 | 0.994 | 0.987 |
| Mean $\lvert\phi - y\rvert$ on held-out successes | 0.04 | 0.03 | 0.05 | 0.05 |
| Stage accuracy, all held-out steps | 0.90 | 0.89 | 0.98 | 0.98 |
| Successes whose progress ends higher than it starts | 100% | 100% | 100% | 100% |

Stage accuracy counts the failures' steps too. That is likely why the variant trained on failures scores higher on it: it has seen failed press steps labelled as press. I haven't broken this down by success and failure.

### Telling successes from failures

| Score | `sarm` Sparsh-skin | `sarm` proprio | `sarm_failures` Sparsh-skin | `sarm_failures` proprio |
| --- | --- | --- | --- | --- |
| **Progress made before the end:** $\phi(\text{end} - 1\,\text{s}) - \phi(0)$ | **0.99** | **0.99** | 0.97 | 0.88 |
| Same, recordings 211+ only | **1.00** | **1.00** | 0.97 | 0.88 |
| Final progress (last 1 s) | 1.00 | 1.00 | 0.98 | 0.95 |
| Episode: average reward per step | 1.00 | 1.00 | 0.98 | 0.96 |
| Single steps | 0.59 | 0.53 | 0.63 | 0.54 |
| Reference: **episode length alone** | 0.94 | 0.94 | 0.94 | 0.94 |

The scores to trust are **progress made before the end**. Two reasons:

- **The episode score is inflated by episode length.** Failures run longer (median 25 s, against 18 s), because an attempt is recorded until it is given up. SARM's average reward per step is the total progress divided by the number of steps, so it partly measures length. Length alone scores 0.94.
- **Progress made before the end avoids both problems.** It doesn't depend on length, and it leaves out the final second, where the click (or the lack of one) is already visible.

**Single steps are near chance, and that is expected.** A reward of "progress made this step" is a tiny number. One step on its own says little; the information is in the sum.

**There are no pre-task cues.** The reward is 0 at the first step, so it can't pick up the start-of-recording cues that Rank2Reward's discriminator uses. Its score doesn't drop within the balanced recordings 211+.

### The shape of its progress

Average progress over an episode, with time scaled to 0–1 (Sparsh-skin, held-out recordings):

- **Successes:** progress rises steadily from start to end, with no plateau.
- **Failures with `sarm`:**
  - Progress rises *faster* than in successes early on, because failures start pressing sooner.
  - It levels off about three-quarters of the way through.
  - It falls back over roughly the last 15%.
  - The fall happens before the final second, so it counts in "progress made before the end".
- **Failures with `sarm_failures`:** progress plateaus where the press starts and stays there. That is what its labels asked for. It doesn't fall back, though, and it separates less well.

**Why does the fall happen?** Mostly because **the predicted stage falls back to grip**; this was checked step by step (section 4).
- At the last step, 91% of failures are classified as grip on Sparsh-skin, and 98% on proprio.
- The within-press progress $\hat\tau$ also falls, from 0.69 to 0.10.
- The fall starts a median 3.1 s before the end (4.1 s on proprio).

Each step is scored from the last 4 s alone. So the hand state at the end of a failed attempt looks to SARM like the time before the thumb moved. Rewind taught it to accept progress going down, instead of holding the highest value it has seen.

### Why adding failures made it worse

With `sarm_failures`, every failed press is labelled 0.70 (start of press) for its whole length. But early in the press, a failure and a success look alike. So the same kind of state is labelled 0.70 in failures and 0.70–0.94 in successes. That blurs the press stage for successes too:

- progress vs time drops from 0.999 to 0.994 (Sparsh-skin) and from 0.997 to 0.987 (proprio);
- the separation is lost through the fall at the end.

On proprio the drop is larger (0.88). Joint state alone carries less about contact, so the conflicting labels hurt more.

### Compared with the other methods

On progress made before the end (Sparsh-skin):

| | SARM | SARM + failures | TimeRewarder | PROGRESSOR | REDS | Coupled Local Global | Rank2Reward |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AUC | **0.99** | 0.97 | 0.97 | 0.97 | 0.89 | 0.79 | 0.70 |

**SARM vs Rank2Reward.** Both learn only from successes, so the difference is how. Rank2Reward scores one state at a time, so a stalled press still looks like a press. SARM reads a 4 s window and was trained with rewind, so it can see the attempt going backwards.

**SARM vs REDS.** They use the same stages. REDS rewards the stage level, so failures score higher than successes (0.10 on the episode score). SARM rewards the progress made, which fixes that.

## 4. What SARM gets wrong

This is the same analysis as Rank2Reward's, over the 284 recordings held out by any seed. For each recording, I counted how many recordings of the other kind it lands on the wrong side of; it is **ranked wrongly** when that is more than half. Recordings are ranked by **progress made before the end**. The average reward per step ranks every recording correctly, but it is skewed by episode length.

| Group (Sparsh-skin) | Recordings | Progress made before the end | Progress 1 s before the end | Highest progress before then | Stage at the last step | Length (s) | Pressing (s) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Successes, ranked right | 89 | 0.90 | 0.92 | 0.92 | click 78%, press 22% | 18.7 | 5.6 |
| Successes, ranked wrong | **0** | | | | | | |
| Failures, ranked right | 194 | 0.64 | 0.67 | **0.96** | grip 91%, press 8% | 24.7 | 11.5 |
| Failures, ranked wrong | **1** (`th_1_196`) | 0.98 | 0.98 | 0.98 | grip | 27.4 | 10.5 |

Medians; each recording is averaged over the seeds that held it out. Proprio gives the same picture, with the same single mistake.

- **One mistake in 284, against 23 for Rank2Reward.** Every recording Rank2Reward gets wrong, including its hard-pressing failures from recordings 211+, is ranked correctly by SARM. The closest call among them is `th_3_3`, on the wrong side of 22% of the successes.
- **Failures look closer to clicking than successes do, until they drop.**
  - Between 75% and 90% of the episode, about a quarter of failures are classified as *click*.
  - A failure's highest progress has a median of 0.96, above the 0.92 a success has reached 1 s before its end. 57% of failures (76% on proprio) peak above the median success.
  - The ranking still works because the drop to grip comes before the final second.
- **The one failure it gets wrong drops too late.** `th_1_196` (recordings 1–210, wrong on both inputs) is classified as click from 78% to 96% of the episode, at progress 0.98. It falls to grip only in the final second. The recording was ended automatically at 27.45 s for "no click within 8 s". Watch it in the Edit tab: either it came very close to clicking, or the detector missed a click.
- **The weakest success starts high rather than ending low.** `th_1_15` reaches 0.87 one second before its end, as a success should. Its progress made is only 0.65 because its first step is already scored at 0.22.
- **`th_3_3` is the only failure SARM thinks ends in a click** (0.97 at its last step, on both inputs). It is from session 3, which has only 14 recordings. Also worth checking.
- **`sarm_failures` makes the opposite mistake.** It gets 2 successes wrong on Sparsh-skin and 11 on proprio, and no failures. Those successes press longer than the others (median 7.5 s against 5.6 s on Sparsh-skin; 6.4 against 5.3 on proprio). Their progress stays at 0.70, the start of the press, which is where that variant was taught to hold failures. It learned "a long press is a failure".

Data: `sarm_errors.json` in the experiment folder. The comparison report shows the same analysis with plots of progress and predicted stage.

## 5. Takeaways and risks

- **SARM is the reward model to try first** for policy training on the pen.
  - It is fast to train.
  - It is easy to read: predicted stage plus position within the stage.
  - It needs no failures.
- **Risk: a failing press is paid before it is taken back.**
  - Failures start pressing sooner, so their progress rises faster early in the episode.
  - Many reach progress 0.96, often classified as click, several seconds before SARM takes it back (section 4).
  - With a discount factor below 1, early reward is worth more than late reward, so a policy could be paid for pressing hard without clicking.
  - **Before relying on it:** train a policy and check how often its rollouts reach the click stage without a click. Options to try are an undiscounted return, or a penalty when the predicted stage falls back.
- **The grip dominates the progress scale.** Grip is 70% of the scale, because it is 70% of a success's time. The press, which decides the outcome, gets only 24%. Fixed shares, or stages based on contact events, could put more of the reward where the task is decided.
- **The stage boundaries are heuristic.** They come from the thumb's first joint move and from "the last 1 s of a success". Better click markers, such as the audio click time or the thumb-force peak, would sharpen the press and click stages.
- **Not wired in yet.** SARM runs through the offline comparison script (`python3 -m reward_models.compare --methods sarm`). It isn't in the GUI's train/inference nodes, and reward-aligned behaviour cloning (the paper's use of the reward) isn't implemented.
