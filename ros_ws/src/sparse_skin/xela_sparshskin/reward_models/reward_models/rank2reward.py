"""Rank2Reward: a shaped reward from the demonstrations' Sparsh-skin taxel states.

Yang, Tjia, Berg, Damen, Agrawal, Gupta, "Rank2Reward: Learning Shaped Reward Functions from
Passive Video", ICRA 2024 (https://rank2reward.github.io/, arXiv 2404.14735). The paper ranks
video frames; here each step is a Sparsh-skin state o (``data.Clip.obs``: forces_local and FK
positions of the 368 taxels) instead of a frame.

Two networks on o, each with its own ``StateEncoder``:

- the **ranker** u(o): trained on pairs of steps (o_i, o_j) of one successful recording with a
  Bradley-Terry / logistic loss, ``BCE(u(o_j) - u(o_i), j > i)``, so it learns the order in
  which the task goes. Its ``progress`` p(o) = sigmoid(u(o)) is pulled to 0 on the first step
  and 1 on the last (``anchor_weight``, so p reads as a fraction of the task done);
- the **discriminator** D(o): trained to tell steps of successful recordings from steps of
  failed ones. The paper trains it against the policy's own states during RL; offline, the
  failed Play on hand recordings stand in for them. It keeps a policy from earning progress in
  states that no demonstration visits.

The reward is ``log p(o) + disc_weight * logit D(o)`` (log D - log(1 - D)). Its terms are
``progress`` (p) and ``discriminator`` (D).

Validation (per epoch, on the held-out recordings): ``val/rank_acc`` (the main metric: the
share of step pairs of successful recordings in the right order), ``val/spearman`` (the rank
correlation of progress with time, mean over successful recordings), ``val/disc_auc`` (success
vs failure steps), ``val/return_auc`` (mean episode reward, success vs failure), and the final
progress of successes and failures.
"""

from __future__ import annotations

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F  # noqa: N812

from reward_models import data
from reward_models.networks import auc, make_encoder, mlp, nanmean, spearman
from reward_models.training import (
    EpochResult,
    StepBank,
    TrainConfig,
    batched,
    config_from_checkpoint,
    load_checkpoint,
)

NAME = "rank2reward"
METRIC = "val/rank_acc"
DEFAULTS = {
    "anchor_weight": 0.1,  # pull progress to 0 / 1 on a recording's first / last step
    "disc_loss_weight": 1.0,
    "disc_weight": 1.0,  # weight of the discriminator's logit in the reward
    "augment_noise": 0.05,  # std of the Gaussian noise added to the z-scored inputs
    "val_pairs": 4000,
    "plot_recordings": 6,
}
EPS = 1e-4


class StateScore(nn.Module):
    """A Sparsh-skin state to one logit."""

    def __init__(self, cfg: TrainConfig) -> None:
        super().__init__()
        self.encoder = make_encoder(cfg)
        self.head = mlp(self.encoder.out_dim, 1)

    def forward(self, obs: torch.Tensor, noise: float = 0.0) -> torch.Tensor:
        return self.head(self.encoder(obs, noise)).squeeze(-1)


def _settings(cfg: TrainConfig) -> dict:
    return {**DEFAULTS, **(cfg.extra or {})}


def reward_terms(u: torch.Tensor, d: torch.Tensor, disc_weight: float):
    progress = torch.sigmoid(u)
    reward = torch.log(progress.clamp_min(EPS)) + disc_weight * d
    return reward, progress, torch.sigmoid(d)


@torch.no_grad()
def _score_clip(ranker: StateScore, disc: StateScore, clip: data.Clip, device) -> tuple:
    obs = torch.from_numpy(clip.obs).to(device)
    u = batched(lambda s: ranker(obs[s]), len(clip))
    d = batched(lambda s: disc(obs[s]), len(clip))
    return u, d


