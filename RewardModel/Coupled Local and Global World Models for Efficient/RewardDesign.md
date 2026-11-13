# Reward Design in "Coupled Local and Global World Models for Efficient First Order RL"

Amigo, Khorrambakht, Mansard, Righetti. CoRL 2026, arXiv:2602.06219v3.

Paper sections used: 3.3 (Global Reward Model), 3.4 (Local Reward and World Models), 3.5 (Data Collection), 5 (Limitations), A.2 (Exploit Patching), A.4 and A.5 (Algorithm).

> **Notation.** Anything marked **[inferred]** is my own interpretation and is not stated in the paper. Everything else comes from the paper itself or from Rank2Reward (Yang et al., ICRA 2024).

---

## 1. Overview

Every task is learned in **pixel space** with **no simulator**, so a hand-written reward function on ground-truth state is impossible. Instead, the authors learn rewards from images in two stages:

1. **Global reward model**: trained offline from images.
   - For **Push-T** it is a goal-conditioned energy function in the style of Rank2Reward.
   - For **Push Cube and G1 Grab Box** it is a reward head with human-labelled frames.
2. **Local reward head** `R̂_ϕ`: the reward head of the small DreamerV3 RSSM. It is trained to imitate the global reward model, and the policy gradient actually flows through **this** head.

| Task | Global world model | Global reward model | Supervision |
|---|---|---|---|
| Push-T (Flexiv arm) | DIAMOND (4M) | Contrastive, goal-conditioned energy `f_ψ(s_t \| s_start, s_goal)` in the style of Rank2Reward | Temporal order in play videos, plus optional demo videos |
| Go2 Push Cube | DreamerV4-style (1.0B) | Lightweight reward head classifying "in task-demonstration distribution" | Human labels; goal frames are labelled **10** |
| G1 Grab Box | DreamerV4-style (1.4B) | Same kind of reward head, re-initialized after each patching round | Human labels |

---

## 2. Rank2Reward (Yang et al., ICRA 2024)

Rank2Reward learns a **shaped** reward from **action-free video** by learning to *rank frames by their temporal order*.

### 2.1 Key assumption

The demonstrations are optimal and make **monotonic progress** toward the goal. Formally, the true reward satisfies $r(s,a) > \varepsilon > 0$, so the optimal value function $V^*(s)$ increases monotonically along an expert trajectory. Under this assumption, *"later in the video" means "closer to the goal"*.

### 2.2 Ranking model (Bradley–Terry)

A network outputs a scalar **utility** $\hat u_\theta(s)$. Consider two frames $s_i^k, s_j^k$ from the same expert trajectory $\tau_k$. The later frame is labelled as preferred, and the preference is modelled as:

$$
p(s_i^k \succ s_j^k) = \frac{\exp \hat u_\theta(s_i^k)}{\exp \hat u_\theta(s_i^k) + \exp \hat u_\theta(s_j^k)}
= \sigma\big(\hat u_\theta(s_i^k) - \hat u_\theta(s_j^k)\big)
$$

The model is trained with a cross-entropy (logistic) loss over pairs:

$$
\max_\theta\ \mathbb{E}_{\tau_k\sim\mathcal D^e,\ s_i^k,s_j^k\sim\tau_k}
\Big[\mathbb 1_{i>j}\log p(s_i^k \succ s_j^k) + \mathbb 1_{i<j}\log p(s_j^k \succ s_i^k)\Big]
$$

The result is a utility function that **increases monotonically along a trajectory**. The ranker is trained on **expert data only**.

### 2.3 From utility to reward

The utility of the start state is anchored at zero, $\hat u(s_0)=0$. Then the probability that a state $s$ is "past the start" is a sigmoid:

$$
p_{RF}(s) = p(s \succ s_0) = \frac{1}{1+\exp(-\hat u_\theta(s))} \in (0,1)
$$

The base reward is $\hat r(s) = \log p_{RF}(s)$. Maximizing it maximizes the log-likelihood of making progress. The paper describes $p_{RF}$ as *value-function-like* (dense and shaped) rather than a sparse success signal.

### 2.4 Handling out-of-distribution states

The ranker is only trained on expert frames, so it gives **spuriously high outputs on out-of-distribution (OOD) states**, and RL exploits this. To counter it, Rank2Reward adds a pessimistic KL penalty toward the expert state distribution:

$$
\max_\pi\ \mathbb E_{s\sim d^\pi}\big[\log p_{RF}(s)\big] - \alpha\, D_{KL}\big(d^\pi(s)\,\|\,d^e(s)\big)
$$

