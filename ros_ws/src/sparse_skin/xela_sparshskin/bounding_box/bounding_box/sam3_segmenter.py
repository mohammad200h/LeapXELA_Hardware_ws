"""SAM 3 text-prompt segmenter used to find the pen in an RGB frame."""

from __future__ import annotations

import os
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image as PILImage


@dataclass
class Segment:
    """One instance mask from SAM 3."""

    mask: np.ndarray
    score: float


def _to_numpy(value):
    if value is None:
        return None
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    return np.asarray(value)


def _looks_like_result(obj) -> bool:
    return hasattr(obj, "masks") or hasattr(obj, "boxes")


def _resize_mask(mask: np.ndarray, height: int, width: int) -> np.ndarray:
    mask = np.squeeze(mask)
    if mask.shape != (height, width):
        mask = cv2.resize(
            mask.astype(np.float32),
            (width, height),
            interpolation=cv2.INTER_LINEAR,
        )
    return (mask > 0.5).astype(np.uint8) * 255


def _segments_from_arrays(masks, boxes, height: int, width: int) -> list[Segment]:
    data = _to_numpy(masks)
    if data is None or data.size == 0:
        return []
    data = np.squeeze(data)
    if data.ndim == 2:
        data = data[None, ...]
    conf = None
    if boxes is not None:
        conf = _to_numpy(getattr(boxes, "conf", boxes))
        if conf is not None and conf.ndim == 2 and conf.shape[1] >= 5:
            conf = conf[:, 4]
    if conf is None or len(conf) != len(data):
        conf = np.ones(len(data), dtype=np.float32)
    return [
        Segment(mask=_resize_mask(mask, height, width), score=float(score))
        for mask, score in zip(data, conf)
    ]


def _as_results(raw) -> list:
    if raw is None:
        return []
    if _looks_like_result(raw):
        return [raw]
    if isinstance(raw, (list, tuple)):
        return list(raw)
    try:
        return list(raw)
    except TypeError:
        return [raw]


def _masks_from_result(result, height: int, width: int) -> list[Segment]:
    masks_obj = getattr(result, "masks", None)
    if masks_obj is None:
        return []
    data = getattr(masks_obj, "data", masks_obj)
    return _segments_from_arrays(data, getattr(result, "boxes", None), height, width)


class Sam3Segmenter:
    """Load Ultralytics SAM 3 once and run text-prompt inference on RGB frames."""

    def __init__(self, model: str, conf: float, device: str = "") -> None:
        try:
            from ultralytics.models.sam import SAM3SemanticPredictor
        except ImportError as exc:
            raise ImportError(
                "ultralytics is required for SAM 3. Install it with "
                "`pip install -U ultralytics` and download gated weights from "
                "https://huggingface.co/facebook/sam3"
            ) from exc

        model_path = os.path.expanduser(model)
        overrides = {
            "conf": conf,
            "task": "segment",
            "mode": "predict",
            "model": model_path,
            "quantize": 16,
            "save": False,
            "verbose": False,
        }
        if device:
            overrides["device"] = device
        self._predictor = SAM3SemanticPredictor(overrides=overrides)
        if hasattr(self._predictor, "setup_model"):
            self._predictor.setup_model()

    def segment(self, rgb: np.ndarray, prompt: str) -> list[Segment]:
        """Return instance masks for ``prompt`` on an (H, W, 3) RGB image."""
        height, width = rgb.shape[:2]
        image = PILImage.fromarray(rgb)
        self._predictor.set_image(image)
        raw = self._predictor(text=[prompt])
        segments: list[Segment] = []
        if _looks_like_result(raw):
            segments.extend(_masks_from_result(raw, height, width))
        elif isinstance(raw, (list, tuple)) and raw and not _looks_like_result(raw[0]):
            masks = raw[0]
            boxes = raw[1] if len(raw) > 1 else None
            segments.extend(_segments_from_arrays(masks, boxes, height, width))
        else:
            for result in _as_results(raw):
                segments.extend(_masks_from_result(result, height, width))
        segments.sort(key=lambda item: item.score, reverse=True)
        return segments
