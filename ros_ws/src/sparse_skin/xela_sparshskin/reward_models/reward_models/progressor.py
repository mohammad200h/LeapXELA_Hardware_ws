"""PROGRESSOR: a goal-conditioned Gaussian estimate of task progress.

Ayalew, Zhang, Wu, Jiang, Maire, Walter, "PROGRESSOR: A Perceptually Guided Reward Estimator
with Self-Supervised Online Refinement", ICCV 2025 (arXiv 2411.17764,
https://github.com/ripl/progressor). The paper uses video frames; here a step is a
``data.Clip.obs`` (Sparsh-skin taxel state or joint state, ``TrainConfig.modality``).

- **Estimator** E(o_i, o_j, o_g) = N(mu, sigma^2): one encoder applied to the initial, current and
  goal steps, the three features concatenated, an MLP to (mu, log sigma^2). Trained on triplets
  i < j < g of one successful recording with KL(N(delta, max(1 / (g - i), sigma_min)^2) || E),
  delta = (j - i) / (g - i). With ``anchor_prob`` the triplet is (first step, j, last step), the
  form used at inference.
- **Goal**: at inference an episode's own goal is unknown, so the reward is averaged over
  ``n_goals`` goal steps (the last step, the click, of training successes), saved in the run.
  With ``cross_goal_prob``, an anchored training triplet's goal is another success's last step,
  so training sees the same kind of goal.
- **Push-back**: the paper pushes the estimate down on the policy's own rollouts with the target
  sg(N(beta * mu, 1 / (g - i)^2)). There is no policy yet, so the failed recordings take that
  place: (their first step, any step, a success's goal). Their early steps look like a
  success's and are pushed down only slightly per update, while the parts where they go wrong
  keep being pushed down.
- **Reward** mu - ``entropy_weight`` * H(N(mu, sigma^2)) (the paper's alpha = 0.4).

Terms: ``progress`` (mu) and ``sigma``. Validation: ``val/spearman`` (the main metric),
``val/expert_kl`` and ``common.summary_metrics``.
"""

from __future__ import annotations

import math

import numpy as np
import torch
from torch import nn

from reward_models import common, data
from reward_models.networks import make_encoder, mlp
from reward_models.training import (
    EpochResult, StepBank, TrainConfig, config_from_checkpoint, load_checkpoint,
)

NAME = "progressor"
METRIC = "val/spearman"
DEFAULTS = {
    "entropy_weight": 0.4,  # alpha
    "beta": 0.9,  # push-back scale
    "pushback_weight": 1.0,
    "sigma_min": 0.02,  # epsilon: floor of the target's std
    "anchor_prob": 0.5,
    "cross_goal_prob": 0.5,
    "n_goals": 16,
    "augment_noise": 0.05,
    "plot_recordings": 6,
}
LOGVAR_RANGE = (-12.0, 4.0)


def _settings(cfg: TrainConfig) -> dict:
    return {**DEFAULTS, **(cfg.extra or {})}


class TripletNet(nn.Module):
    def __init__(self, cfg: TrainConfig) -> None:
        super().__init__()
        self.encoder = make_encoder(cfg)
        self.head = mlp(3 * self.encoder.out_dim, 2)

    def forward(self, oi, oj, og, noise: float = 0.0):
        x = torch.cat([self.encoder(oi, noise), self.encoder(oj, noise),
                       self.encoder(og, noise)], -1)
        mu, logvar = self.head(x).unbind(-1)
        return mu, logvar.clamp(*LOGVAR_RANGE)


def gaussian_kl(mu_p, var_p, mu_q, var_q) -> torch.Tensor:
    """KL(N(mu_p, var_p) || N(mu_q, var_q))."""
    return 0.5 * (torch.log(var_q / var_p) + (var_p + (mu_p - mu_q) ** 2) / var_q - 1.0)


def entropy(var: torch.Tensor) -> torch.Tensor:
    return 0.5 * torch.log(2 * math.pi * math.e * var)


def sample_triplets(rng, n: np.ndarray, anchor_prob: float):
    """Positions i < j < g in clips of lengths ``n`` (>= 3)."""
    m = len(n)
    i = (rng.random(m) * (n - 2)).astype(np.int64)
    g = i + 2 + (rng.random(m) * (n - i - 2)).astype(np.int64)
    anchored = rng.random(m) < anchor_prob
    i, g = np.where(anchored, 0, i), np.where(anchored, n - 1, g)
    j = i + 1 + (rng.random(m) * (g - i - 1)).astype(np.int64)
    return i, j, g, anchored


@torch.no_grad()
def score_clip(net: TripletNet, goals: torch.Tensor, clip: data.Clip, device, s: dict):
    """mu and sigma of every step against each goal, pooled (mixture mean and variance)."""
    obs = torch.from_numpy(clip.obs).to(device)
    n, shape = len(clip), obs.shape[1:]
    mus, vars_ = [], []
    for g in goals:
        mu_g, var_g = [], []
        for a in range(0, n, 256):
            o = obs[a:a + 256]
            mu, logvar = net(obs[:1].expand(len(o), *shape), o, g[None].expand(len(o), *shape))
            mu_g.append(mu)
            var_g.append(logvar.exp())
        mus.append(torch.cat(mu_g))
        vars_.append(torch.cat(var_g))
    mus, vars_ = torch.stack(mus), torch.stack(vars_)
    mu = mus.mean(0)
    var = vars_.mean(0) + mus.var(0, unbiased=False)
    reward = mu - s["entropy_weight"] * entropy(var)
    return reward.cpu().numpy(), mu.cpu().numpy(), var.sqrt().cpu().numpy()


