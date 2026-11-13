"""Metrics of the reward model runs: a local ``metrics.jsonl`` and Weights & Biases.

W&B is set up as LEQ_DV3 does (``dreamerv3/main.py`` ``make_logger``, and its training
instructions): the API key is ``WANDB_API_KEY`` from the environment or from LEQ_DV3's
``.env`` (``DEFAULT_ENV_FILE``, ``KEY=VALUE`` lines), else the cached ``wandb login``;
``WANDB_PROJECT`` / ``WANDB_NAME`` override the project / run name and ``WANDB_ENABLE=False``
turns it off. ``metrics.jsonl`` (one ``{"step", ...metrics}`` per line) is always written next to
the run, so the GUI can plot a run without W&B.
"""

from __future__ import annotations

import json
import os
import time

import numpy as np

DEFAULT_ENV_FILE = "/workspace/LeapXELA_Hardware_ws/LEQ_DV3/.env"
DEFAULT_PROJECT = "reward_models"
METRICS_NAME = "metrics.jsonl"


def load_env_file(path: str) -> None:
    """Sets the ``KEY=VALUE`` lines of ``path`` (``export`` and quotes allowed) that are not in
    the environment already."""
    if not path or not os.path.isfile(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[len("export "):]
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def wandb_enabled(requested: bool) -> bool:
    return requested and os.environ.get("WANDB_ENABLE", "True").lower() not in ("false", "0", "no")


class RunLogger:
    """Logs scalars (and W&B plots) of one run. ``use_wandb`` False (or W&B failing to start)
    keeps only ``metrics.jsonl``."""

    def __init__(
        self, run_dir: str, use_wandb: bool, project: str, name: str, config: dict,
        env_file: str = DEFAULT_ENV_FILE, job_type: str = "train", log=print,
    ) -> None:
        self.run_dir = run_dir
        self._log = log
        self._wandb = None
        self._run = None
        self.url = ""
        os.makedirs(run_dir, exist_ok=True)
        self._metrics = open(os.path.join(run_dir, METRICS_NAME), "a")
        load_env_file(env_file)
        if not wandb_enabled(use_wandb):
            return
        try:
            import wandb

            if os.environ.get("WANDB_API_KEY"):
                wandb.login(key=os.environ["WANDB_API_KEY"], relogin=False)
            self._run = wandb.init(
                project=os.environ.get("WANDB_PROJECT") or project or DEFAULT_PROJECT,
                name=os.environ.get("WANDB_NAME") or name,
                config=config, dir=run_dir, job_type=job_type, reinit=True,
            )
            self._wandb = wandb
            self.url = self._run.url or ""
        except Exception as e:  # noqa: BLE001 - training goes on without W&B
            self._log(f"W&B not started ({e}); logging to {METRICS_NAME} only")

    def scalars(self, step: int, metrics: dict[str, float]) -> None:
        clean = {k: float(v) for k, v in metrics.items() if v is not None and np.isfinite(v)}
        self._metrics.write(json.dumps({"step": int(step), "time": time.time(), **clean}) + "\n")
        self._metrics.flush()
        if self._run is not None:
            self._run.log(clean, step=int(step))

    def curves(self, step: int, key: str, curves: dict[str, tuple[np.ndarray, np.ndarray]],
               title: str, xname: str = "t (s)") -> None:
        """A W&B line plot of several (x, y) curves (one per recording)."""
        if self._run is None or not curves:
            return
        names = list(curves)
        plot = self._wandb.plot.line_series(
            xs=[list(map(float, curves[n][0])) for n in names],
            ys=[list(map(float, curves[n][1])) for n in names],
            keys=names, title=title, xname=xname,
        )
        self._run.log({key: plot}, step=int(step))

    def table(self, step: int, key: str, columns: list[str], rows: list[list]) -> None:
        if self._run is None or not rows:
            return
        self._run.log({key: self._wandb.Table(columns=columns, data=rows)}, step=int(step))

    def summary(self, values: dict) -> None:
        if self._run is not None:
            for k, v in values.items():
                self._run.summary[k] = v

    def finish(self) -> None:
        self._metrics.close()
        if self._run is not None:
            self._run.finish()
            self._run = None


def read_metrics(run_dir: str) -> list[dict]:
    """The rows of a run's ``metrics.jsonl`` (empty when it has none)."""
    rows = []
    try:
        with open(os.path.join(run_dir, METRICS_NAME)) as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return rows
