"""Networks and metrics shared by the reward models."""

from __future__ import annotations

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F  # noqa: N812

from reward_models.data import N_TAXELS, OBS_CHANNELS, SPARSH, obs_dim


class StateEncoder(nn.Module):
    """A Sparsh-skin step (``obs`` (B, 368, 6): forces_local and positions per taxel) to a
    feature vector: each channel z-scored with ``mean`` / ``std`` (kept in the state dict,
    clipped to +-``clip``), flattened in FK order, and an MLP (Linear, LayerNorm, SiLU)."""

    def __init__(self, mean=None, std=None, out_dim: int = 256, hidden: int = 512,
                 clip: float = 20.0, in_dim: int = N_TAXELS * OBS_CHANNELS) -> None:
        super().__init__()
        self.register_buffer("mean", torch.as_tensor(
            np.zeros(OBS_CHANNELS) if mean is None else mean, dtype=torch.float32))
        self.register_buffer("std", torch.as_tensor(
            np.ones(OBS_CHANNELS) if std is None else std, dtype=torch.float32))
        self.clip = clip
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden), nn.LayerNorm(hidden), nn.SiLU(),
            nn.Linear(hidden, out_dim), nn.LayerNorm(out_dim), nn.SiLU(),
        )
        self.out_dim = out_dim

    def normalize(self, obs: torch.Tensor) -> torch.Tensor:
        return ((obs - self.mean) / self.std).clamp(-self.clip, self.clip)

    def forward(self, obs: torch.Tensor, noise: float = 0.0) -> torch.Tensor:
        """``noise``: std of Gaussian noise added to the z-scores (training augmentation)."""
        x = self.normalize(obs)
        if noise > 0:
            x = x + noise * torch.randn_like(x)
        return self.net(x.flatten(1))


def make_encoder(cfg, **kwargs) -> StateEncoder:
    """A ``StateEncoder`` for ``cfg.modality``'s ``obs``, z-scored with ``cfg.obs_mean`` /
    ``obs_std`` (sparsh: per taxel channel, 6; proprio: per channel, ``PROPRIO_DIM``)."""
    modality = getattr(cfg, "modality", SPARSH) or SPARSH
    return StateEncoder(cfg.obs_mean or None, cfg.obs_std or None,
                        in_dim=obs_dim(modality), **kwargs)


def mlp(in_dim: int, out_dim: int, hidden: int = 256, layers: int = 2) -> nn.Sequential:
    mods, dim = [], in_dim
    for _ in range(layers):
        mods += [nn.Linear(dim, hidden), nn.LayerNorm(hidden), nn.SiLU()]
        dim = hidden
    mods.append(nn.Linear(dim, out_dim))
    return nn.Sequential(*mods)


# ---- DreamerV3's symlog two-hot reward head --------------------------------------------------


def symlog(x: torch.Tensor) -> torch.Tensor:
    return torch.sign(x) * torch.log1p(torch.abs(x))


def symexp(x: torch.Tensor) -> torch.Tensor:
    return torch.sign(x) * (torch.exp(torch.abs(x)) - 1)


class TwoHot(nn.Module):
    """Values as a categorical over ``bins`` evenly spaced in symlog space (DreamerV3)."""

    def __init__(self, bins: int = 255, low: float = -20.0, high: float = 20.0) -> None:
        super().__init__()
        self.register_buffer("edges", torch.linspace(low, high, bins))

    def loss(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        y = symlog(target).clamp(self.edges[0], self.edges[-1])
        above = torch.searchsorted(self.edges, y.contiguous()).clamp(1, len(self.edges) - 1)
        below = above - 1
        lo, hi = self.edges[below], self.edges[above]
        w_hi = ((y - lo) / (hi - lo)).clamp(0, 1)
        dist = torch.zeros_like(logits)
        dist.scatter_(-1, below[..., None], (1 - w_hi)[..., None])
        dist.scatter_add_(-1, above[..., None], w_hi[..., None])
        return -(dist * F.log_softmax(logits, -1)).sum(-1).mean()

    def mean(self, logits: torch.Tensor) -> torch.Tensor:
        return symexp((F.softmax(logits, -1) * self.edges).sum(-1))


# ---- metrics ---------------------------------------------------------------------------------


def auc(positive: np.ndarray, negative: np.ndarray) -> float:
    """Area under the ROC curve of scores ``positive`` above ``negative`` (Mann-Whitney U)."""
    positive, negative = np.asarray(positive, float), np.asarray(negative, float)
    if len(positive) == 0 or len(negative) == 0:
        return float("nan")
    scores = np.concatenate([positive, negative])
    ranks = np.empty(len(scores))
    order = np.argsort(scores, kind="mergesort")
    ranks[order] = np.arange(1, len(scores) + 1)
    for value in np.unique(scores):  # ties share their mean rank
        tie = scores == value
        if tie.sum() > 1:
            ranks[tie] = ranks[tie].mean()
    u = ranks[: len(positive)].sum() - len(positive) * (len(positive) + 1) / 2
    return float(u / (len(positive) * len(negative)))


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3:
        return float("nan")
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def nanmean(values) -> float:
    values = np.asarray([v for v in values if v is not None], float)
    values = values[np.isfinite(values)]
    return float(values.mean()) if len(values) else float("nan")