The density ratio $d^e/d^\pi$ is estimated with a classifier $D_\phi$. It is trained with binary cross-entropy to separate expert states from on-policy replay states, and the ratio is $D_\phi/(1-D_\phi)$. This gives the **final reward**:

$$
\boxed{\hat r(s) = \log p_{RF}(s) + \alpha\big(\log D_\phi(s) - \log(1-D_\phi(s))\big)}
$$

The two terms play different roles:

- The **ranking term** is learned offline and provides shaping.
- The **classifier term** is updated online and keeps the agent on the expert distribution.

The authors describe the whole method as a *progress-weighted GAIL*.

### 2.5 Goal-conditioned variant in Rank2Reward

This variant appears **only in Rank2Reward's Ego4D experiment**:

- The **last frame of each clip is the goal**, and the ranker is conditioned on it.
- The classifier is trained to decide whether a frame and a goal come from the **same clip**. Frames from the same clip are positives, and frames from other clips are "counterfactual" negatives.
- With the true goal the reward rises monotonically. With a counterfactual goal it stays flat or low.

Rank2Reward does **not** condition on a start frame. Its RL backbone is DrQ-v2 in simulation and a sample-efficient actor-critic on the real xArm, both using frozen R3M features.

---

## 3. The goal-conditioned energy function (Push-T)

### 3.1 What the paper states

> "we train a contrastive reward model on random play and, optionally, demonstration videos, following [Rank2Reward]. Specifically, we learn a goal-conditioned energy function $f_\psi(s_t \mid s_{start}, s_{goal})$ that assigns higher scores to states temporally closer to the goal."

That is all the detail the paper gives. It does not provide the loss, the architecture, the sampling scheme, or whether the OOD classifier from Section 2.4 is used.

### 3.2 Why "energy function"

The Bradley–Terry model in Section 2.2 is an **energy-based model** over states. Write $E_\psi = -f_\psi$. The probability of picking one state from a set is then a Boltzmann distribution:

$$
p(s_i \text{ is closest to goal} \mid \{s_1,\dots,s_N\}, s_{goal}) = \frac{\exp f_\psi(s_i\mid s_{start}, s_{goal})}{\sum_n \exp f_\psi(s_n\mid s_{start}, s_{goal})}
$$

With $N=2$ this is exactly the pairwise loss of Rank2Reward. With $N>2$ it is an InfoNCE-style **contrastive** loss, which matches the paper's word "contrastive". In either case $f_\psi$ is an **unnormalized log-score**: it only makes sense *relative* to other states under the same conditioning, so only differences and orderings carry meaning.

### 3.3 How it can be trained on random play [inferred]

Rank2Reward needs *expert* videos, because "later" means "better" only if the agent is making progress. Random play does not have that property. **Goal conditioning removes the requirement.**

- Pick a play trajectory, choose a later frame from it as $s_{goal}$ (hindsight relabelling), and use an earlier frame as $s_{start}$.
- **Relative to that goal**, frames that come later in the trajectory are temporally closer to it, so the ranking label is valid even when the behaviour is random.
- The demonstration videos (marked "optionally") then add trajectories that move toward the *actual task goal* directly.

Two further readings, also inferred:

- **Role of $s_{start}$.** It plays the part of Rank2Reward's anchor $\hat u(s_0)=0$. Conditioning on it tells the model which segment of progress is being measured, so scores are comparable across episodes.
- **Inference.** For RL, $s_{goal}$ is a fixed image of the T block centred in the target orientation, $s_{start}$ is the episode's first frame, and the per-step reward is $r_t = f_\psi(s_t\mid s_{start}, s_{goal})$, possibly normalized.

### 3.4 Pros and cons in this setting

- **Pro:** no frame-level human labels are needed. The reward is dense and shaped, which suits first-order gradients, since a smooth reward gives informative $\partial r/\partial s$.
- **Con:** the monotonic-progress assumption is weak in play data, and an energy trained only on recorded frames can be exploited on OOD frames hallucinated by the world model. Rank2Reward handles this with $D_\phi$. Whether this paper does the same is **not stated**.

---

## 4. Human-labelled reward head (Push Cube and G1 Grab Box)

On the transformer (DreamerV4-style) world model, the authors **replace** the energy model with a lightweight **reward head** on the world model:

- The head **classifies whether a frame belongs to the task-demonstration distribution**.
- On **Push Cube**, frames where the cube reaches the goal get a **higher label, 10**.
- **Labels come from a human.** They are recorded either *during data collection* (button presses during play) or in a *post-processing pass*.
- On **G1**, the head is **re-initialized after each of the 7 patching rounds** (Section 6) and retrained on the play data plus all patching data collected so far.