def train(cfg: TrainConfig, train_clips, val_clips, device, logger, cancelled):
    """Yields (epoch, EpochResult) after each of ``cfg.epochs`` epochs."""
    s = _settings(cfg)
    rng = np.random.default_rng(cfg.seed)
    bank = StepBank(train_clips, device)
    success_ids = bank.clip_ids(bank.success)
    failure_ids = bank.clip_ids(~bank.success)
    use_disc = len(failure_ids) > 0
    if not use_disc:
        logger.scalars(0, {"warning/no_failures": 1.0})
    ranker = StateScore(cfg).to(device)
    disc = StateScore(cfg).to(device)
    params = list(ranker.parameters()) + list(disc.parameters())
    opt = torch.optim.AdamW(params, lr=cfg.learning_rate, weight_decay=1e-4)
    b, noise = cfg.batch_size, s["augment_noise"]
    step = 0
    for epoch in range(1, cfg.epochs + 1):
        ranker.train()
        disc.train()
        sums: dict[str, float] = {}
        for _ in range(cfg.steps_per_epoch):
            if cancelled():
                return
            # Pairs of steps of one successful recording.
            clips = bank.sample_clips(rng, success_ids, b)
            n = bank.length[clips]
            i = (rng.random(b) * n).astype(np.int64)
            j = (rng.random(b) * (n - 1)).astype(np.int64)
            j = j + (j >= i)  # j != i
            idx_i = torch.from_numpy(bank.start[clips] + i).to(device)
            idx_j = torch.from_numpy(bank.start[clips] + j).to(device)
            later = torch.from_numpy((j > i).astype(np.float32)).to(device)
            u = ranker(bank.obs[torch.cat([idx_i, idx_j])], noise)
            rank_loss = F.binary_cross_entropy_with_logits(u[b:] - u[:b], later)
            # Progress 0 at the first step, 1 at the last.
            ends = torch.from_numpy(np.concatenate(
                [bank.start[clips], bank.start[clips] + n - 1]
            )).to(device)
            anchor_loss = F.binary_cross_entropy_with_logits(
                ranker(bank.obs[ends], noise),
                torch.cat([torch.zeros(b), torch.ones(b)]).to(device),
            )
            loss = rank_loss + s["anchor_weight"] * anchor_loss
            if use_disc:
                both = torch.cat([bank.sample_steps(rng, success_ids, b),
                                  bank.sample_steps(rng, failure_ids, b)])
                disc_loss = F.binary_cross_entropy_with_logits(
                    disc(bank.obs[both], noise),
                    torch.cat([torch.ones(b), torch.zeros(b)]).to(device),
                )
                loss = loss + s["disc_loss_weight"] * disc_loss
                sums["train/disc_loss"] = sums.get("train/disc_loss", 0.0) + disc_loss.item()
            opt.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            step += 1
            for k, v in (("train/loss", loss), ("train/rank_loss", rank_loss),
                         ("train/anchor_loss", anchor_loss)):
                sums[k] = sums.get(k, 0.0) + v.item()
        metrics = {k: v / cfg.steps_per_epoch for k, v in sums.items()}
        val_metrics, rows = evaluate(ranker, disc, val_clips, device, s, rng, use_disc)
        metrics.update(val_metrics)
        metrics["epoch"] = epoch
        logger.scalars(step, metrics)
        _log_plots(logger, step, rows, s["plot_recordings"])
        yield epoch, EpochResult(
            train_loss=metrics["train/loss"], val_loss=metrics.get("val/rank_loss", float("nan")),
            val_metric=metrics.get(METRIC, float("nan")), metrics=metrics, eval_rows=rows,
            nets={"ranker": ranker, "disc": disc}, extra={"use_disc": use_disc},
        )


