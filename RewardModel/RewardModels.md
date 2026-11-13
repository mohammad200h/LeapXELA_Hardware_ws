# Learned Reward Models from Video: Rank2Reward and Follow-ups

This note covers five reward-learning methods that turn videos (with or without actions) into a dense reward for RL. It then explains how *Coupled Local and Global World Models for Efficient First Order RL* builds and uses its reward model.

| Method | Venue | Reward signal | OOD / failure handling | Paper | Code |
|---|---|---|---|---|---|
| Rank2Reward | ICRA 2024 | Bradley–Terry temporal ranking → $\log p(s \succ s_0)$ | Online GAIL-style discriminator | [arXiv 2404.14735](https://arxiv.org/abs/2404.14735) | [dxyang/rank2reward](https://github.com/dxyang/rank2reward) |
| PROGRESSOR | ICCV 2025 | Gaussian over progress, given (start, current, goal) | Adversarial "push-back" on rollouts | [arXiv 2411.17764](https://arxiv.org/abs/2411.17764) | [ripl/progressor](https://github.com/ripl/progressor) |
| REDS | ICLR 2025 | Subtask-conditioned reward from a causal transformer | Iterative fine-tuning on failed rollouts | [arXiv 2502.20630](https://arxiv.org/abs/2502.20630) | [REDS_reward_learning](https://github.com/csmile-1006/REDS_reward_learning), [REDS_agent](https://github.com/csmile-1006/REDS_agent) |
| TimeRewarder | ICML 2026 (spotlight) | Signed temporal distance between frame pairs | Reverse pairs act as implicit negatives | [arXiv 2509.26627](https://arxiv.org/abs/2509.26627) | [CowAndSheep/TimeRewarder](https://github.com/CowAndSheep/TimeRewarder) |
| SARM | ICLR 2026 | Stage + within-stage progress, $y = P_{k-1} + \bar\alpha_k \tau$; reward = progress made | Rewind augmentation; mistakes excluded | [arXiv 2509.25358](https://arxiv.org/abs/2509.25358) | [LeRobot](https://www.mintlify.com/huggingface/lerobot/policies/sarm) (no author repo) |
| Coupled Local/Global WMs | CoRL 2026 | Rank2Reward-style energy (Push-T) or human-labelled reward head (Go2, G1), distilled into an RSSM reward head | Real-robot "exploit patching" data | [arXiv 2602.06219](https://arxiv.org/abs/2602.06219) | Not released ("release soon" on the [project page](https://coupled-global-local-wm-rl.pages.dev/)) |

The rest of the document is ordered so that each method builds on the one before it.

---

## 1. Rank2Reward

**Paper:** Yang, Tjia, Berg, Damen, Agrawal, Gupta. *Rank2Reward: Learning Shaped Reward Functions from Passive Video.* ICRA 2024. [arXiv 2404.14735](https://arxiv.org/abs/2404.14735), [project page](https://rank2reward.github.io)
**Code:** [github.com/dxyang/rank2reward](https://github.com/dxyang/rank2reward). This is the official code: a DrQ-v2 fork with Meta-World environments, plus GAIL, VICE and AIRL baselines.

### Idea
The method assumes expert demonstrations make **monotonic progress**, so a later frame is closer to the goal. It learns a utility $\hat u_\theta(s)$ that ranks frames in time order, using a Bradley–Terry model on pairs from the same expert video:

$$
p(s_i \succ s_j) = \sigma\big(\hat u_\theta(s_i) - \hat u_\theta(s_j)\big), \qquad \text{label: later frame preferred}
$$

### Reward
The start state is anchored at $\hat u(s_0) = 0$. The progress probability is $p_{RF}(s) = \sigma(\hat u_\theta(s))$, and the shaped reward is $\log p_{RF}(s)$.

The ranker has only seen expert frames, so it can give **spuriously high scores on out-of-distribution (OOD) states**. To counter this, a classifier $D_\phi$ is trained online to separate expert states from policy states, and its log-ratio is added as a penalty:

$$
\hat r(s) = \log p_{RF}(s) + \alpha\big(\log D_\phi(s) - \log(1 - D_\phi(s))\big)
$$

The authors call the result *progress-weighted GAIL*.

### Strengths and weaknesses
- **+** Needs no actions and no labels. Gives a dense, shaped reward. Also works with human video (an Ego4D variant conditions on the goal frame).
- **−** Only learns *pairwise order*, not *how much* progress was made, so it gives little fine-grained signal between adjacent frames.
- **−** Assumes the demos are optimal and monotonic.
- **−** The discriminator term is adversarial and can be unstable.

A more detailed derivation is in [RewardDesign.md §2](Coupled%20Local%20and%20Global%20World%20Models%20for%20Efficient/RewardDesign.md).

How it was trained on the mechanical-pen data, and the results: [Rank2Reward/Rank2Reward_mechanical_pen.md](Rank2Reward/Rank2Reward_mechanical_pen.md).

---

## 2. PROGRESSOR

**Paper:** Ayalew, Zhang, Wu, Jiang, Maire, Walter (UChicago / TTIC). *PROGRESSOR: A Perceptually Guided Reward Estimator with Self-Supervised Online Refinement.* ICCV 2025. [arXiv 2411.17764](https://arxiv.org/abs/2411.17764), [ICCV open access](https://openaccess.thecvf.com/content/ICCV2025/html/Ayalew_PROGRESSOR_A_Perceptually_Guided_Reward_Estimator_with_Self-Supervised_Online_Refinement_ICCV_2025_paper.html), [project page](https://ripl.github.io/progressor)
**Code:** [github.com/ripl/progressor](https://github.com/ripl/progressor) (official)

### Idea
PROGRESSOR is goal-conditioned and predicts **how far along** the task is, rather than a ranking. Given an initial frame $o_i$, the current frame $o_j$ and a goal frame $o_g$, it predicts a **Gaussian over normalized progress**.

- The progress label is

  $$
  \delta = \frac{|j - i|}{|g - i|} \in [0,1], \qquad p_{target} = \mathcal N\big(\delta,\ \max(\tfrac{1}{g-i}, \epsilon)^2\big)
  $$

- Training minimizes $D_{KL}(p_{target} \,\|\, E_\theta(o_i, o_j, o_g))$.
- For negatives, $o_j$ is replaced with a frame from a different video and the target mean is set to $-1$.
- **Architecture:** a shared ResNet34 encoder per frame. The three embeddings are concatenated and passed through an MLP with two heads, one for $\mu$ and one for $\log\sigma^2$.

### Reward
The reward is the predicted progress minus a penalty on uncertainty (the entropy $\mathcal H$ of the Gaussian):

$$
r = \mu - \alpha\, \mathcal H\big(\mathcal N(\mu, \sigma^2)\big), \qquad \alpha = 0.4
$$

### Online "push-back" refinement
This step replaces Rank2Reward's discriminator. During RL, triplets taken from policy rollouts get a target whose mean is the model's **own prediction scaled down**:

$$
p_{push} = \mathrm{sg}\Big(\mathcal N\big(\beta\, \mu_{\tau'},\ \tfrac{1}{(g-i)^2}\big)\Big), \quad \beta = 0.9
$$

Here $\mathrm{sg}$ is stop-gradient. Expert-loss steps and push-back steps alternate, which gradually lowers reward on non-expert states without training a separate classifier.

### Results
- **Simulation:** Meta-World with DrQ-v2. It beats Rank2Reward, GAIL and TCN on most of 6 tasks, and is the only method that makes progress on door-open and peg-insert-side.
- **Real robot:** UR5 arm. The model was pretrained on EPIC-KITCHENS and then used as the weight in reward-weighted regression on ACT, with 20 good and 20 failed demos per task. It beat R3M and VIP rewards on all 4 tasks.

### Strengths and weaknesses
- **+** Calibrated progress in $[0,1]$ plus an uncertainty estimate.
- **+** Learns from human video.
- **+** Can use mixed-quality demos.
- **−** Assumes **linear, unimodal progress**, so it is unsuitable for cyclic tasks.
- **−** Push-back can over-penalize a policy that is already succeeding (the paper sees this on *reach*).
- **−** Some hyperparameters are unreported: $\epsilon$, the update frequency, and the loss weighting.

---

## 3. REDS: Subtask-Aware Visual Reward Learning from Segmented Demonstrations

**Paper:** Kim, Heo, Lee, Lee, Shin, Lim, Lee (KAIST / UMich / LG AI Research). ICLR 2025. [arXiv 2502.20630](https://arxiv.org/abs/2502.20630), [OpenReview](https://openreview.net/forum?id=mqKVe6F3Up), [project page](https://changyeon.site/reds)
**Code:** [github.com/csmile-1006/REDS_reward_learning](https://github.com/csmile-1006/REDS_reward_learning) trains the reward model. [github.com/csmile-1006/REDS_agent](https://github.com/csmile-1006/REDS_agent) holds the full pipeline and the DreamerV3 agent.

### Idea
REDS targets **long-horizon** tasks, where a single progress scalar is ambiguous. Demonstrations are split into **subtasks**, using scripted indicators, human annotators or a VLM. Each subtask has a text description, and the reward is conditioned on which subtask the robot is currently in.

- **Architecture:** a frozen CLIP ViT-B/16 encodes the frames and the subtask text. A causal GPT (3 layers, 8 heads) reads a short window of frames and outputs a video embedding $v_t$. A small MLP head gives the reward: $\hat R_\theta(s_t; U_i) = f(v_t, e_i)$.
- **The loss has three terms:**
  1. An **EPIC loss** makes the learned reward *policy-equivalent* to the ground-truth subtask signal $\psi$ (EPIC is a pseudometric between reward functions that ignores shaping and scale):

     $$\mathcal L_{EPIC} = \tfrac1k \textstyle\sum_i D^{EPIC}(\hat R^{U_i}_\theta, \psi)$$

  2. A **progress regularizer** on expert data makes the reward increase over time:

     $$\mathcal L_{reg} = \max\big(0,\ \epsilon - (\hat R_\theta(s_{t+j}) - \hat R_\theta(s_t))\big)$$

  3. A **contrastive alignment** term pulls $v_t$ toward the embedding of its correct subtask text.

### Reward at inference
No labels are needed at test time. REDS picks the subtask whose embedding is most similar to the current video embedding, $\bar i = \arg\max_i \mathrm{sim}(v_t, e_i)$, and outputs $f(v_t, e_{\bar i})$.

### Handling failures
REDS refines the model **iteratively**:

1. Train an RL agent with the current reward model and collect its sub-optimal rollouts.
2. Label those rollouts automatically: when the similarity drops below a per-subtask threshold, that subtask is marked as failed.
3. Fine-tune the reward model on the expert data plus these failures, then repeat.

### Results
- **Meta-World:** 8 tasks with DreamerV3. REDS beats the baselines, and on Drawer Open, Push and Coffee Pull it beats the hand-engineered dense reward.
- **Real robot:** FurnitureBench *One Leg* with IQL. It completed 2.45 subtasks on average, against 1.25 for VIPER and 1.10 for DrS.
- **Reward accuracy:** EPIC distance to the ground-truth reward is lower than Rank2Reward's on every task reported. On One Leg it is 0.07, versus 0.60 for Rank2Reward.

### Strengths and weaknesses
- **+** Handles multi-stage tasks.
- **+** Generalizes to unseen tasks and to visual distractors.
- **+** Explicit failure data makes the reward robust.
- **−** Needs **subtask segmentation** for training.
- **−** Relies on CLIP features, which struggle with subtle changes such as screwing in a leg.
- **−** Sensitive to large shifts in camera or background.

---

## 4. TimeRewarder

**Paper:** Liu, Wen, Hu, Jayaraman, Gao (Tsinghua / SJTU / UPenn). *TimeRewarder: Learning Dense Reward from Passive Videos via Frame-wise Temporal Distance.* ICML 2026 (spotlight). [arXiv 2509.26627](https://arxiv.org/abs/2509.26627), [project page](https://timerewarder.github.io)
**Code:** [github.com/CowAndSheep/TimeRewarder](https://github.com/CowAndSheep/TimeRewarder) (official)

### Idea
TimeRewarder is the most direct upgrade of Rank2Reward. Rank2Reward learns a **binary order** between two frames; TimeRewarder learns the **signed, normalized temporal distance** between them:

$$
d_{uv} = \frac{v - u}{T - 1} \in [-1, 1]
$$

- **Discretization:** $d_{uv}$ is split into $K = 20$ bins, encoded as two-hot, and trained with cross-entropy. The paper chose this over direct regression for numerical stability.
- **Implicit negatives:** pairs are sampled in both orders, so a backward pair (negative $d$) represents regressing or wrong behaviour. No separate negative data is needed.
- **Pair sampling:** the gap between frames is sampled with $P(\Delta) \propto 1/\Delta$. This emphasizes small, adjacent-step progress while still covering long gaps.
- **Architecture:** a CLIP ViT-B/16 encodes each frame (fine-tuned). The two features are concatenated and passed through a linear layer that outputs $K$ logits.

### Reward
The reward model is frozen during RL. The reward for each step is the predicted distance between consecutive frames, plus a sparse success bonus:

$$
r_t = \hat d(o_t, o_{t+1}) + \alpha\, r_{success}(o_t)
$$

The dense term is **positive when the robot makes progress, negative when it regresses, and about zero when it stalls**. That gives a fine-grained shaping signal and also discourages oscillating.

### Results
- **Setup:** 10 Meta-World tasks with DrQ-v2, 100 action-free expert videos per task, and 200k environment steps.
- **Success:** near-perfect on 9 of 10 tasks.
- **Baselines beaten:** Rank2Reward, PROGRESSOR, VIP, GAIfO, OT, ADS, TemporalOT and BCO, and also the hand-designed environment reward.
- **Progress estimates:** highest value-order correlation, including against the GVL baseline that uses Gemini.
- **Cross-domain:** mixing 1 robot demo with 20 human videos beats either source alone.

The paper also notes that PROGRESSOR's reward saturates after grasping, while Rank2Reward and TimeRewarder correctly score partial progress on failed attempts.

### Strengths and weaknesses
- **+** Simple, and needs no adversarial or online reward updates.
- **+** Dense and signed, so it penalizes regress.
- **+** Learns from human video.
- **−** Single-frame inputs suffer **visual aliasing** in back-and-forth motions. The authors suggest observation histories as future work.
- **−** The paper's experiments are mainly in simulation.

---

## 5. SARM: Stage-Aware Reward Modeling

**Paper:** Qianzhong Chen et al. (Stanford, UC Berkeley, xdof.ai). *SARM: Stage-Aware Reward Modeling for Long Horizon Robot Manipulation.* ICLR 2026. [arXiv 2509.25358](https://arxiv.org/abs/2509.25358), [ICLR poster](https://iclr.cc/virtual/2026/poster/10008682)
**Code:** no repository from the authors. SARM is part of [LeRobot](https://www.mintlify.com/huggingface/lerobot/policies/sarm) (`lerobot-train --policy.type=sarm`, with optional RA-BC). [Dimios45/packsarm](https://github.com/Dimios45/packsarm) is a third-party reimplementation built on LeRobot.

### Idea
SARM fixes a weakness of frame-index progress labels (Rank2Reward, TimeRewarder) on long tasks whose demonstrations vary in speed. Under such labels the same state can be labelled anywhere from 0.2 to 0.8 progress, depending on how fast that demonstration was. SARM labels progress by **stage**, not by time:

- Each demonstration is split into $K$ subtasks by annotated start/end frames $[s_k, e_k]$.
- A dataset-level prior gives each stage's average share of an episode: $\bar\alpha_k = \frac1M\sum_i L_{i,k}/T_i$, with cumulative $P_k = \sum_{j\le k}\bar\alpha_j$ and $P_0 = 0$.
- Within a stage, progress is normalised time: $\tau_t = (t - s_k)/(e_k - s_k)$.
- The label is

  $$y_t = P_{k-1} + \bar\alpha_k\,\tau_t \in [0, 1]$$

  so every demonstration reaches $P_k$ exactly when it finishes stage $k$, however long it took.

### Model
- **Inputs:** a window of 9 frames: the episode's first frame, then 8 frames 1 s apart ending now. The frames come from a fixed top camera, encoded by frozen CLIP ViT-B/32, together with the joint states. Only the first frame gets a positional bias.
- **Backbone:** an 8-layer transformer (hidden 768, 12 heads).
- **Two heads:**
  1. A **stage estimator**: softmax over $K$ stages, trained with cross-entropy.
  2. A **subtask estimator**: predicts $\hat\tau \in [0,1]$ from the features and the stage, trained with MSE.
- **Inference:** the progress is $\hat y = P_{\hat k-1} + \bar\alpha_{\hat k}\hat\tau$, using the *predicted* stage $\hat k$.
- **Rewind augmentation** (from ReWiND): up to 4 earlier frames are appended in reverse order, so the model sees progress going down. Without it, the paper reports the model "becomes overly optimistic" on real rollouts.

### Reward
For policy learning SARM uses the **progress made over a chunk**, $\hat r = \phi(o_{t+\Delta}) - \phi(o_t)$.

In **Reward-Aligned Behaviour Cloning (RA-BC)**, each training chunk's loss is weighted by this reward:
- weight 1 above a threshold $\kappa$;
- a linear ramp between 0 and $\kappa$, using running statistics of $\hat r$;
- weight 0 for chunks that lose progress.

The result is a soft filter that keeps the demonstrations, or parts of them, that make progress.

### Handling failures
Demonstrations with mistakes are **excluded** from reward-model training; rewind augmentation is what teaches the model about regress. RA-BC then down-weights slow or regressing chunks of the policy data.

### Results
- **Reward quality:** on T-shirt folding, SARM's progress estimates beat LIV, VLC, GVL and ReWiND, both on held-out human demonstrations and on real policy rollouts.
- **Policy success:** RA-BC with SARM reaches 83% on medium and 67% on hard folding at 40k steps. Vanilla BC on all the data gets 1/12 and 0/12.

### Strengths and weaknesses
- **+** Progress labels that don't depend on how fast a demonstration was.
- **+** Explicit stages make the reward easy to read and debug.
- **+** Integrated in LeRobot.
- **−** Needs stage annotation for every training demonstration.
- **−** Progress is shaped by the stage prior $\bar\alpha$, so a stage that takes a short time contributes little reward.
- **−** If progress itself is used as the reward, reaching a stage early and staying there pays well. The paper avoids this by using progress *differences*.

### In this repository
SARM is implemented as two methods in `reward_models` (`sarm` and `sarm_failures`), on Sparsh-skin or joint state instead of camera frames. See [`docs/sarm.md`](../ros_ws/src/sparse_skin/xela_sparshskin/reward_models/docs/sarm.md) and the comparison report in `LEQ_DV3/eval/mechanical_pen/reports/reward_models/`. How it works on the pen data, with results: [SARM/SARM_mechanical_pen.md](SARM/SARM_mechanical_pen.md).

---

## 6. How *Coupled Local and Global World Models* designs its reward

**Paper:** Amigo, Khorrambakht, Mansard, Righetti (NYU). *Coupled Local and Global World Models for Efficient First Order RL.* CoRL 2026. [arXiv 2602.06219](https://arxiv.org/abs/2602.06219), [project page](https://coupled-global-local-wm-rl.pages.dev/)
**Code:** none yet. The project page says "Code (release soon)", and I found no GitHub repository.
**Full notes:** [RewardDesign.md](Coupled%20Local%20and%20Global%20World%20Models%20for%20Efficient/RewardDesign.md)

### Setting
Policies are trained entirely inside a learned world model that works on pixels, with no simulator and no ground-truth state, so the reward has to be **learned from images**. The design has two levels.

### 6.1 Global reward model (the "teacher")

| Task | Global world model | Global reward model |
|---|---|---|
| Push-T (Flexiv arm) | DIAMOND (4M parameters) | A **goal-conditioned energy** $f_\psi(s_t \mid s_{start}, s_{goal})$, trained contrastively "following Rank2Reward" on **random play** and, optionally, demo videos. It scores states higher when they are temporally closer to the goal. |
| Go2 Push Cube / G1 Grab Box | DreamerV4-style transformer (1.0B / 1.4B) | A lightweight **reward head trained on human labels**. It classifies frames as in or out of the task-demonstration distribution, and goal frames get label 10. Labels are recorded with button presses during data collection or added afterwards. |

How this relates to Rank2Reward:
- **Goal conditioning** (and hindsight goal relabelling, which is my inference) removes Rank2Reward's need for *expert* videos. Relative to a goal sampled later in the same trajectory, "later" means "closer" even in random play.
- With $N > 2$ candidates, the pairwise Bradley–Terry loss becomes an InfoNCE / energy-based loss. That matches the paper's words "contrastive" and "energy".
- The paper does **not** say whether it uses Rank2Reward's OOD discriminator. The loss, architecture and sampling scheme are also not specified.

### 6.2 Local reward head (the "student" the policy differentiates)
The small DreamerV3 RSSM has its own reward head $\hat R_\phi$. It uses two-hot regression over 255 bins in symlog space. The head is **distilled from the global reward**:
- **Offline:** on play data, it is trained against the global energy (Push-T) or the human labels (Go2, G1).
- **Online:** on rollouts from the global world model, it is trained against the global reward's predictions.

The rewards enter training in three places:
- The **actor** (first-order, DMO-SAPO) backpropagates through $\hat R_\phi$ and the RSSM Jacobians, and *never* through the expensive global reward model.
- The **critic** builds its λ-returns from the *global* reward plus an entropy bonus.
- The reported **learning curves** sum the global reward over each episode.

The two levels exist for **cost**: a cheap local reward head keeps the gradients cheap to compute, and the large global model keeps the reward faithful to the images.

### 6.3 Handling OOD states and reward hacking
The method has no learned OOD penalty. The policy exploits both the world model and the reward (for example, the box "teleporting" into the hand). The authors fix this with **exploit patching**:

1. Run the exploiting policy on the real robot.
2. Record what actually happens.
3. Fine-tune the world model and **retrain the reward head from scratch**.

On G1 this took 7 rounds and 4.4 h of extra data. The loop plays the same role as Rank2Reward's $D_\phi$, PROGRESSOR's push-back and REDS's failure fine-tuning: it adds data where the reward was wrong. Here the data is real-world and the loop needs a human.

### 6.4 Where the follow-ups could slot in
- **TimeRewarder** could replace the Push-T energy directly. It is pairwise, gives a signed reward per step, and needs no discriminator. A smooth, signed per-step reward also suits first-order gradients.
- **PROGRESSOR's** $(s_{start}, s_t, s_{goal})$ conditioning is almost identical to $f_\psi(s_t \mid s_{start}, s_{goal})$. Its push-back loss is an automatic alternative to retraining the reward head from scratch during patching.
- **SARM** fits the same multi-stage tasks with simpler labels than REDS: stage boundaries plus a per-stage share of the episode, and progress differences as the reward.
- **REDS** fits the multi-stage G1 task (approach, grasp, lift). It could replace hand-labelled reward values with subtask-aware rewards that a VLM segments, which is the automation the paper lists as future work.

---

## References
- Yang et al. *Rank2Reward.* ICRA 2024. https://arxiv.org/abs/2404.14735, https://github.com/dxyang/rank2reward
- Ayalew et al. *PROGRESSOR.* ICCV 2025. https://arxiv.org/abs/2411.17764, https://github.com/ripl/progressor
- Kim et al. *REDS: Subtask-Aware Visual Reward Learning from Segmented Demonstrations.* ICLR 2025. https://arxiv.org/abs/2502.20630, https://github.com/csmile-1006/REDS_reward_learning, https://github.com/csmile-1006/REDS_agent
- Liu et al. *TimeRewarder.* ICML 2026. https://arxiv.org/abs/2509.26627, https://github.com/CowAndSheep/TimeRewarder
- Chen et al. *SARM: Stage-Aware Reward Modeling for Long Horizon Robot Manipulation.* ICLR 2026. https://arxiv.org/abs/2509.25358, https://www.mintlify.com/huggingface/lerobot/policies/sarm
- Amigo et al. *Coupled Local and Global World Models for Efficient First Order RL.* CoRL 2026. https://arxiv.org/abs/2602.06219, https://coupled-global-local-wm-rl.pages.dev/
