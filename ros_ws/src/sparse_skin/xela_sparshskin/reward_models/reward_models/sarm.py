"""SARM: stage-aware reward modelling (stage, then progress within the stage).

Chen et al., "SARM: Stage-Aware Reward Modeling for Long Horizon Robot Manipulation", ICLR 2026
(arXiv 2509.25358; also in LeRobot as ``--policy.type=sarm``). The paper encodes RGB frames and
joint states with frozen CLIP; here a step is a ``data.Clip.obs`` (Sparsh-skin taxel state or
joint state, ``TrainConfig.modality``) through the package's encoder.

- **Stages** k (the same as ``reds``): 0 *grip*, from the episode's start to the thumb's first
  move (``Clip.thumb_onset``); 1 *press*, from there on; 2 *click*, the last ``click_window_s``
  of a successful recording.
- **Progress label** (the paper's Eq. 1-2): alpha_k, the mean share of a successful training
  recording spent in stage k; P_k = alpha_1 + ... + alpha_k; within the stage
  tau_t = (t - s_k) / (e_k - s_k); the target y_t = P_{k-1} + alpha_k * tau_t, in [0, 1]. Unlike a
  frame-index label, the same state gets the same progress in a fast and a slow recording.
- **Model**: the encoder on a window of ``1 + frames`` steps: the episode's first step, then
  ``frames`` steps ``frame_gap`` apart ending at t. A transformer over them, with a learned
  bias on the first token only (no other positions, as in the paper). Per step, a stage head
  (``N_STAGES`` logits) and a progress head on (feature, stage embedding), sigmoid, giving tau.
- **Losses**: cross-entropy on the stage and MSE on tau, for every step of the window except
  the first, summed. During training the progress head gets the true stage (the paper doesn't
  say); at inference it gets the predicted one (the paper's Eq. 3-4).
- **Rewind** (the paper's augmentation from ReWiND): with ``rewind_prob``, the window's last
  1-4 steps are replaced by earlier steps in reverse order, with their own (falling) labels.
  This teaches the model that progress can go down.
- **Failures** (``failures`` setting): the paper trains on successful demonstrations only
  (``"exclude"``, the ``sarm`` method). ``"flat"`` (the ``sarm_failures`` method) also trains on
  failed recordings: grip labelled as in a success, and every press step held at P_1 with
  tau = 0, so pressing without a click earns no progress.
- **Progress** phi_t = P_{k-1} + alpha_k * tau_hat for the predicted stage k (Eq. 4).
- **Reward** (``reward`` setting): ``"delta"`` (default) phi_t - phi_{t-1}, 0 at the first step:
  the paper's reward for policy learning (Eq. 6, phi_{t+D} - phi_t) with D one step. Summed over
  an episode it is the progress made, so stalling earns nothing. ``"progress"`` uses phi_t
  itself, which rewards reaching a stage early and staying there.

Terms: ``progress`` (phi) and ``stage``. Validation: ``val/spearman`` (the main
metric, progress vs time on successes), ``val/stage_acc``, ``val/progress_mae`` (phi against
y_t on successes) and ``common.summary_metrics``.
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

NAME = "sarm"
METRIC = "val/spearman"
N_STAGES = 3  # grip, press, click
STAGE_NAMES = ("grip", "press", "click")
DEFAULTS = {
    "failures": "exclude",  # "exclude" (the paper) or "flat"
    "frames": 8,  # steps after the episode's first step in the window (the paper's 8)
    "frame_gap": 5,  # steps between them: 0.5 s at 10 Hz (the paper: 1 s at 30 fps)
    "click_window_s": 1.0,
    "rewind_prob": 0.5,
    "rewind_max": 4,  # the paper: "up to four frames"
    "layers": 2,
    "heads": 4,
    "reward": "delta",  # "delta" (phi_t - phi_{t-1}) or "progress" (phi_t)
    "augment_noise": 0.05,
    "plot_recordings": 6,
}


def _settings(cfg: TrainConfig, defaults: dict | None = None) -> dict:
    return {**(defaults or DEFAULTS), **(cfg.extra or {})}


def stages(clip: data.Clip, click_window_s: float) -> np.ndarray:
    """k per step: 0 grip, 1 press (from the thumb's first move), 2 click (successes' end)."""
    k = np.zeros(len(clip), np.int64)
    if clip.thumb_onset >= 0:
        k[clip.thumb_onset:] = 1
    if clip.success:
        k[clip.t >= clip.t[-1] - click_window_s] = 2
    return k


def stage_priors(clips, click_window_s: float) -> np.ndarray:
    """alpha_k: the mean share of a successful recording spent in each stage (Eq. 1)."""
    shares = [np.bincount(stages(c, click_window_s), minlength=N_STAGES) / len(c)
              for c in clips if c.success]
    alpha = np.mean(shares, 0) if shares else np.full(N_STAGES, 1.0 / N_STAGES)
    return (alpha / alpha.sum()).astype(np.float32)


def labels(clip: data.Clip, alpha: np.ndarray, s: dict) -> tuple[np.ndarray, np.ndarray]:
    """Per step: stage k and within-stage progress tau (Eq. 2's pieces)."""
    k = stages(clip, s["click_window_s"])
    tau = np.zeros(len(clip), np.float32)
    for stage in range(N_STAGES):
        idx = np.flatnonzero(k == stage)
        if len(idx) == 0:
            continue
        if not clip.success and stage == 1 and s["failures"] == "flat":
            continue  # pressing without a click: no progress within the stage
        a, b = idx[0], idx[-1]
        tau[idx] = (idx - a) / max(b - a, 1)
    return k, tau


def compose(alpha: torch.Tensor, k: torch.Tensor, tau: torch.Tensor) -> torch.Tensor:
    """y = P_{k-1} + alpha_k * tau (Eq. 2 / Eq. 4)."""
    before = torch.cumsum(alpha, 0) - alpha
    return before[k] + alpha[k] * tau


class SARMNet(nn.Module):
    def __init__(self, cfg: TrainConfig, s: dict) -> None:
        super().__init__()
        self.encoder = make_encoder(cfg)
        dim = self.encoder.out_dim
        self.first = nn.Parameter(torch.zeros(dim))  # positional bias on the first token only
        layer = nn.TransformerEncoderLayer(dim, s["heads"], 2 * dim, dropout=0.0,
                                           batch_first=True, norm_first=True)
        self.temporal = nn.TransformerEncoder(layer, s["layers"])
        self.stage_head = mlp(dim, N_STAGES)
        self.stage_emb = nn.Embedding(N_STAGES, dim)
        self.progress_head = mlp(2 * dim, 1)

    def features(self, windows: torch.Tensor, noise: float = 0.0) -> torch.Tensor:
        """``windows`` (B, W, *obs) to per-step features (B, W, D)."""
        b, w = windows.shape[:2]
        e = self.encoder(windows.flatten(0, 1), noise).view(b, w, -1)
        e = torch.cat([e[:, :1] + self.first, e[:, 1:]], 1)
        return self.temporal(e)

    def stage_logits(self, h: torch.Tensor) -> torch.Tensor:
        return self.stage_head(h)

    def tau(self, h: torch.Tensor, k: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(self.progress_head(torch.cat([h, self.stage_emb(k)], -1))).squeeze(-1)


def window_positions(pos: np.ndarray, frames: int, gap: int) -> np.ndarray:
    """(B, 1 + frames) clip positions: the first step, then ``frames`` steps ``gap`` apart
    ending at ``pos`` (clamped at the first step)."""
    offsets = (np.arange(frames) - (frames - 1)) * gap
    return np.concatenate([np.zeros((len(pos), 1), np.int64),
                           np.maximum(pos[:, None] + offsets[None], 0)], 1)


def rewind(rng, win: np.ndarray, prob: float, most: int, gap: int) -> np.ndarray:
    """With ``prob``, replace the last r (1..``most``) steps of each window by the steps before
    the one kept last, in reverse order: the window goes forward, then backward."""
    win = win.copy()
    for b in np.flatnonzero(rng.random(len(win)) < prob):
        r = int(rng.integers(1, most + 1))
        keep = win.shape[1] - r
        last = win[b, keep - 1]
        win[b, keep:] = np.maximum(last - gap * np.arange(1, r + 1), 0)
    return win


@torch.no_grad()
def score_clip(net: SARMNet, alpha: torch.Tensor, clip: data.Clip, device, s: dict):
    """phi and the predicted stage of every step, from the window ending at it."""
    obs = torch.from_numpy(clip.obs).to(device)
    n = len(clip)
    win = torch.from_numpy(window_positions(np.arange(n), s["frames"], s["frame_gap"]))
    phi, stage = [], []
    for a in range(0, n, 256):
        h = net.features(obs[win[a:a + 256].to(device)])[:, -1]
        k = net.stage_logits(h).argmax(-1)
        phi.append(compose(alpha, k, net.tau(h, k)))
        stage.append(k)
    return torch.cat(phi).cpu().numpy(), torch.cat(stage).cpu().numpy()


def reward_of(phi: np.ndarray, s: dict) -> np.ndarray:
    if s["reward"] == "progress":
        return phi
    return np.concatenate([[0.0], np.diff(phi)]).astype(np.float32)


def make_train(defaults: dict):
    def train(cfg: TrainConfig, train_clips, val_clips, device, logger, cancelled):
        """Yields (epoch, EpochResult) after each of ``cfg.epochs`` epochs."""
        s = _settings(cfg, defaults)
        rng = np.random.default_rng(cfg.seed)
        clips = [c for c in train_clips if len(c) >= 2 and (c.success or s["failures"] != "exclude")]
        alpha_np = stage_priors(clips, s["click_window_s"])
        alpha = torch.from_numpy(alpha_np).to(device)
        bank = StepBank(clips, device)
        k_np, tau_np = zip(*[labels(c, alpha_np, s) for c in clips])
        k_all = torch.from_numpy(np.concatenate(k_np)).to(device)
        tau_all = torch.from_numpy(np.concatenate(tau_np)).to(device)
        ids = bank.clip_ids()
        net = SARMNet(cfg, s).to(device)
        opt = torch.optim.AdamW(net.parameters(), lr=cfg.learning_rate, weight_decay=1e-3)
        b, noise = cfg.batch_size, s["augment_noise"]
        step = 0
        for epoch in range(1, cfg.epochs + 1):
            net.train()
            sums: dict[str, float] = {}
            for _ in range(cfg.steps_per_epoch):
                if cancelled():
                    return
                cl = bank.sample_clips(rng, ids, b)
                pos = (rng.random(b) * bank.length[cl]).astype(np.int64)
                win = window_positions(pos, s["frames"], s["frame_gap"])
                win = rewind(rng, win, s["rewind_prob"], s["rewind_max"], s["frame_gap"])
                idx = torch.from_numpy(bank.start[cl][:, None] + win).to(device)
                h = net.features(bank.obs[idx], noise)[:, 1:]  # the first step is the anchor
                k, tau = k_all[idx[:, 1:]], tau_all[idx[:, 1:]]
                stage_loss = F.cross_entropy(net.stage_logits(h).flatten(0, 1), k.flatten())
                tau_loss = F.mse_loss(net.tau(h, k), tau)
                loss = stage_loss + tau_loss
                opt.zero_grad(set_to_none=True)
                loss.backward()
                nn.utils.clip_grad_norm_(net.parameters(), 1.0)
                opt.step()
                step += 1
                for name, val in (("train/loss", loss), ("train/stage_ce", stage_loss),
                                  ("train/tau_mse", tau_loss)):
                    sums[name] = sums.get(name, 0.0) + val.item()
            metrics = {name: val / cfg.steps_per_epoch for name, val in sums.items()}
            val_metrics, rows = evaluate(net, alpha, val_clips, device, s)
            metrics.update(val_metrics)
            metrics["epoch"] = epoch
            for i, name in enumerate(STAGE_NAMES):
                metrics[f"prior/{name}"] = float(alpha_np[i])
            logger.scalars(step, metrics)
            common.log_plots(logger, step, rows, s["plot_recordings"])
            yield epoch, EpochResult(
                train_loss=metrics["train/loss"],
                val_loss=metrics.get("val/progress_mae", float("nan")),
                val_metric=metrics.get(METRIC, float("nan")), metrics=metrics, eval_rows=rows,
                nets={"sarm": net}, extra={"alpha": torch.from_numpy(alpha_np)},
            )
    return train


@torch.no_grad()
def evaluate(net: SARMNet, alpha, clips, device, s) -> tuple[dict, list[dict]]:
    net.eval()
    rows, right, err = [], [], []
    alpha_np = alpha.cpu().numpy()
    for clip in clips:
        phi, stage = score_clip(net, alpha, clip, device, s)
        k, tau = labels(clip, alpha_np, {**s, "failures": "flat"})
        right.append((stage == k).astype(float))
        if clip.success:
            y = compose(alpha.cpu(), torch.from_numpy(k), torch.from_numpy(tau)).numpy()
            err.append(np.abs(phi - y))
        rows.append({"name": clip.name, "label": clip.label, "t": clip.t - clip.t[0],
                     "reward": reward_of(phi, s),
                     "terms": {"progress": phi, "stage": stage.astype(np.float32)}})
    metrics = common.summary_metrics(rows)
    metrics["val/stage_acc"] = float(np.concatenate(right).mean()) if right else float("nan")
    metrics["val/progress_mae"] = float(np.concatenate(err).mean()) if err else float("nan")
    return metrics, rows


def make_model(defaults: dict):
    class Model:
        """A trained run, for inference."""

        term_names = ("progress", "stage")

        def __init__(self, run_dir: str, device: torch.device) -> None:
            ckpt = load_checkpoint(run_dir, device)
            self.cfg = config_from_checkpoint(ckpt)
            self.settings = _settings(self.cfg, defaults)
            self.device = device
            self.net = SARMNet(self.cfg, self.settings).to(device)
            self.net.load_state_dict(ckpt["state"]["sarm"])
            self.net.eval()
            self.alpha = ckpt["alpha"].to(device)

        @property
        def step_hz(self) -> float:
            return self.cfg.step_hz

        def __call__(self, clip: data.Clip) -> tuple[np.ndarray, dict[str, np.ndarray]]:
            phi, stage = score_clip(self.net, self.alpha, clip, self.device, self.settings)
            return reward_of(phi, self.settings), {"progress": phi,
                                                   "stage": stage.astype(np.float32)}
    return Model


train = make_train(DEFAULTS)
Model = make_model(DEFAULTS)