def train(cfg: TrainConfig, train_clips, val_clips, device, logger, cancelled):
    """Yields (epoch, EpochResult) after each of ``cfg.epochs`` epochs."""
    s = _settings(cfg)
    rng = np.random.default_rng(cfg.seed)
    bank = StepBank([c for c in train_clips if len(c) >= 3], device)
    success_ids = bank.clip_ids(bank.success)
    failure_ids = bank.clip_ids(~bank.success)
    ends = bank.start + bank.length - 1  # each clip's last step
    pick = rng.choice(success_ids, size=min(s["n_goals"], len(success_ids)), replace=False)
    goals = bank.obs[torch.from_numpy(ends[pick]).to(device)].clone()
    net = TripletNet(cfg).to(device)
    opt = torch.optim.AdamW(net.parameters(), lr=cfg.learning_rate, weight_decay=1e-4)
    b, noise = cfg.batch_size, s["augment_noise"]
    to_t = lambda x: torch.from_numpy(np.asarray(x)).to(device)  # noqa: E731
    step = 0
    for epoch in range(1, cfg.epochs + 1):
        net.train()
        sums: dict[str, float] = {}
        for _ in range(cfg.steps_per_epoch):
            if cancelled():
                return
            clips = bank.sample_clips(rng, success_ids, b)
            n = bank.length[clips]
            i, j, g, anchored = sample_triplets(rng, n, s["anchor_prob"])
            g_idx = bank.start[clips] + g
            cross = anchored & (rng.random(b) < s["cross_goal_prob"])
            g_idx = np.where(cross, ends[rng.choice(success_ids, size=b)], g_idx)
            delta = to_t(((j - i) / (g - i)).astype(np.float32))
            sigma = to_t(np.maximum(1.0 / (g - i), s["sigma_min"]).astype(np.float32))
            mu, logvar = net(bank.obs[to_t(bank.start[clips] + i)],
                             bank.obs[to_t(bank.start[clips] + j)], bank.obs[to_t(g_idx)], noise)
            expert = gaussian_kl(delta, sigma ** 2, mu, logvar.exp()).mean()
            loss = expert
            if len(failure_ids):
                f = bank.sample_clips(rng, failure_ids, b)
                nf = bank.length[f]
                jf = (rng.random(b) * nf).astype(np.int64)
                gf = ends[rng.choice(success_ids, size=b)]
                mu_f, logvar_f = net(bank.obs[to_t(bank.start[f])],
                                     bank.obs[to_t(bank.start[f] + jf)], bank.obs[to_t(gf)], noise)
                sig_f = to_t(np.maximum(1.0 / (nf - 1), s["sigma_min"]).astype(np.float32))
                push = gaussian_kl(s["beta"] * mu_f.detach(), sig_f ** 2, mu_f,
                                   logvar_f.exp()).mean()
                loss = loss + s["pushback_weight"] * push
                sums["train/pushback_loss"] = sums.get("train/pushback_loss", 0.0) + push.item()
            opt.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
            step += 1
            for k, v in (("train/loss", loss), ("train/expert_kl", expert)):
                sums[k] = sums.get(k, 0.0) + v.item()
        metrics = {k: v / cfg.steps_per_epoch for k, v in sums.items()}
        val_metrics, rows = evaluate(net, goals, val_clips, device, s, rng)
        metrics.update(val_metrics)
        metrics["epoch"] = epoch
        logger.scalars(step, metrics)
        common.log_plots(logger, step, rows, s["plot_recordings"])
        yield epoch, EpochResult(
            train_loss=metrics["train/loss"], val_loss=metrics.get("val/expert_kl", float("nan")),
            val_metric=metrics.get(METRIC, float("nan")), metrics=metrics, eval_rows=rows,
            nets={"triplet": net}, extra={"goals": goals.cpu()},
        )


@torch.no_grad()
def evaluate(net, goals, clips, device, s, rng) -> tuple[dict, list[dict]]:
    net.eval()
    rows, kls = [], []
    for clip in clips:
        reward, mu, sigma = score_clip(net, goals, clip, device, s)
        rows.append({"name": clip.name, "label": clip.label, "t": clip.t - clip.t[0],
                     "reward": reward, "terms": {"progress": mu, "sigma": sigma}})
        if clip.success and len(clip) >= 3:
            obs = torch.from_numpy(clip.obs).to(device)
            i, j, g, _ = sample_triplets(rng, np.full(64, len(clip)), s["anchor_prob"])
            t = lambda x: torch.from_numpy(x).to(device)  # noqa: E731
            m, lv = net(obs[t(i)], obs[t(j)], obs[t(g)])
            delta = t(((j - i) / (g - i)).astype(np.float32))
            sig = t(np.maximum(1.0 / (g - i), s["sigma_min"]).astype(np.float32))
            kls.append(gaussian_kl(delta, sig ** 2, m, lv.exp()).mean().item())
    metrics = common.summary_metrics(rows)
    metrics["val/expert_kl"] = float(np.mean(kls)) if kls else float("nan")
    return metrics, rows


class Model:
    """A trained run, for inference."""

    term_names = ("progress", "sigma")

    def __init__(self, run_dir: str, device: torch.device) -> None:
        ckpt = load_checkpoint(run_dir, device)
        self.cfg = config_from_checkpoint(ckpt)
        self.settings = _settings(self.cfg)
        self.device = device
        self.net = TripletNet(self.cfg).to(device)
        self.net.load_state_dict(ckpt["state"]["triplet"])
        self.net.eval()
        self.goals = ckpt["goals"].to(device)

    @property
    def step_hz(self) -> float:
        return self.cfg.step_hz

    def __call__(self, clip: data.Clip) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        reward, mu, sigma = score_clip(self.net, self.goals, clip, self.device, self.settings)
        return reward, {"progress": mu, "sigma": sigma}