**[inferred]** The PPO failure mode on Push Cube was *"repeatedly approaching and avoiding the cube to collect rewards of 1"*. This suggests a two-level scheme: about **1** for task-relevant frames, such as the cube in view and being approached or pushed, and **10** at the goal. The exact G1 labelling scheme is not described.

The trade-off compared with Push-T is simple: it is cheaper to build and more robust, but it needs human labelling effort and is less smoothly shaped. The Limitations section suggests **VLM-based labelling** as the way to automate it.

---

## 5. Local reward head: what the policy actually optimizes

The DreamerV3 RSSM has its own reward head $\hat R_\phi$. It uses two-hot regression over **255 bins** in **symlog [−20, 20]**.

| Phase | Push-T target | Push Cube / G1 target |
|---|---|---|
| Offline pretraining on play data | Global energy model predictions | Per-frame human labels (the same ones that supervise the global head) |
| Online fine-tuning during RL | Global reward predictions on rollouts from the global world model | Same |

The rewards enter training at three different points:

- **Actor (DMO-SAPO).** The objective uses the **local** head on local latents $l_h$. These latents are obtained by re-encoding frames generated by the global model:

  $$
  \mathcal L_\pi(\theta) = \mathbb E\Big[\textstyle\sum_{h=0}^{H-1}\gamma^h\big(\hat R_\phi(l_{h+1}) + \alpha\tilde{\mathcal H}_h\big) + \gamma^H V_\psi(l_H)\Big]
  $$

  Gradients go through $\hat R_\phi$ and the RSSM Jacobians. They never pass through the global reward model.
- **Critic.** The λ-return targets use the **global** reward plus an entropy bonus: $\tilde r_n = r_n + \alpha\tilde{\mathcal H}_n$.
- **Reported learning curves.** These show the undiscounted sum of the global reward over 64-step episodes.

**Why use two heads?** The global reward model works on pixels, or on the global model's latents, and differentiating through it is expensive. Distilling it into $\hat R_\phi$ keeps the backward pass cheap, which is the same reason the world model is split into local and global parts. The cost is that the gradient comes from an *approximation of an approximation* of the task reward.

---

## 6. Reward hacking and patching

The policy exploited **both** the world model and the reward model. The paper does not fix this by redesigning the reward. It fixes it by **collecting targeted data**:

1. Train RL, and let it find policies with artificially high returns, such as the box teleporting into the hand or an "invisible force" pulling the box (Fig. 7).
2. Deploy those exploiting policies on the **real robot** and record what actually happens.
3. Fine-tune the world model on the new data and **retrain the reward head from scratch**.

On G1 this took **7 rounds**, adding 0.19, 0.55, 0.74, 0.80, 1.00, 0.72 and 0.43 h of data, **4.4 h** in total. Each round fine-tuned the model for 3k updates. Separately, the authors probed the model with VR headsets (Meta Quest 3 for Go2, Pico with IMUs for G1) to find poorly modelled regions.

In effect, this loop does the job that Rank2Reward's OOD classifier $D_\phi$ does: it suppresses reward in states the data does not support. The difference is that it uses real-world data and human effort instead of a learned density ratio.

---

## 7. Open questions and gaps

- **Push-T energy model:** the loss, architecture, pair or negative sampling, goal relabelling scheme, and normalization are all missing. It is also unclear whether demo videos were actually used.
- **OOD regularization:** there is no mention of a Rank2Reward-style discriminator term.
- **Label scheme:** only the value 10 at the goal is given. Values for other frames, and the entire G1 scheme, are not described.
- **No ablation on reward design:** the paper does not compare energy-based and labelled rewards on the same task, and does not compare a global reward with a local-only one.
- **Reward fidelity metrics:** the paper reports LPIPS for the world model but no accuracy or calibration numbers for the reward model.

---

## References

- Amigo et al. *Coupled Local and Global World Models for Efficient First Order RL.* CoRL 2026. arXiv:2602.06219.
- Yang, Tjia, Berg, Damen, Agrawal, Gupta. *Rank2Reward: Learning Shaped Reward Functions from Passive Video.* ICRA 2024. <https://arxiv.org/abs/2404.14735>, project page: <https://rank2reward.github.io>
- Hafner et al. *Mastering Diverse Control Tasks through World Models* (DreamerV3). Nature 2025.
- Xing, Luk, Oh. *Stabilizing RL in Differentiable Multiphysics Simulation* (SAPO). ICLR 2025.
