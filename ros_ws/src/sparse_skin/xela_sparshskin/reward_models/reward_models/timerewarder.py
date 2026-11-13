"""TimeRewarder: a dense reward from the signed temporal distance between two steps.

Liu, Wen, Hu, Jayaraman, Gao, "TimeRewarder: Learning Dense Reward from Passive Videos via
Frame-wise Temporal Distance", ICML 2026 (arXiv 2509.26627,
https://github.com/CowAndSheep/TimeRewarder). The paper pairs video frames; here a step is a
``data.Clip.obs`` (Sparsh-skin taxel state or joint state, ``TrainConfig.modality``).

- **Distance model** F(o_u, o_v): one encoder applied to both steps, the two features
  concatenated, an MLP to ``bins`` logits over [-1, 1]. Trained on pairs of one successful
  recording with the two-hot cross-entropy to d_uv = (v - u) / (T - 1). The pair's gap is
  log-uniform (P(gap) ~ 1 / gap: mostly near steps, some far ones) and its order is random, so
  backward pairs (negative d) are the implicit negatives: undoing progress scores below zero.
- **Reward** r_t = F(o_{t-k}, o_t) decoded to a scalar (k = ``reward_stride``; 0 for t < k).
  The paper adds a sparse success bonus; the episodes' terminal reward already carries it.
- **Progress** term: F(o_0, o_t), the distance travelled from the episode's first step.

Validation: ``val/spearman`` (the main metric: progress vs time on successes),
``val/pair_acc`` (sign of held-out pairs), ``val/pair_loss``, and ``common.summary_metrics``.
"""

from __future__ import annotations

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F  # noqa: N812

from reward_models import common, data
from reward_models.networks import make_encoder, mlp
from reward_models.training import (
    EpochResult, StepBank, TrainConfig, batched, config_from_checkpoint, load_checkpoint,
)

NAME = "timerewarder"
METRIC = "val/spearman"
DEFAULTS = {
    "bins": 20,
    "reward_stride": 1,  # k: the reward compares each step with the one k steps before
    "augment_noise": 0.05,
    "val_pairs": 4000,
    "plot_recordings": 6,
}


def _settings(cfg: TrainConfig) -> dict:
    return {**DEFAULTS, **(cfg.extra or {})}


class PairNet(nn.Module):
    def __init__(self, cfg: TrainConfig, bins: int) -> None:
        super().__init__()
        self.encoder = make_encoder(cfg)
        self.head = mlp(2 * self.encoder.out_dim, bins)
        self.register_buffer("centers", torch.linspace(-1.0, 1.0, bins))

    def forward(self, a, b, noise: float = 0.0) -> torch.Tensor:  # logits
        return self.head(torch.cat([self.encoder(a, noise), self.encoder(b, noise)], -1))

    def decode(self, logits: torch.Tensor) -> torch.Tensor:
        return (F.softmax(logits, -1) * self.centers).sum(-1)

    def loss(self, logits: torch.Tensor, d: torch.Tensor, reduction: str = "mean"):
        """Two-hot cross-entropy to distances ``d`` in [-1, 1]."""
        k = len(self.centers)
        pos = ((d.clamp(-1, 1) + 1) / 2 * (k - 1))
        lo = pos.floor().clamp(0, k - 2).long()
        w = (pos - lo).clamp(0, 1)
        target = torch.zeros_like(logits)
        target.scatter_(-1, lo[..., None], (1 - w)[..., None])
        target.scatter_add_(-1, (lo + 1)[..., None], w[..., None])
        ce = -(target * F.log_softmax(logits, -1)).sum(-1)
        return ce.mean() if reduction == "mean" else ce


def sample_pairs(rng: np.random.Generator, n: np.ndarray):
    """For clips of lengths ``n`` (>= 2): positions (a, b) with a log-uniform gap and a random
    order, and their signed distance (b - a) / (n - 1)."""
    gap = np.floor(np.exp(rng.random(len(n)) * np.log(n))).astype(np.int64)
    gap = np.clip(gap, 1, n - 1)
    u = (rng.random(len(n)) * (n - gap)).astype(np.int64)
    v = u + gap
    swap = rng.random(len(n)) < 0.5
    a, b = np.where(swap, v, u), np.where(swap, u, v)
    return a, b, ((b - a) / (n - 1)).astype(np.float32)


