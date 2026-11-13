"""The reward models of Coupled Local Global world models, on Sparsh-skin taxel states.

Amigo, Khorrambakht, Mansard, Righetti, "Coupled Local and Global World Models for Efficient
First Order RL", CoRL 2026 (https://arxiv.org/abs/2602.06219).

In the paper a large global (diffusion) world model rolls the policy forward and scores its
states with a global reward head, while a small local RSSM, re-encoding those states, gives the
Jacobians for first-order policy gradients through its own reward head. This module trains the
two reward parts on the Play on hand recordings' Sparsh-skin episodes (``data.Clip.obs``:
forces_local and FK positions of the 368 taxels; the paper uses images); the world models and
the RL are not here.

- **Global reward** G(o): a ``StateEncoder`` and a symlog two-hot head (255 bins over
  [-20, 20]), trained per step on labels as the paper's Push Cube / G1 reward head: a step of
  a successful recording is in the demonstration distribution (``demo_reward``), its last
  ``goal_window_s`` before ``terminal`` is the goal (``goal_reward``, 10 as in the paper), a
  step of a failed recording is 0.
- **Local model**: a smaller encoder e_t, a GRU over (e_t, a_{t-1}) (a: the episode's sim
  joint targets, standardised; the dynamics' action input, not an observation) with latent
  l_t = (h_t, e_t), and
  - a two-hot reward head R(l_t) trained on the same labels and, with ``coupling_weight``, on
    the global reward's prediction for the step (no gradient into G) - the targets it is
    fine-tuned on during RL in the paper;
  - a one-step dynamics head predicting e_{t+1} (no gradient) from (l_t, a_t), so the local
    model is accurate for single steps, which is all its Jacobians need.

The reward is the global one (what the forward rollouts score); its terms are ``global`` and
``local`` (the local model run over the recording from its start).

Validation: ``val/return_auc_global`` (the main metric: mean episode reward, success vs
failure), ``val/return_auc_local``, ``val/goal_auc`` (goal steps vs other steps),
``val/local_global_corr`` (how well the local reward follows the global one), and the losses.
"""

from __future__ import annotations

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F  # noqa: N812

from reward_models import data
from reward_models.networks import TwoHot, auc, make_encoder, mlp, nanmean
from reward_models.training import (
    EpochResult, StepBank, TrainConfig, batched, config_from_checkpoint, load_checkpoint,
)

NAME = "coupled_local_global"
METRIC = "val/return_auc_global"
DEFAULTS = {
    "demo_reward": 1.0,
    "goal_reward": 10.0,
    "goal_window_s": 0.5,
    "seq_len": 16,  # the paper's horizon H (steps)
    "coupling_weight": 1.0,
    "dyn_weight": 1.0,
    "local_hidden": 256,
    "augment_noise": 0.05,  # std of the Gaussian noise added to the z-scored inputs
    "plot_recordings": 6,
}


def _settings(cfg: TrainConfig) -> dict:
    return {**DEFAULTS, **(cfg.extra or {})}


class GlobalReward(nn.Module):
    def __init__(self, cfg: TrainConfig) -> None:
        super().__init__()
        self.encoder = make_encoder(cfg)
        self.head = mlp(self.encoder.out_dim, 255)

    def forward(self, obs, noise: float = 0.0) -> torch.Tensor:  # two-hot logits
        return self.head(self.encoder(obs, noise))


class LocalModel(nn.Module):
    def __init__(self, cfg: TrainConfig, hidden: int) -> None:
        super().__init__()
        self.encoder = make_encoder(cfg, out_dim=128, hidden=256)
        e, a = self.encoder.out_dim, data.N_JOINTS
        self.gru = nn.GRUCell(e + a, hidden)
        self.reward = mlp(hidden + e, 255)
        self.dynamics = mlp(hidden + e + a, e)
        self.hidden = hidden

    def rollout(self, embeds: torch.Tensor, actions: torch.Tensor):
        """``embeds`` (B, T, E), ``actions`` (B, T, A) to latents (B, T, H + E): h_t from
        (e_t, a_{t-1}), a_{-1} = 0."""
        b, t, _ = embeds.shape
        h = embeds.new_zeros(b, self.hidden)
        prev = torch.cat([actions.new_zeros(b, 1, actions.shape[-1]), actions[:, :-1]], 1)
        latents = []
        for k in range(t):
            h = self.gru(torch.cat([embeds[:, k], prev[:, k]], -1), h)
            latents.append(torch.cat([h, embeds[:, k]], -1))
        return torch.stack(latents, 1)


