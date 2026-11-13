"""REDS: a subtask-aware reward from segmented demonstrations.

Kim, Heo, Lee, Lee, Shin, Lim, Lee, "Subtask-Aware Visual Reward Learning from Segmented
Demonstrations", ICLR 2025 (arXiv 2502.20630, https://github.com/csmile-1006/REDS_reward_learning).
The paper encodes video frames and subtask texts with CLIP; here a step is a ``data.Clip.obs``
(Sparsh-skin taxel state or joint state, ``TrainConfig.modality``) and each subtask has a
learned embedding (there is no text).

- **Subtasks** psi (used in training only; the reward needs none at inference):
  0 *grip*, from ``episode_start`` to the thumb's first move (``Clip.thumb_onset``, from the
  joint states whatever the modality); 1 *press*, from there on; 2 *click*, the last
  ``click_window_s`` of a successful recording. A failure never reaches the click. psi is the
  number of subtasks done, the paper's ground-truth subtask reward.
- **Model**: the encoder on each of the last ``context`` steps, a causal transformer over them,
  its last output v_t; subtask embeddings e_i; a reward head f(v_t, e_i).
- **Losses** (the paper's, summed):
  - EPIC: for each subtask i, the EPIC distance sqrt((1 - rho) / 2) between f(v, e_i) and psi
    over the batch (rho: Pearson correlation, which already ignores the canonicalisation's
    offset);
  - progress: on successes, a hinge making f(v_{t+j}, e_psi) exceed f(v_t, e_psi) by ``margin``;
  - contrastive: v_t's cosine similarities to the e_i (over ``temperature``) classify psi.
- **Failures**: the paper fine-tunes the model on the RL agent's failed rollouts, labelled with
  the subtask they stall in. The failed recordings are that data already, so they are in the
  EPIC and contrastive losses from the start.
- **Reward** f(v_t, e_i*) with i* the subtask most similar to v_t.

Terms: ``progress`` (the reward) and ``subtask`` (i*). Validation: ``val/epic_score`` (the main
metric: 1 - EPIC distance to psi on held-out steps), ``val/subtask_acc`` and
``common.summary_metrics``.
"""

from __future__ import annotations

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F  # noqa: N812

from reward_models import common, data
from reward_models.networks import make_encoder, mlp
from reward_models.training import (
    EpochResult, StepBank, TrainConfig, config_from_checkpoint, load_checkpoint,
)

NAME = "reds"
METRIC = "val/epic_score"
N_SUBTASKS = 3  # grip, press, click
DEFAULTS = {
    "context": 4,  # steps the causal transformer sees
    "click_window_s": 1.0,
    "margin": 0.05,  # epsilon of the progress hinge
    "progress_gaps": [1, 3, 5],  # j of the progress hinge, in steps
    "temperature": 0.1,
    "layers": 2,
    "heads": 4,
    "augment_noise": 0.05,
    "plot_recordings": 6,
}


def _settings(cfg: TrainConfig) -> dict:
    return {**DEFAULTS, **(cfg.extra or {})}


def subtasks(clip: data.Clip, click_window_s: float) -> np.ndarray:
    """psi per step: 0 grip, 1 press (from the thumb's first move), 2 click (successes' end)."""
    psi = np.zeros(len(clip), np.int64)
    if clip.thumb_onset >= 0:
        psi[clip.thumb_onset:] = 1
    if clip.success:
        psi[clip.t >= clip.t[-1] - click_window_s] = 2
    return psi


class REDSNet(nn.Module):
    def __init__(self, cfg: TrainConfig, s: dict) -> None:
        super().__init__()
        self.encoder = make_encoder(cfg)
        dim, k = self.encoder.out_dim, s["context"]
        self.pos = nn.Parameter(torch.zeros(k, dim))
        layer = nn.TransformerEncoderLayer(dim, s["heads"], 2 * dim, dropout=0.0,
                                           batch_first=True, norm_first=True)
        self.temporal = nn.TransformerEncoder(layer, s["layers"])
        self.register_buffer("mask", nn.Transformer.generate_square_subsequent_mask(k))
        self.subtasks = nn.Embedding(N_SUBTASKS, dim)
        self.head = mlp(2 * dim, 1)

    def video(self, windows: torch.Tensor, noise: float = 0.0) -> torch.Tensor:
        """``windows`` (B, K, *obs) to v (B, D): the causal transformer's last output."""
        b, k = windows.shape[:2]
        e = self.encoder(windows.flatten(0, 1), noise).view(b, k, -1) + self.pos
        return self.temporal(e, mask=self.mask, is_causal=True)[:, -1]

    def reward(self, v: torch.Tensor, i: torch.Tensor) -> torch.Tensor:
        return self.head(torch.cat([v, self.subtasks(i)], -1)).squeeze(-1)

    def similarity(self, v: torch.Tensor) -> torch.Tensor:  # (B, N_SUBTASKS) cosine
        return F.normalize(v, dim=-1) @ F.normalize(self.subtasks.weight, dim=-1).T


def epic_distance(r: torch.Tensor, psi: torch.Tensor) -> torch.Tensor:
    r, psi = r - r.mean(), psi - psi.mean()
    rho = (r * psi).sum() / (r.norm() * psi.norm()).clamp_min(1e-8)
    return torch.sqrt(((1 - rho) / 2).clamp_min(0))


