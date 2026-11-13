"""Train every reward method on every modality for several seeds, then compare them.

    python3 -m reward_models.compare \\
        --recordings-dir /workspace/LeapXELA_Hardware_ws/ros_ws/demonstrations/compose_playbacks

(from a shell where the workspace is sourced, or with ``reward_models`` and
``mechanical_pen_data_collection`` on ``PYTHONPATH``). The defaults train ``METHODS`` x
``sparsh`` / ``proprio`` x seeds 0, 1, 2 (30 runs) on the 10 Hz Sparsh-skin episodes, each step
of them (``episode_hz`` = ``step_hz`` = 10: no resampling at training time), without W&B.

Everything goes to ``--out`` (default ``<recordings>/reward_models/comparison/<time>``):

- ``runs/<method>_<modality>_s<seed>/``: each run as ``training.run_training`` writes it
  (``config.json``, ``metrics.jsonl``, ``model.pt`` of the best epoch, ``eval.json``) and a
  ``done.json`` once it has finished. A run with ``done.json`` is not trained again, so the
  same command with the same ``--out`` resumes after a stop (``--force`` retrains);
- ``results.csv``: one row per run, ``common.COMPARISON_METRICS`` on the run's own validation
  recordings (the seed's split, the same for every method and modality);
- ``summary.csv`` / ``summary.md``: mean and std over seeds per method and modality;
- ``metrics.png``: the summary as bars; ``curves_<modality>.png``: mean progress over
  normalised episode time, successes vs failures, per method (seed ``--seeds[0]``).

``--compare-only`` skips training and compares the finished runs in ``--out``.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import traceback
from dataclasses import asdict
from datetime import datetime

import numpy as np

from reward_models import (
    common, coupled_local_global, data, progressor, rank2reward, reds, sarm, sarm_failures,
    timerewarder,
)
from reward_models.training import TrainConfig, resolve_device, run_training

METHODS = {m.NAME: m for m in (rank2reward, timerewarder, progressor, reds,
                               coupled_local_global, sarm, sarm_failures)}
DONE_NAME = "done.json"
RATE_HZ = 10.0


def log(*args) -> None:
    print(f"[{datetime.now():%H:%M:%S}]", *args, flush=True)


def run_name(method: str, modality: str, seed: int) -> str:
    return f"{method}_{modality}_s{seed}"


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--recordings-dir", required=True)
    p.add_argument("--out", default="", help="default <recordings>/reward_models/comparison/<time>")
    p.add_argument("--methods", nargs="+", default=list(METHODS), choices=list(METHODS))
    p.add_argument("--modalities", nargs="+", default=list(data.MODALITIES),
                   choices=list(data.MODALITIES))
    p.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    p.add_argument("--hz", type=float, default=RATE_HZ,
                   help="the Sparsh-skin episodes' folder rate, trained at every step")
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--steps-per-epoch", type=int, default=200)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--learning-rate", type=float, default=3e-4)
    p.add_argument("--val-fraction", type=float, default=0.2)
    p.add_argument("--end-window-s", type=float, default=1.0,
                   help="the end of an episode that pre_end / final metrics leave out / use")
    p.add_argument("--device", default="cuda")
    p.add_argument("--wandb", action="store_true", help="also log each run to W&B")
    p.add_argument("--force", action="store_true", help="retrain runs that are done")
    p.add_argument("--compare-only", action="store_true")
    return p.parse_args(argv)


# ---- training ---------------------------------------------------------------------------------


def train_all(args, runs_dir: str) -> None:
    jobs = [(m, mod, seed) for seed in args.seeds for mod in args.modalities
            for m in args.methods]
    for k, (method, modality, seed) in enumerate(jobs, 1):
        name = run_name(method, modality, seed)
        run_dir = os.path.join(runs_dir, name)
        if os.path.isfile(os.path.join(run_dir, DONE_NAME)) and not args.force:
            log(f"({k}/{len(jobs)}) {name}: done, skipped")
            continue
        cfg = TrainConfig(
            method=method, recordings_dir=args.recordings_dir, output_dir=runs_dir,
            epochs=args.epochs, steps_per_epoch=args.steps_per_epoch,
            batch_size=args.batch_size, learning_rate=args.learning_rate,
            val_fraction=args.val_fraction, episode_hz=args.hz, step_hz=args.hz,
            modality=modality, seed=seed, wandb=args.wandb, wandb_name=name,
            device=args.device,
        )
        log(f"({k}/{len(jobs)}) {name}: training")
        start = time.time()
        last = [0.0]

        def report(fb) -> None:
            if fb.stage == "training" and fb.epoch and time.time() - last[0] > 30:
                last[0] = time.time()
                log(f"  {name} epoch {fb.epoch}/{fb.epochs} train {fb.train_loss:.4f} "
                    f"{fb.val_metric_name} {fb.val_metric:.4f}")

        try:
            result = run_training(METHODS[method], cfg, report, lambda: False,
                                  log=lambda m: log("  " + m))
        except Exception:  # noqa: BLE001 - one failed run does not stop the others
            log(f"  {name} FAILED\n{traceback.format_exc()}")
            continue
        if not result.get("success"):
            log(f"  {name} FAILED: {result.get('message')}")
            continue
        with open(os.path.join(result["run_dir"], DONE_NAME), "w") as f:
            json.dump({**{k: v for k, v in result.items() if isinstance(v, (str, float, int, bool))},
                       "seconds": time.time() - start, "config": asdict(cfg)}, f, indent=1)
        log(f"  {name}: {result['message']} ({time.time() - start:.0f} s)")


# ---- comparison -------------------------------------------------------------------------------


def finished_runs(runs_dir: str) -> list[dict]:
    runs = []
    for name in sorted(os.listdir(runs_dir)) if os.path.isdir(runs_dir) else []:
        run_dir = os.path.join(runs_dir, name)
        if not os.path.isfile(os.path.join(run_dir, DONE_NAME)):
            continue
        with open(os.path.join(run_dir, "config.json")) as f:
            cfg = json.load(f)
        with open(os.path.join(run_dir, DONE_NAME)) as f:
            done = json.load(f)
        runs.append({"name": name, "dir": run_dir, "method": cfg["method"],
                     "modality": cfg.get("modality", data.SPARSH), "seed": cfg["seed"],
                     "val": set(cfg["val_recordings"]), "seconds": done.get("seconds", np.nan),
                     "episode_hz": cfg["episode_hz"], "step_hz": cfg["step_hz"]})
    return runs


def compare(args, out: str, runs_dir: str) -> None:
    runs = [r for r in finished_runs(runs_dir)
            if r["method"] in args.methods and r["modality"] in args.modalities
            and r["seed"] in args.seeds]
    if not runs:
        log(f"no finished runs in {runs_dir}")
        return
    device = resolve_device(args.device)
    results, curves = [], {}
    for modality in sorted({r["modality"] for r in runs}):
        group = [r for r in runs if r["modality"] == modality]
        hz = {(r["episode_hz"], r["step_hz"]) for r in group}
        if len(hz) > 1:
            raise ValueError(f"{modality} runs were trained at different rates: {hz}")
        episode_hz, step_hz = hz.pop()
        log(f"loading the {episode_hz:g} Hz {modality} clips")
        clips, _ = data.load_clips(args.recordings_dir, step_hz, episode_hz=episode_hz,
                                   modality=modality)
        by_name = {c.name: c for c in clips}
        for r in group:
            model = METHODS[r["method"]].Model(r["dir"], device)
            val = [by_name[n] for n in sorted(r["val"]) if n in by_name]
            rows = []
            for clip in val:
                reward, terms = model(clip)
                rows.append({"name": clip.name, "label": clip.label, "t": clip.t - clip.t[0],
                             "reward": reward, "terms": terms})
            metrics = common.comparison_metrics(rows, args.end_window_s)
            results.append({"method": r["method"], "modality": modality, "seed": r["seed"],
                            "val_recordings": len(val), "train_seconds": r["seconds"],
                            **metrics})
            log(f"{r['name']}: " + ", ".join(f"{k} {v:.3f}" for k, v in metrics.items()))
            if r["seed"] == args.seeds[0]:
                curves[(modality, r["method"])] = mean_curves(rows)
            del model
    write_results(out, results)
    plot_metrics(out, results)
    plot_curves(out, curves)
    log(f"comparison written to {out}")


def mean_curves(rows: list[dict], bins: int = 50) -> dict[str, np.ndarray]:
    """Mean progress over normalised time (``bins`` points) of successes and failures, each run
    z-scored over all its validation steps so methods share an axis."""
    allp = np.concatenate([common.progress_of(r) for r in rows])
    mu, sd = allp.mean(), max(allp.std(), 1e-8)
    grid = np.linspace(0, 1, bins)
    out = {}
    for label in (data.SUCCESS, data.FAILURE):
        ys = [np.interp(grid, np.linspace(0, 1, len(r["t"])), (common.progress_of(r) - mu) / sd)
              for r in rows if r["label"] == label and len(r["t"]) > 1]
        if ys:
            out[label] = np.mean(ys, 0)
    return out


def write_results(out: str, results: list[dict]) -> None:
    metrics = list(common.COMPARISON_METRICS)
    with open(os.path.join(out, "results.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0]))
        w.writeheader()
        w.writerows(results)
    groups = sorted({(r["method"], r["modality"]) for r in results})
    summary = []
    for method, modality in groups:
        rs = [r for r in results if r["method"] == method and r["modality"] == modality]
        row = {"method": method, "modality": modality, "seeds": len(rs)}
        for m in metrics + ["train_seconds"]:
            v = np.asarray([r[m] for r in rs], float)
            v = v[np.isfinite(v)]
            row[f"{m}_mean"] = float(v.mean()) if len(v) else float("nan")
            row[f"{m}_std"] = float(v.std()) if len(v) else float("nan")
        summary.append(row)
    with open(os.path.join(out, "summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)
    best = {m: np.nanmax([s[f"{m}_mean"] for s in summary]) for m in metrics}
    lines = ["# Reward model comparison", "",
             f"{len(results)} runs; mean ± std over seeds, on each seed's validation recordings. "
             "Higher is better; the best mean per metric is in bold.", "",
             "| method | modality | " + " | ".join(metrics) + " | train s |",
             "|---|---|" + "---|" * (len(metrics) + 1)]
    for s in summary:
        cells = []
        for m in metrics:
            text = f"{s[f'{m}_mean']:.3f} ± {s[f'{m}_std']:.3f}"
            cells.append(f"**{text}**" if np.isclose(s[f"{m}_mean"], best[m]) else text)
        lines.append(f"| {s['method']} | {s['modality']} | " + " | ".join(cells)
                     + f" | {s['train_seconds_mean']:.0f} |")
    lines += ["", "## Metrics", ""] + [f"- **{k}**: {v}" for k, v in
                                       common.COMPARISON_METRICS.items()]
    with open(os.path.join(out, "summary.md"), "w") as f:
        f.write("\n".join(lines) + "\n")


def plot_metrics(out: str, results: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    metrics = list(common.COMPARISON_METRICS)
    methods = sorted({r["method"] for r in results})
    modalities = sorted({r["modality"] for r in results})
    fig, axes = plt.subplots(2, (len(metrics) + 1) // 2, figsize=(5 * ((len(metrics) + 1) // 2), 8),
                             squeeze=False)
    width = 0.8 / len(modalities)
    for ax, m in zip(axes.flat, metrics):
        for k, mod in enumerate(modalities):
            vals = [[r[m] for r in results if r["method"] == me and r["modality"] == mod]
                    for me in methods]
            mean = [np.nanmean(v) if v else np.nan for v in vals]
            std = [np.nanstd(v) if v else np.nan for v in vals]
            ax.bar(np.arange(len(methods)) + (k - (len(modalities) - 1) / 2) * width, mean,
                   width, yerr=std, capsize=3, label=mod)
        ax.set_title(m)
        ax.set_xticks(np.arange(len(methods)))
        ax.set_xticklabels(methods, rotation=30, ha="right")
        ax.axhline(0.5 if "auc" in m else 0.0, color="grey", lw=0.8, ls="--")
    for ax in list(axes.flat)[len(metrics):]:
        ax.axis("off")
    axes.flat[0].legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out, "metrics.png"), dpi=120)
    plt.close(fig)


def plot_curves(out: str, curves: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    for modality in sorted({k[0] for k in curves}):
        methods = sorted(m for mod, m in curves if mod == modality)
        fig, axes = plt.subplots(1, len(methods), figsize=(4 * len(methods), 3.5), squeeze=False)
        for ax, method in zip(axes[0], methods):
            for label, y in curves[(modality, method)].items():
                ax.plot(np.linspace(0, 1, len(y)), y, label=label)
            ax.set_title(method)
            ax.set_xlabel("episode time (normalised)")
        axes[0][0].set_ylabel("progress (z-scored)")
        axes[0][0].legend()
        fig.suptitle(f"{modality}: mean validation progress")
        fig.tight_layout()
        fig.savefig(os.path.join(out, f"curves_{modality}.png"), dpi=120)
        plt.close(fig)


def main(argv=None) -> int:
    args = parse_args(argv)
    out = args.out or os.path.join(data.runs_root(args.recordings_dir), "comparison",
                                   f"{datetime.now():%Y%m%d_%H%M%S}")
    runs_dir = os.path.join(out, "runs")
    os.makedirs(runs_dir, exist_ok=True)
    with open(os.path.join(out, "args.json"), "w") as f:
        json.dump(vars(args), f, indent=1)
    log(f"output: {out}")
    if not args.compare_only:
        train_all(args, runs_dir)
    compare(args, out, runs_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