def step_targets(bank: StepBank, idx: torch.Tensor, s: dict) -> torch.Tensor:
    success = bank.step_success[idx]
    goal = (bank.time_to_end[idx] <= s["goal_window_s"]).float() * success
    return success * s["demo_reward"] + goal * (s["goal_reward"] - s["demo_reward"])


def train(cfg: TrainConfig, train_clips, val_clips, device, logger, cancelled):
    """Yields (epoch, EpochResult) after each of ``cfg.epochs`` epochs."""
    s = _settings(cfg)
    rng = np.random.default_rng(cfg.seed)
    train_clips = [c for c in train_clips if len(c) > s["seq_len"]]
    bank = StepBank(train_clips, device)
    a_mean = bank.actions.mean(0)
    a_std = bank.actions.std(0).clamp_min(1e-3)
    all_ids = bank.clip_ids()
    twohot = TwoHot().to(device)
    glob = GlobalReward(cfg).to(device)
    local = LocalModel(cfg, s["local_hidden"]).to(device)
    params = list(glob.parameters()) + list(local.parameters())
    opt = torch.optim.AdamW(params, lr=cfg.learning_rate, weight_decay=1e-4)
    b, seq, noise = cfg.batch_size, s["seq_len"], s["augment_noise"]
    n_seq = max(2, b // 4)
    step = 0
    for epoch in range(1, cfg.epochs + 1):
        glob.train()
        local.train()
        sums: dict[str, float] = {}
        for _ in range(cfg.steps_per_epoch):
            if cancelled():
                return
            # Global: single steps, both labels.
            idx = bank.sample_steps(rng, all_ids, b)
            g_loss = twohot.loss(glob(bank.obs[idx], noise), step_targets(bank, idx, s))
            # Local: windows of seq_len steps.
            clips = bank.sample_clips(rng, all_ids, n_seq)
            first = bank.start[clips] + (rng.random(n_seq) * (bank.length[clips] - seq)).astype(np.int64)
            flat = torch.from_numpy(first[:, None] + np.arange(seq)[None]).to(device).reshape(-1)
            embeds = local.encoder(bank.obs[flat], noise).reshape(n_seq, seq, -1)
            actions = ((bank.actions[flat] - a_mean) / a_std).reshape(n_seq, seq, -1)
            latents = local.rollout(embeds, actions)
            logits = local.reward(latents).reshape(n_seq * seq, -1)
            l_label = twohot.loss(logits, step_targets(bank, flat, s))
            with torch.no_grad():
                g_pred = twohot.mean(glob(bank.obs[flat]))
            l_couple = twohot.loss(logits, g_pred)
            pred = local.dynamics(torch.cat([latents[:, :-1], actions[:, :-1]], -1))
            dyn_loss = F.mse_loss(pred, embeds[:, 1:].detach())
            loss = (g_loss + l_label + s["coupling_weight"] * l_couple
                    + s["dyn_weight"] * dyn_loss)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            step += 1
            for k, v in (("train/loss", loss), ("train/global_loss", g_loss),
                         ("train/local_label_loss", l_label),
                         ("train/local_coupling_loss", l_couple), ("train/dyn_loss", dyn_loss)):
                sums[k] = sums.get(k, 0.0) + v.item()
        metrics = {k: v / cfg.steps_per_epoch for k, v in sums.items()}
        model = _Scorer(glob, local, twohot, a_mean, a_std, device)
        val_metrics, rows = evaluate(model, val_clips, s)
        metrics.update(val_metrics)
        metrics["epoch"] = epoch
        logger.scalars(step, metrics)
        _log_plots(logger, step, rows, s["plot_recordings"])
        yield epoch, EpochResult(
            train_loss=metrics["train/loss"], val_loss=metrics.get("val/global_loss", float("nan")),
            val_metric=metrics.get(METRIC, float("nan")), metrics=metrics, eval_rows=rows,
            nets={"global": glob, "local": local},
            extra={"action_mean": a_mean.cpu(), "action_std": a_std.cpu()},
        )


class _Scorer:
    """Global and local reward (and the local dynamics loss) over a whole clip."""

    def __init__(self, glob, local, twohot, a_mean, a_std, device) -> None:
        self.glob, self.local, self.twohot = glob, local, twohot
        self.a_mean, self.a_std, self.device = a_mean, a_std, device

    @torch.no_grad()
    def __call__(self, clip: data.Clip) -> dict[str, np.ndarray | float]:
        self.glob.eval()
        self.local.eval()
        obs = torch.from_numpy(clip.obs).to(self.device)
        g = self.twohot.mean(batched(lambda s: self.glob(obs[s]), len(clip)))
        embeds = batched(lambda s: self.local.encoder(obs[s]), len(clip))[None]
        actions = ((torch.from_numpy(clip.actions).to(self.device) - self.a_mean) / self.a_std)[None]
        latents = self.local.rollout(embeds, actions)
        loc = self.twohot.mean(self.local.reward(latents))[0]
        pred = self.local.dynamics(torch.cat([latents[:, :-1], actions[:, :-1]], -1))
        dyn = F.mse_loss(pred, embeds[:, 1:]).item()
        return {"global": g.cpu().numpy(), "local": loc.cpu().numpy(), "dyn_loss": dyn}


def evaluate(model: _Scorer, clips: list[data.Clip], s: dict) -> tuple[dict, list[dict]]:
    rows, g_loss, dyn = [], [], []
    returns_g = {data.SUCCESS: [], data.FAILURE: []}
    returns_l = {data.SUCCESS: [], data.FAILURE: []}
    goal_scores, other_scores, all_g, all_l = [], [], [], []
    for clip in clips:
        out = model(clip)
        g, loc = out["global"], out["local"]
        target = np.zeros(len(clip), np.float32)
        if clip.success:
            target[:] = s["demo_reward"]
            goal = (clip.t[-1] - clip.t) <= s["goal_window_s"]
            target[goal] = s["goal_reward"]
            goal_scores.append(g[goal])
            other_scores.append(g[~goal])
        else:
            other_scores.append(g)
        g_loss.append(float(np.mean((g - target) ** 2)))
        dyn.append(out["dyn_loss"])
        returns_g[clip.label].append(float(g.mean()))
        returns_l[clip.label].append(float(loc.mean()))
        all_g.append(g)
        all_l.append(loc)
        rows.append({"name": clip.name, "label": clip.label, "t": clip.t - clip.t[0],
                     "reward": g, "terms": {"global": g, "local": loc}})
    cat = lambda xs: np.concatenate(xs) if xs else np.zeros(0)  # noqa: E731
    g_all, l_all = cat(all_g), cat(all_l)
    corr = (float(np.corrcoef(g_all, l_all)[0, 1])
            if len(g_all) > 2 and g_all.std() > 0 and l_all.std() > 0 else float("nan"))
    return {
        "val/global_loss": nanmean(g_loss),  # MSE to the labels
        "val/dyn_loss": nanmean(dyn),
        "val/return_success": nanmean(returns_g[data.SUCCESS]),
        "val/return_failure": nanmean(returns_g[data.FAILURE]),
        "val/return_auc_global": auc(returns_g[data.SUCCESS], returns_g[data.FAILURE]),
        "val/return_auc_local": auc(returns_l[data.SUCCESS], returns_l[data.FAILURE]),
        "val/goal_auc": auc(cat(goal_scores), cat(other_scores)),
        "val/local_global_corr": corr,
    }, rows


def _log_plots(logger, step: int, rows: list[dict], n: int) -> None:
    shown = ([r for r in rows if r["label"] == data.SUCCESS][: (n + 1) // 2]
             + [r for r in rows if r["label"] == data.FAILURE][: n // 2])
    name = lambda r: f"{r['name']} ({r['label']})"  # noqa: E731
    logger.curves(step, "val/global_reward_curves",
                  {name(r): (r["t"], r["terms"]["global"]) for r in shown},
                  "Global reward over validation recordings")
    logger.curves(step, "val/local_reward_curves",
                  {name(r): (r["t"], r["terms"]["local"]) for r in shown},
                  "Local reward over validation recordings")


class Model:
    """A trained run, for inference."""

    term_names = ("global", "local")

    def __init__(self, run_dir: str, device: torch.device) -> None:
        ckpt = load_checkpoint(run_dir, device)
        self.cfg = config_from_checkpoint(ckpt)
        s = _settings(self.cfg)
        glob = GlobalReward(self.cfg).to(device)
        local = LocalModel(self.cfg, s["local_hidden"]).to(device)
        glob.load_state_dict(ckpt["state"]["global"])
        local.load_state_dict(ckpt["state"]["local"])
        self._scorer = _Scorer(glob, local, TwoHot().to(device),
                               ckpt["action_mean"].to(device), ckpt["action_std"].to(device),
                               device)

    @property
    def step_hz(self) -> float:
        return self.cfg.step_hz

    def __call__(self, clip: data.Clip) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        out = self._scorer(clip)
        return out["global"], {"global": out["global"], "local": out["local"]}