@torch.no_grad()
def score_clip(net: REDSNet, clip: data.Clip, device, context: int):
    obs = torch.from_numpy(clip.obs).to(device)
    n = len(clip)
    win = torch.from_numpy(common.window_index(np.zeros(n, np.int64), np.arange(n), context))
    v = torch.cat([net.video(obs[win[a:a + 256].to(device)]) for a in range(0, n, 256)])
    sub = net.similarity(v).argmax(-1)
    return net.reward(v, sub).cpu().numpy(), sub.cpu().numpy(), v


def train(cfg: TrainConfig, train_clips, val_clips, device, logger, cancelled):
    """Yields (epoch, EpochResult) after each of ``cfg.epochs`` epochs."""
    s = _settings(cfg)
    rng = np.random.default_rng(cfg.seed)
    bank = StepBank(train_clips, device)
    psi_np = np.concatenate([subtasks(c, s["click_window_s"]) for c in train_clips])
    psi = torch.from_numpy(psi_np).to(device)
    all_ids, success_ids = bank.clip_ids(), bank.clip_ids(bank.success)
    net = REDSNet(cfg, s).to(device)
    opt = torch.optim.AdamW(net.parameters(), lr=cfg.learning_rate, weight_decay=1e-4)
    b, k, noise = cfg.batch_size, s["context"], s["augment_noise"]
    gaps = np.asarray(s["progress_gaps"], np.int64)
    every = torch.arange(N_SUBTASKS, device=device)
    step = 0

    def windows(clips: np.ndarray, pos: np.ndarray) -> torch.Tensor:
        return torch.from_numpy(common.window_index(bank.start[clips], pos, k)).to(device)

    for epoch in range(1, cfg.epochs + 1):
        net.train()
        sums: dict[str, float] = {}
        for _ in range(cfg.steps_per_epoch):
            if cancelled():
                return
            # EPIC and contrastive: steps of every recording.
            clips = bank.sample_clips(rng, all_ids, b)
            pos = (rng.random(b) * bank.length[clips]).astype(np.int64)
            idx = windows(clips, pos)
            v = net.video(bank.obs[idx], noise)
            target = psi[idx[:, -1]]
            epic = torch.stack([
                epic_distance(net.reward(v, every[i].expand(b)), target.float())
                for i in range(N_SUBTASKS)
            ]).mean()
            contrast = F.cross_entropy(net.similarity(v) / s["temperature"], target)
            # Progress: step pairs (t, t + j) of successes.
            sc = bank.sample_clips(rng, success_ids, b)
            j = rng.choice(gaps, size=b)
            n = bank.length[sc]
            j = np.minimum(j, n - 1)
            t0 = (rng.random(b) * (n - j)).astype(np.int64)
            w0, w1 = windows(sc, t0), windows(sc, t0 + j)
            v01 = net.video(bank.obs[torch.cat([w0, w1])], noise)
            p01 = psi[torch.cat([w0[:, -1], w1[:, -1]])]
            r01 = net.reward(v01, p01)
            reg = F.relu(s["margin"] - (r01[b:] - r01[:b])).mean()
            loss = epic + reg + contrast
            opt.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
            step += 1
            for name, val in (("train/loss", loss), ("train/epic", epic),
                              ("train/progress_hinge", reg), ("train/contrastive", contrast)):
                sums[name] = sums.get(name, 0.0) + val.item()
        metrics = {name: val / cfg.steps_per_epoch for name, val in sums.items()}
        val_metrics, rows = evaluate(net, val_clips, device, s)
        metrics.update(val_metrics)
        metrics["epoch"] = epoch
        logger.scalars(step, metrics)
        common.log_plots(logger, step, rows, s["plot_recordings"])
        yield epoch, EpochResult(
            train_loss=metrics["train/loss"], val_loss=1 - metrics.get(METRIC, float("nan")),
            val_metric=metrics.get(METRIC, float("nan")), metrics=metrics, eval_rows=rows,
            nets={"reds": net},
        )


@torch.no_grad()
def evaluate(net: REDSNet, clips, device, s) -> tuple[dict, list[dict]]:
    net.eval()
    rows, rewards, targets, right = [], [], [], []
    for clip in clips:
        reward, sub, _ = score_clip(net, clip, device, s["context"])
        psi = subtasks(clip, s["click_window_s"])
        rewards.append(reward)
        targets.append(psi)
        right.append((sub == psi).astype(float))
        rows.append({"name": clip.name, "label": clip.label, "t": clip.t - clip.t[0],
                     "reward": reward,
                     "terms": {"progress": reward, "subtask": sub.astype(np.float32)}})
    metrics = common.summary_metrics(rows)
    if rewards:
        d = epic_distance(torch.from_numpy(np.concatenate(rewards)).double(),
                          torch.from_numpy(np.concatenate(targets)).double())
        metrics["val/epic_score"] = float(1 - d)
        metrics["val/subtask_acc"] = float(np.concatenate(right).mean())
    return metrics, rows


class Model:
    """A trained run, for inference."""

    term_names = ("progress", "subtask")

    def __init__(self, run_dir: str, device: torch.device) -> None:
        ckpt = load_checkpoint(run_dir, device)
        self.cfg = config_from_checkpoint(ckpt)
        self.settings = _settings(self.cfg)
        self.device = device
        self.net = REDSNet(self.cfg, self.settings).to(device)
        self.net.load_state_dict(ckpt["state"]["reds"])
        self.net.eval()

    @property
    def step_hz(self) -> float:
        return self.cfg.step_hz

    def __call__(self, clip: data.Clip) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        reward, sub, _ = score_clip(self.net, clip, self.device, self.settings["context"])
        return reward, {"progress": reward, "subtask": sub.astype(np.float32)}