@torch.no_grad()
def score_clip(net: PairNet, clip: data.Clip, device, stride: int):
    obs = torch.from_numpy(clip.obs).to(device)
    n = len(clip)
    first = obs[:1]
    progress = net.decode(batched(lambda s: net(first.expand(s.stop - s.start, *obs.shape[1:]),
                                                obs[s]), n))
    reward = torch.zeros(n, device=device)
    if n > stride:
        reward[stride:] = net.decode(batched(lambda s: net(obs[s], obs[stride:][s]), n - stride))
    return reward.cpu().numpy(), progress.cpu().numpy()


def train(cfg: TrainConfig, train_clips, val_clips, device, logger, cancelled):
    """Yields (epoch, EpochResult) after each of ``cfg.epochs`` epochs."""
    s = _settings(cfg)
    rng = np.random.default_rng(cfg.seed)
    bank = StepBank([c for c in train_clips if len(c) >= 2], device)
    success_ids = bank.clip_ids(bank.success)
    net = PairNet(cfg, s["bins"]).to(device)
    opt = torch.optim.AdamW(net.parameters(), lr=cfg.learning_rate, weight_decay=1e-4)
    b, noise = cfg.batch_size, s["augment_noise"]
    step = 0
    for epoch in range(1, cfg.epochs + 1):
        net.train()
        total = 0.0
        for _ in range(cfg.steps_per_epoch):
            if cancelled():
                return
            clips = bank.sample_clips(rng, success_ids, b)
            a, bb, d = sample_pairs(rng, bank.length[clips])
            ia = torch.from_numpy(bank.start[clips] + a).to(device)
            ib = torch.from_numpy(bank.start[clips] + bb).to(device)
            loss = net.loss(net(bank.obs[ia], bank.obs[ib], noise), torch.from_numpy(d).to(device))
            opt.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
            step += 1
            total += loss.item()
        metrics = {"train/loss": total / cfg.steps_per_epoch}
        val_metrics, rows = evaluate(net, val_clips, device, s, rng)
        metrics.update(val_metrics)
        metrics["epoch"] = epoch
        logger.scalars(step, metrics)
        common.log_plots(logger, step, rows, s["plot_recordings"])
        yield epoch, EpochResult(
            train_loss=metrics["train/loss"], val_loss=metrics.get("val/pair_loss", float("nan")),
            val_metric=metrics.get(METRIC, float("nan")), metrics=metrics, eval_rows=rows,
            nets={"pair": net},
        )


@torch.no_grad()
def evaluate(net: PairNet, clips, device, s, rng) -> tuple[dict, list[dict]]:
    net.eval()
    rows, right, losses = [], [], []
    successes = [c for c in clips if c.success and len(c) >= 2]
    per_clip = max(1, s["val_pairs"] // max(len(successes), 1))
    for clip in clips:
        reward, progress = score_clip(net, clip, device, s["reward_stride"])
        rows.append({"name": clip.name, "label": clip.label, "t": clip.t - clip.t[0],
                     "reward": reward, "terms": {"progress": progress}})
        if clip.success and len(clip) >= 2:
            a, b, d = sample_pairs(rng, np.full(per_clip, len(clip)))
            obs = torch.from_numpy(clip.obs).to(device)
            logits = net(obs[torch.from_numpy(a).to(device)], obs[torch.from_numpy(b).to(device)])
            pred = net.decode(logits).cpu().numpy()
            right.append((np.sign(pred) == np.sign(d)).astype(float))
            losses.append(net.loss(logits, torch.from_numpy(d).to(device), "none").cpu().numpy())
    metrics = common.summary_metrics(rows)
    metrics["val/pair_acc"] = float(np.concatenate(right).mean()) if right else float("nan")
    metrics["val/pair_loss"] = float(np.concatenate(losses).mean()) if losses else float("nan")
    return metrics, rows


class Model:
    """A trained run, for inference."""

    term_names = ("progress",)

    def __init__(self, run_dir: str, device: torch.device) -> None:
        ckpt = load_checkpoint(run_dir, device)
        self.cfg = config_from_checkpoint(ckpt)
        self.settings = _settings(self.cfg)
        self.device = device
        self.net = PairNet(self.cfg, self.settings["bins"]).to(device)
        self.net.load_state_dict(ckpt["state"]["pair"])
        self.net.eval()

    @property
    def step_hz(self) -> float:
        return self.cfg.step_hz

    def __call__(self, clip: data.Clip) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        reward, progress = score_clip(self.net, clip, self.device, self.settings["reward_stride"])
        return reward, {"progress": progress}
