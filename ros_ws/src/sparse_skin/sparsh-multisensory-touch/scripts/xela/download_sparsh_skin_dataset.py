#!/usr/bin/env python3
"""Download Sparsh-Skin / Xela data from Hugging Face for the visualizer (or training).

Dataset: https://huggingface.co/datasets/facebook/sparsh-skin-dataset

Layout on HF mirrors the README (`pretraining/{object}/{id}/…`, `baseline/`, `urdf/`).
Configs expect that tree under:
  {out_dir}/xela/pretraining/extracted/

Example (minimal ~300 MB, enough for visualizer.py):
  python3 scripts/xela/download_sparsh_skin_dataset.py

Then:
  python3 -m tactile_ssl.data.xela.visualizer \\
    --urdf-path data/xela/pretraining/extracted/urdf/ahrcpcpn.urdf \\
    --data-path data/xela/pretraining/extracted/ball/0 \\
    --baseline-signal-path data/xela/pretraining/extracted/baseline/xela/data.pkl
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

HF_REPO = "facebook/sparsh-skin-dataset"
OBJECTS = (
    "ball",
    "corn",
    "cup",
    "drill",
    "lego",
    "legopool",
    "loofah",
    "metalcup",
    "mustard",
    "popcorn",
    "pringle",
    "rubikscube",
    "slipper",
    "watermelon",
)


def _require_hf():
    try:
        from huggingface_hub import hf_hub_download, snapshot_download
    except ImportError as e:
        raise SystemExit(
            "huggingface_hub is required. Install with:\n  pip install huggingface_hub"
        ) from e
    return hf_hub_download, snapshot_download


def _extract_root(out_dir: Path) -> Path:
    """Match config/data/xela.yaml: ${data_root}/xela/pretraining/extracted."""
    root = out_dir / "xela" / "pretraining" / "extracted"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _download_file(hf_hub_download, repo_path: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"[skip] {dest}")
        return dest
    print(f"[get]  {repo_path} -> {dest}")
    cached = hf_hub_download(
        repo_id=HF_REPO,
        repo_type="dataset",
        filename=repo_path,
    )
    shutil.copy2(cached, dest)
    return dest


def download_visualizer_bundle(
    out_dir: Path,
    object_name: str,
    sequence_id: int,
    include_forces: bool,
) -> Path:
    """Baseline + URDF + one teleop sequence (no camera images)."""
    hf_hub_download, _ = _require_hf()
    root = _extract_root(out_dir)

    files = [
        "pretraining/baseline/xela/data.pkl",
        "pretraining/urdf/ahrcpcpn.urdf",
        f"pretraining/{object_name}/{sequence_id}/xela/data.pkl",
        f"pretraining/{object_name}/{sequence_id}/allegro/data.pkl",
    ]
    if include_forces:
        files.extend(
            [
                "pretraining/baseline/xela/forces.pkl",
                f"pretraining/{object_name}/{sequence_id}/xela/forces.pkl",
            ]
        )

    for repo_path in files:
        rel = Path(repo_path).relative_to("pretraining")
        _download_file(hf_hub_download, repo_path, root / rel)

    return root


def download_snapshot(
    out_dir: Path,
    allow_patterns: list[str],
    ignore_patterns: list[str] | None,
) -> Path:
    _, snapshot_download = _require_hf()
    root = _extract_root(out_dir)
    # HF paths are pretraining/…; stage under a temp dir then flatten into extracted/.
    stage = out_dir / "xela" / "_hf_download"
    stage.mkdir(parents=True, exist_ok=True)
    print(f"[snapshot] {HF_REPO} -> {root}")
    print(f"  allow:  {allow_patterns}")
    if ignore_patterns:
        print(f"  ignore: {ignore_patterns}")
    snapshot_download(
        repo_id=HF_REPO,
        repo_type="dataset",
        allow_patterns=allow_patterns,
        ignore_patterns=ignore_patterns,
        local_dir=stage,
        local_dir_use_symlinks=False,
    )
    staged_pretraining = stage / "pretraining"
    if not staged_pretraining.exists():
        raise SystemExit(f"Expected {staged_pretraining} after download")
    for child in staged_pretraining.iterdir():
        dest = root / child.name
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()
        shutil.move(str(child), str(dest))
    shutil.rmtree(stage, ignore_errors=True)
    return root


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Download facebook/sparsh-skin-dataset for Sparsh-Skin / visualizer."
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data"),
        help="Data root (default: ./data). Files land in "
        "{out-dir}/xela/pretraining/extracted/ … matching config/data/xela.yaml.",
    )
    p.add_argument(
        "--mode",
        choices=("visualizer", "objects", "full-pretraining"),
        default="visualizer",
        help="visualizer: baseline+urdf+one sequence (~0.3 GB). "
        "objects: chosen objects (all sequence ids). "
        "full-pretraining: entire pretraining tree (~tens of GB).",
    )
    p.add_argument(
        "--object",
        default="ball",
        choices=OBJECTS,
        help="Object folder for --mode visualizer (default: ball).",
    )
    p.add_argument(
        "--sequence-id",
        type=int,
        default=0,
        help="Sequence id for --mode visualizer (default: 0).",
    )
    p.add_argument(
        "--objects",
        nargs="+",
        default=["ball"],
        choices=OBJECTS,
        help="Object folders for --mode objects (default: ball).",
    )
    p.add_argument(
        "--include-forces",
        action="store_true",
        help="Also download forces.pkl (not required by visualizer).",
    )
    p.add_argument(
        "--include-cameras",
        action="store_true",
        help="Include camera / realsense images (large; skipped by default).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = args.out_dir.resolve()
    ignore = None
    if not args.include_cameras:
        ignore = [
            "**/left_camera/**",
            "**/top_camera/**",
            "**/realsense/**",
        ]

    if args.mode == "visualizer":
        root = download_visualizer_bundle(
            out_dir,
            object_name=args.object,
            sequence_id=args.sequence_id,
            include_forces=args.include_forces,
        )
        data_path = root / args.object / str(args.sequence_id)
        urdf = root / "urdf" / "ahrcpcpn.urdf"
        baseline = root / "baseline" / "xela" / "data.pkl"
        print("\nDone. Run the visualizer with:\n")
        print(
            "python3 -m tactile_ssl.data.xela.visualizer \\\n"
            f"  --urdf-path {urdf} \\\n"
            f"  --data-path {data_path} \\\n"
            f"  --baseline-signal-path {baseline}"
        )
        return

    if args.mode == "objects":
        patterns = ["pretraining/urdf/**", "pretraining/baseline/xela/data.pkl"]
        if args.include_forces:
            patterns.append("pretraining/baseline/xela/forces.pkl")
        for obj in args.objects:
            patterns.append(f"pretraining/{obj}/**/xela/data.pkl")
            patterns.append(f"pretraining/{obj}/**/allegro/data.pkl")
            if args.include_forces:
                patterns.append(f"pretraining/{obj}/**/xela/forces.pkl")
            if args.include_cameras:
                patterns.append(f"pretraining/{obj}/**/left_camera/**")
                patterns.append(f"pretraining/{obj}/**/top_camera/**")
        root = download_snapshot(out_dir, patterns, ignore)
        print(f"\nDone. Extracted tree: {root}")
        return

    if args.mode == "full-pretraining":
        patterns = ["pretraining/**"]
        root = download_snapshot(out_dir, patterns, ignore)
        print(f"\nDone. Full pretraining tree: {root}")
        print(
            "Set paths.data_root to "
            f"{out_dir} so config resolves "
            "xela/pretraining/extracted/…"
        )
        return

    raise SystemExit(f"Unknown mode: {args.mode}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
