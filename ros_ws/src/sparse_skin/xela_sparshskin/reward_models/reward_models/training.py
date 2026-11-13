"""What the reward model trainers share: the run configuration, the Sparsh-skin steps on the
GPU, the checkpoint format and the run driver (load the clips, split, log, train, report).

A run is a folder ``<output_dir>/<run name>/`` with:

- ``config.json``: the ``TrainConfig``, the W&B run URL and the train / validation recordings;
- ``metrics.jsonl``: every logged scalar (``logging_utils``), also sent to W&B;
- ``model.pt``: the checkpoint of the best validation epoch (``save_checkpoint``);
- ``eval.json``: that epoch's per-recording validation results (``label``, ``t``, ``reward``,
  ``terms``), which the GUI's Visualize tab plots.
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import Callable

import numpy as np
import torch

from reward_models import data
from reward_models.logging_utils import DEFAULT_ENV_FILE, DEFAULT_PROJECT, RunLogger

CONFIG_NAME = "config.json"
MODEL_NAME = "model.pt"
EVAL_NAME = "eval.json"
LOAD_SHARE = 0.15  # share of the progress bar for loading the clips


@dataclass
class TrainConfig:
    method: str
    recordings_dir: str
    output_dir: str = ""
    epochs: int = 30
    steps_per_epoch: int = 200
    batch_size: int = 64
    learning_rate: float = 3e-4
    val_fraction: float = 0.2
    # The Sparsh-skin episodes' rate: those of <recordings_dir>/sparsh_skin/<episode_hz>hz/
    # (the Processing tab's Rate) are used. Runs saved before it have the default, 100 Hz.
    episode_hz: float = 100.0
    step_hz: float = 25.0  # the Sparsh-skin episodes are taken at this rate
    # What a step's obs is (data.MODALITIES): the Sparsh-skin taxel state or the joint state.
    # Runs saved before it are sparsh.
    modality: str = data.SPARSH
    seed: int = 0
    wandb: bool = True
    wandb_project: str = DEFAULT_PROJECT
    wandb_name: str = ""
    env_file: str = DEFAULT_ENV_FILE
    device: str = "cuda"
    extra: dict = field(default_factory=dict)  # the method's own settings
    # Per-channel z-score of obs (data.ObsStats), set by run_training from the training clips.
    obs_mean: list = field(default_factory=list)
    obs_std: list = field(default_factory=list)


@dataclass
class Feedback:
    stage: str
    progress: float
    epoch: int = 0
    epochs: int = 0
    train_loss: float = float("nan")
    val_loss: float = float("nan")
    val_metric: float = float("nan")
    val_metric_name: str = ""
    status: str = ""


@dataclass
class EpochResult:
    """What a method reports after each epoch."""
    train_loss: float
    val_loss: float
    val_metric: float
    metrics: dict[str, float]
    eval_rows: list[dict]  # per validation recording: name, label, t, reward, terms
    nets: dict[str, torch.nn.Module]  # saved in model.pt when the epoch is the best
    extra: dict = field(default_factory=dict)  # saved with them


Report = Callable[[Feedback], None]
Cancelled = Callable[[], bool]


class Cancel(Exception):
    pass


def default_output_dir(recordings_dir: str, method: str) -> str:
    return os.path.join(data.runs_root(recordings_dir), method)


def resolve_device(name: str) -> torch.device:
    if name.startswith("cuda") and not torch.cuda.is_available():
        return torch.device("cpu")
    return torch.device(name)


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


class StepBank:
    """Every step of a set of clips, concatenated on ``device``, to sample batches from.

    ``start`` / ``length`` locate each clip's steps; ``phase`` is each step's place in its
    clip (0 at ``episode_start``, 1 at ``terminal``)."""

    def __init__(self, clips: list[data.Clip], device: torch.device) -> None:
        self.clips = clips
        self.device = device
        self.length = np.array([len(c) for c in clips], np.int64)
        self.start = np.concatenate([[0], np.cumsum(self.length)[:-1]]).astype(np.int64)
        self.success = np.array([c.success for c in clips], bool)
        self.obs = torch.from_numpy(np.concatenate([c.obs for c in clips])).to(device)
        self.actions = torch.from_numpy(np.concatenate([c.actions for c in clips])).to(device)
        self.phase = torch.from_numpy(np.concatenate(
            [np.linspace(0.0, 1.0, len(c), dtype=np.float32) for c in clips]
        )).to(device)
        self.time_to_end = torch.from_numpy(np.concatenate(
            [(c.t[-1] - c.t).astype(np.float32) for c in clips]
        )).to(device)
        self.step_success = torch.from_numpy(
            np.repeat(self.success, self.length).astype(np.float32)
        ).to(device)

    def clip_ids(self, which: np.ndarray | None = None) -> np.ndarray:
        ids = np.arange(len(self.clips))
        return ids if which is None else ids[which]

    def sample_clips(self, rng: np.random.Generator, ids: np.ndarray, n: int) -> np.ndarray:
        """``n`` clips of ``ids``, each picked in proportion to its length."""
        weights = self.length[ids].astype(float)
        return rng.choice(ids, size=n, p=weights / weights.sum())

    def sample_steps(self, rng: np.random.Generator, ids: np.ndarray, n: int) -> torch.Tensor:
        """Indices of ``n`` steps, uniform over the steps of clips ``ids``."""
        clips = self.sample_clips(rng, ids, n)
        offsets = (rng.random(n) * self.length[clips]).astype(np.int64)
        return torch.from_numpy(self.start[clips] + offsets).to(self.device)


def save_checkpoint(run_dir: str, cfg: TrainConfig, nets: dict[str, torch.nn.Module],
                    epoch: int, metrics: dict[str, float], **extra) -> None:
    path = os.path.join(run_dir, MODEL_NAME)
    torch.save({
        "method": cfg.method,
        "config": asdict(cfg),
        "state": {name: net.state_dict() for name, net in nets.items()},
        "epoch": epoch,
        "metrics": metrics,
        **extra,
    }, path + ".tmp")
    os.replace(path + ".tmp", path)


def write_eval(run_dir: str, epoch: int, rows: list[dict]) -> None:
    def plain(row: dict) -> dict:
        return {
            "name": row["name"], "label": row["label"],
            "t": [round(float(v), 4) for v in row["t"]],
            "reward": [float(v) for v in row["reward"]],
            "terms": {k: [float(x) for x in v] for k, v in row.get("terms", {}).items()},
        }

    with open(os.path.join(run_dir, EVAL_NAME), "w") as f:
        json.dump({"epoch": epoch, "recordings": [plain(r) for r in rows]}, f)


def run_training(
    method, cfg: TrainConfig, report: Report, cancelled: Cancelled, log=print,
) -> dict:
    """Trains ``method`` (a module with ``NAME``, ``METRIC`` and ``train``) as ``cfg`` says.
    Returns the result: success, message, run_dir, wandb_url, the last train / val loss and
    the best validation metric."""
    seed_everything(cfg.seed)
    device = resolve_device(cfg.device)

    def loading(done: int, total: int, text: str) -> None:
        report(Feedback("loading", LOAD_SHARE * done / max(total, 1),
                        status=f"{done}/{total} recordings: {text}"))

    report(Feedback("loading", 0.0, status=f"reading {cfg.recordings_dir}"))
    clips, skipped = data.load_clips(cfg.recordings_dir, cfg.step_hz, loading, cancelled,
                                     episode_hz=cfg.episode_hz, modality=cfg.modality)
    if cancelled():
        raise Cancel()
    train, val = data.split_clips(clips, cfg.val_fraction, cfg.seed)
    n_success = sum(c.success for c in train)
    if n_success < 2:
        return {"success": False, "message": (
            f"{len(clips)} usable {cfg.episode_hz:g} Hz Sparsh-skin episodes for "
            f"{cfg.recordings_dir} ({n_success} "
            f"successes to train on); {len(skipped)} skipped"
        )}
    cfg.obs_mean, cfg.obs_std = data.obs_stats(
        cfg.recordings_dir, train, cfg.episode_hz
    ).as_lists()

    name = cfg.wandb_name or (
        f"{cfg.method}_{cfg.modality}_{cfg.episode_hz:g}hz_{datetime.now():%Y%m%d_%H%M%S}"
    )
    output_dir = cfg.output_dir or default_output_dir(cfg.recordings_dir, cfg.method)
    run_dir = os.path.join(output_dir, name)
    os.makedirs(run_dir, exist_ok=True)
    counts = {
        "train": len(train), "train_success": n_success,
        "val": len(val), "val_success": sum(c.success for c in val), "skipped": len(skipped),
        # The Sparsh-skin episodes' rate (Processing tab's Rate) and the rate actually trained
        # at (step_hz rounded to a whole stride of it), to compare runs across rates.
        "episode_hz": cfg.episode_hz,
        "trained_hz": sorted({round(c.clip_hz, 3) for c in clips}),
    }
    log(f"Run {run_dir}: {counts}")
    logger = RunLogger(run_dir, cfg.wandb, cfg.wandb_project, name,
                       {**asdict(cfg), **counts}, cfg.env_file, log=log)
    with open(os.path.join(run_dir, CONFIG_NAME), "w") as f:
        json.dump({
            **asdict(cfg), "run_name": name, "device_used": str(device), "counts": counts,
            "wandb_url": logger.url, "train_recordings": [c.name for c in train],
            "val_recordings": [c.name for c in val], "skipped": skipped,
        }, f, indent=1)
    best = {"val_metric": float("nan"), "train_loss": float("nan"), "val_loss": float("nan")}
    try:
        report(Feedback("training", LOAD_SHARE, 0, cfg.epochs, val_metric_name=method.METRIC,
                        status=f"{counts['train']} train / {counts['val']} val recordings on "
                               f"{device}"))
        for epoch, result in method.train(cfg, train, val, device, logger, cancelled):
            better = epoch == 1 or (np.isfinite(result.val_metric) and (
                not np.isfinite(best["val_metric"]) or result.val_metric > best["val_metric"]
            ))
            if better:
                best = {"val_metric": result.val_metric}
                save_checkpoint(run_dir, cfg, result.nets, epoch, result.metrics, **result.extra)
                write_eval(run_dir, epoch, result.eval_rows)
                logger.summary({f"best/{method.METRIC}": result.val_metric, "best/epoch": epoch})
            best["train_loss"], best["val_loss"] = result.train_loss, result.val_loss
            report(Feedback(
                "training", LOAD_SHARE + (1 - LOAD_SHARE) * epoch / cfg.epochs, epoch,
                cfg.epochs, result.train_loss, result.val_loss, result.val_metric,
                method.METRIC, f"epoch {epoch}/{cfg.epochs}"
                + (" (best, saved)" if better else ""),
            ))
            if cancelled():
                raise Cancel()
    except Cancel:
        logger.finish()
        return {"success": False, "cancelled": True, "run_dir": run_dir, "wandb_url": logger.url,
                "message": f"cancelled; best epoch so far kept in {run_dir}", **best}
    logger.finish()
    return {
        "success": True, "run_dir": run_dir, "wandb_url": logger.url, **best,
        "message": f"trained {cfg.epochs} epochs, best {method.METRIC} "
                   f"{best['val_metric']:.3f}, saved in {run_dir}",
    }


def newest_run(runs_dir: str) -> str | None:
    """The run folder in ``runs_dir`` with the newest ``model.pt``."""
    runs = list_runs(runs_dir)
    return runs[0] if runs else None


def list_runs(runs_dir: str) -> list[str]:
    """Run folders in ``runs_dir`` that have a ``model.pt``, newest first."""
    if not os.path.isdir(runs_dir):
        return []
    runs = [os.path.join(runs_dir, d) for d in os.listdir(runs_dir)
            if os.path.isfile(os.path.join(runs_dir, d, MODEL_NAME))]
    return sorted(runs, key=lambda r: os.path.getmtime(os.path.join(r, MODEL_NAME)), reverse=True)


def load_checkpoint(run_dir: str, device: torch.device) -> dict:
    """A run's ``model.pt``; raises ValueError for one trained on camera frames by an older
    version of this package (no ``obs_mean``)."""
    ckpt = torch.load(os.path.join(run_dir, MODEL_NAME), map_location=device, weights_only=False)
    if not ckpt["config"].get("obs_mean"):
        raise ValueError(f"{os.path.basename(run_dir)} was trained on camera frames by an older "
                         "version; train a new run on the Sparsh-skin episodes")
    return ckpt


def config_from_checkpoint(ckpt: dict) -> TrainConfig:
    names = {f.name for f in fields(TrainConfig)}
    return TrainConfig(**{k: v for k, v in ckpt["config"].items() if k in names})


@torch.no_grad()
def batched(fn: Callable, n: int, size: int = 256) -> torch.Tensor:
    """``fn(slice)`` over ``range(n)`` in chunks of ``size``, concatenated."""
    return torch.cat([fn(slice(i, min(i + size, n))) for i in range(0, n, size)])
