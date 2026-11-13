"""What the reward methods and the comparison share: window indexing, the per-recording
validation summary and its plots, and the method-agnostic comparison metrics.

A *row* is one scored recording: ``{"name", "label", "t" (from 0), "reward", "terms"}`` (the
``eval_rows`` of ``training.EpochResult``). Its *progress* is ``terms["progress"]`` when the
method has one, else the reward itself (Coupled Local Global's global reward).
"""

from __future__ import annotations

import numpy as np

from reward_models import data
from reward_models.networks import auc, nanmean, spearman


def progress_of(row: dict) -> np.ndarray:
    return np.asarray(row["terms"].get("progress", row["reward"]), float)


def window_index(start: np.ndarray, pos: np.ndarray, context: int) -> np.ndarray:
    """(B, context) step indices of the ``context`` steps ending at clip position ``pos`` of
    clips starting at ``start``; positions before the clip's first step repeat it."""
    offsets = np.arange(context) - (context - 1)
    return start[:, None] + np.maximum(pos[:, None] + offsets[None], 0)


def summary_metrics(rows: list[dict]) -> dict[str, float]:
    """The validation numbers every method logs: progress vs time on successes, episode
    reward and final progress of successes vs failures."""
    rho, returns, final = [], {data.SUCCESS: [], data.FAILURE: []}, {
        data.SUCCESS: [], data.FAILURE: []}
    for r in rows:
        p = progress_of(r)
        if r["label"] == data.SUCCESS:
            rho.append(spearman(np.asarray(r["t"]), p))
        returns[r["label"]].append(float(np.mean(r["reward"])))
        final[r["label"]].append(float(p[-1]))
    return {
        "val/spearman": nanmean(rho),
        "val/return_success": nanmean(returns[data.SUCCESS]),
        "val/return_failure": nanmean(returns[data.FAILURE]),
        "val/return_auc": auc(returns[data.SUCCESS], returns[data.FAILURE]),
        "val/final_progress_success": nanmean(final[data.SUCCESS]),
        "val/final_progress_failure": nanmean(final[data.FAILURE]),
    }


def log_plots(logger, step: int, rows: list[dict], n: int) -> None:
    shown = ([r for r in rows if r["label"] == data.SUCCESS][: (n + 1) // 2]
             + [r for r in rows if r["label"] == data.FAILURE][: n // 2])
    name = lambda r: f"{r['name']} ({r['label']})"  # noqa: E731
    logger.curves(step, "val/progress_curves", {name(r): (r["t"], progress_of(r)) for r in shown},
                  "Progress over validation recordings")
    logger.curves(step, "val/reward_curves", {name(r): (r["t"], r["reward"]) for r in shown},
                  "Reward over validation recordings")


# ---- the comparison ---------------------------------------------------------------------------

# name: (what it measures, higher is better). All are rank based, so rewards of different
# scales (log-probabilities, temporal distances, two-hot values) compare directly.
COMPARISON_METRICS = {
    "return_auc": "mean reward per step of an episode, successes ranked above failures",
    "pre_end_return_auc": "the same without the last end_window_s (before the click is near)",
    "step_auc": "reward of single steps, success steps ranked above failure steps",
    "progress_spearman": "rank correlation of progress with time, mean over successes",
    "final_progress_auc": "progress over the last end_window_s, successes above failures",
    "success_rise_rate": "share of successes whose progress ends above where it starts",
}


def comparison_metrics(rows: list[dict], end_window_s: float = 1.0) -> dict[str, float]:
    ret, pre, steps, final = ({data.SUCCESS: [], data.FAILURE: []} for _ in range(4))
    rho, rise = [], []
    for r in rows:
        t = np.asarray(r["t"], float)
        reward = np.asarray(r["reward"], float)
        p = progress_of(r)
        end = t >= t[-1] - end_window_s
        lab = r["label"]
        ret[lab].append(float(reward.mean()))
        if (~end).any():
            pre[lab].append(float(reward[~end].mean()))
        steps[lab].append(reward)
        final[lab].append(float(p[end].mean()))
        if lab == data.SUCCESS:
            rho.append(spearman(t, p))
            k = max(1, int(end.sum()))
            rise.append(float(p[-k:].mean() > p[:k].mean()))
    cat = lambda xs: np.concatenate(xs) if xs else np.zeros(0)  # noqa: E731
    return {
        "return_auc": auc(ret[data.SUCCESS], ret[data.FAILURE]),
        "pre_end_return_auc": auc(pre[data.SUCCESS], pre[data.FAILURE]),
        "step_auc": auc(cat(steps[data.SUCCESS]), cat(steps[data.FAILURE])),
        "progress_spearman": nanmean(rho),
        "final_progress_auc": auc(final[data.SUCCESS], final[data.FAILURE]),
        "success_rise_rate": nanmean(rise),
    }
