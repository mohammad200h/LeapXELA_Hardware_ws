"""Locate the Hunyuan3D-Part checkout and make its demo importable."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import torch

UPSTREAM_URL = "https://github.com/Tencent-Hunyuan/Hunyuan3D-Part.git"
_HARDCODED_COUNTS = (
    "    point_num = 100000\n"
    "    prompt_num = 400\n"
    "    with Timer(\"获取邻接面片\"):\n"
)
_HONORED_COUNTS = "    with Timer(\"获取邻接面片\"):\n"
_EMPTY_BATCH = (
    "            cur_propmt = _point_prompts[bs * i : bs * (i + 1)]\n"
    "            pred_mask_1, pred_mask_2, pred_mask_3, pred_iou = get_mask(\n"
)
_SKIP_EMPTY_BATCH = (
    "            cur_propmt = _point_prompts[bs * i : bs * (i + 1)]\n"
    "            if len(cur_propmt) == 0:\n"
    "                continue\n"
    "            pred_mask_1, pred_mask_2, pred_mask_3, pred_iou = get_mask(\n"
)


def default_root() -> Path:
    """Return the checkout path from ``P3_SAM_ROOT`` or the user cache."""
    env = os.environ.get("P3_SAM_ROOT")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".cache" / "p3_sam" / "Hunyuan3D-Part"


def prepare_upstream(root: Path | None = None) -> Path:
    """Clone Hunyuan3D-Part if needed and patch the demo so CLI sizes apply."""
    checkout = (root or default_root()).expanduser().resolve()
    demo = checkout / "P3-SAM" / "demo" / "auto_mask.py"
    if not demo.is_file():
        checkout.parent.mkdir(parents=True, exist_ok=True)
        subprocess.check_call(
            ["git", "clone", "--depth", "1", UPSTREAM_URL, str(checkout)]
        )
    _patch_file(
        demo,
        _HARDCODED_COUNTS,
        _HONORED_COUNTS,
    )
    _patch_file(demo, _EMPTY_BATCH, _SKIP_EMPTY_BATCH)
    model = checkout / "P3-SAM" / "model.py"
    sonata_root = Path.home() / ".cache" / "p3_sam" / "sonata"
    _patch_file(
        model,
        "download_root='/root/sonata'",
        f"download_root='{sonata_root}'",
    )
    _patch_file(
        model,
        "os.path.join(os.path.expanduser('~'), '/.cache/p3sam/weights')",
        "os.path.join(os.path.expanduser('~'), '.cache', 'p3_sam', 'weights')",
    )
    # The published Sonata config asks for flash-attn. The demo already has the
    # math-attention switch; turn it on so the node runs without that package.
    sonata_model = checkout / "XPart" / "partgen" / "models" / "sonata" / "model.py"
    _patch_file(
        sonata_model,
        "    # ckpt[\"config\"]['enable_flash'] = False\n",
        "    ckpt[\"config\"]['enable_flash'] = False\n",
    )
    return checkout


def import_auto_mask(root: Path | None = None):
    """Import ``demo.auto_mask`` from the prepared checkout."""
    checkout = prepare_upstream(root)
    _install_torch_scatter_shim()
    p3_sam = checkout / "P3-SAM"
    for entry in (p3_sam / "demo", p3_sam, checkout / "XPart" / "partgen"):
        path = str(entry)
        if path not in sys.path:
            sys.path.insert(0, path)
    import auto_mask  # noqa: WPS433  upstream demo module

    auto_mask.Timer.STATE = False
    return auto_mask


def _patch_file(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if old not in text:
        return
    path.write_text(text.replace(old, new, 1))


def _install_torch_scatter_shim() -> None:
    """Provide ``segment_csr`` when the CUDA ``torch_scatter`` wheel is absent."""
    try:
        import torch_scatter  # noqa: F401
    except ImportError:
        sys.modules["torch_scatter"] = _ScatterShim()


class _ScatterShim:
    """Stand-in for the ``torch_scatter.segment_csr`` calls Sonata makes."""

    @staticmethod
    def segment_csr(src, indptr, out=None, reduce="sum"):
        """Reduce ``src`` over the CSR segments described by ``indptr``."""
        reduce_name = {
            "sum": "sum",
            "add": "sum",
            "mean": "mean",
            "max": "amax",
            "min": "amin",
        }[reduce]
        indptr = indptr.to(device=src.device, dtype=torch.long)
        lengths = (indptr[1:] - indptr[:-1]).clamp(min=0)
        segment_ids = torch.repeat_interleave(
            torch.arange(lengths.numel(), device=src.device),
            lengths,
        )
        if segment_ids.numel() != src.shape[0]:
            raise ValueError(
                "segment_csr length mismatch: "
                f"src {src.shape[0]} vs indptr {int(segment_ids.numel())}"
            )
        index = segment_ids.view(-1, *([1] * (src.dim() - 1))).expand_as(src)
        reduced = torch.zeros(
            lengths.numel(),
            *src.shape[1:],
            device=src.device,
            dtype=src.dtype,
        ).scatter_reduce(0, index, src, reduce=reduce_name, include_self=False)
        if out is not None:
            out.copy_(reduced)
            return out
        return reduced