@torch.no_grad()
def evaluate(ranker, disc, clips, device, s, rng, use_disc) -> tuple[dict, list[dict]]:
    ranker.eval()
    disc.eval()
    rows, rank_right, rank_loss, rho = [], [], [], []
    final = {data.SUCCESS: [], data.FAILURE: []}
    returns = {data.SUCCESS: [], data.FAILURE: []}
    d_steps = {data.SUCCESS: [], data.FAILURE: []}
    successes = [c for c in clips if c.success]
    pairs_per_clip = max(1, s["val_pairs"] // max(len(successes), 1))
    for clip in clips:
        u, d = _score_clip(ranker, disc, clip, device)
        reward, progress, d_prob = reward_terms(u, d, s["disc_weight"] if use_disc else 0.0)
        u_np = u.cpu().numpy()
        if clip.success:
            i = rng.integers(0, len(clip), pairs_per_clip)
            j = rng.integers(0, len(clip), pairs_per_clip)
            keep = i != j
            i, j = i[keep], j[keep]
            rank_right.append(((u_np[j] > u_np[i]) == (j > i)).astype(float))
            rank_loss.append(F.binary_cross_entropy_with_logits(
                torch.from_numpy(u_np[j] - u_np[i]), torch.from_numpy((j > i).astype(np.float32)),
                reduction="none",
            ).numpy())
            rho.append(spearman(clip.t, u_np))
        final[clip.label].append(float(progress[-1]))
        returns[clip.label].append(float(reward.mean()))
        d_steps[clip.label].append(d.cpu().numpy())
        rows.append({
            "name": clip.name, "label": clip.label, "t": clip.t - clip.t[0],
            "reward": reward.cpu().numpy(),
            "terms": {"progress": progress.cpu().numpy(), "discriminator": d_prob.cpu().numpy()},
        })
    cat = lambda xs: np.concatenate(xs) if xs else np.zeros(0)  # noqa: E731
    metrics = {
        "val/rank_acc": float(cat(rank_right).mean()) if rank_right else float("nan"),
        "val/rank_loss": float(cat(rank_loss).mean()) if rank_loss else float("nan"),
        "val/spearman": nanmean(rho),
        "val/final_progress_success": nanmean(final[data.SUCCESS]),
        "val/final_progress_failure": nanmean(final[data.FAILURE]),
        "val/return_success": nanmean(returns[data.SUCCESS]),
        "val/return_failure": nanmean(returns[data.FAILURE]),
        "val/return_auc": auc(returns[data.SUCCESS], returns[data.FAILURE]),
    }
    if use_disc:
        metrics["val/disc_auc"] = auc(cat(d_steps[data.SUCCESS]), cat(d_steps[data.FAILURE]))
    return metrics, rows


def _log_plots(logger, step: int, rows: list[dict], n: int) -> None:
    shown = ([r for r in rows if r["label"] == data.SUCCESS][: (n + 1) // 2]
             + [r for r in rows if r["label"] == data.FAILURE][: n // 2])
    name = lambda r: f"{r['name']} ({r['label']})"  # noqa: E731
    logger.curves(step, "val/progress_curves",
                  {name(r): (r["t"], r["terms"]["progress"]) for r in shown},
                  "Progress over validation recordings")
    logger.curves(step, "val/reward_curves", {name(r): (r["t"], r["reward"]) for r in shown},
                  "Reward over validation recordings")


class Model:
    """A trained run, for inference."""

    term_names = ("progress", "discriminator")

    def __init__(self, run_dir: str, device: torch.device) -> None:
        ckpt = load_checkpoint(run_dir, device)
        self.cfg = config_from_checkpoint(ckpt)
        self.settings = _settings(self.cfg)
        self.use_disc = ckpt.get("use_disc", True)
        self.device = device
        self.ranker = StateScore(self.cfg).to(device)
        self.disc = StateScore(self.cfg).to(device)
        self.ranker.load_state_dict(ckpt["state"]["ranker"])
        self.disc.load_state_dict(ckpt["state"]["disc"])
        self.ranker.eval()
        self.disc.eval()

    @property
    def step_hz(self) -> float:
        return self.cfg.step_hz

    def __call__(self, clip: data.Clip) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        u, d = _score_clip(self.ranker, self.disc, clip, self.device)
        reward, progress, d_prob = reward_terms(
            u, d, self.settings["disc_weight"] if self.use_disc else 0.0
        )
        return reward.cpu().numpy(), {
            "progress": progress.cpu().numpy(), "discriminator": d_prob.cpu().numpy(),
        }
