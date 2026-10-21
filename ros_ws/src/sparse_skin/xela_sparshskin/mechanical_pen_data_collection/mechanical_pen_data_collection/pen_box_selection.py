"""Choosing one pen box for a recording from the SAM boxes seen during it.

The box moves and changes size while recording, e.g. it shrinks while a hand covers part of the
pen. A recording keeps the box most like the others:

1. Boxes much smaller than usual for the recording are left out: those whose area is under
   ``shrink_ratio`` of the ``ref_quantile`` quantile of all areas (an upper quantile, so the
   reference is the unhidden pen even if it was covered much of the time).
2. Of the rest, the box with the highest mean overlap (IoU of the rotated boxes) with all the
   others is kept; a tie goes to the higher detection score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import cv2
import numpy as np

SHRINK_RATIO = 0.7
REF_QUANTILE = 0.75


@dataclass
class BoxChoice:
    index: int  # of the chosen box in the boxes given
    kept: int  # boxes compared (not shrunken)
    shrunken: int  # boxes left out as shrunken
    mean_iou: float  # of the chosen box with the other kept ones (1.0 if it is alone)
    ref_area: float  # area the shrink test compares with (px^2)


def box_area(corners: np.ndarray) -> float:
    return float(abs(cv2.contourArea(np.asarray(corners, dtype=np.float32))))


def box_iou(a: np.ndarray, b: np.ndarray) -> float:
    """Intersection over union of two convex quadrilaterals (4, 2)."""
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    area_a, area_b = box_area(a), box_area(b)
    if area_a <= 0.0 or area_b <= 0.0:
        return 0.0
    # Both must wind the same way for the convex intersection.
    a = cv2.convexHull(a).reshape(-1, 2)
    b = cv2.convexHull(b).reshape(-1, 2)
    inter, _ = cv2.intersectConvexConvex(a, b)
    union = area_a + area_b - inter
    return float(inter / union) if union > 0.0 else 0.0


def choose_consistent_box(
    corners: Sequence[np.ndarray],
    scores: Sequence[float] | None = None,
    shrink_ratio: float = SHRINK_RATIO,
    ref_quantile: float = REF_QUANTILE,
) -> BoxChoice | None:
    """The box (4, 2 corners each) most like the others, leaving out shrunken ones; None if
    there are no boxes."""
    n = len(corners)
    if n == 0:
        return None
    scores = list(scores) if scores is not None else [0.0] * n
    areas = np.array([box_area(c) for c in corners])
    ref = float(np.quantile(areas, ref_quantile))
    kept = [i for i in range(n) if areas[i] >= shrink_ratio * ref]
    if not kept:  # only when every area is 0
        kept = list(range(n))
    if len(kept) == 1:
        return BoxChoice(kept[0], 1, n - 1, 1.0, ref)
    iou = np.eye(len(kept))
    for a in range(len(kept)):
        for b in range(a + 1, len(kept)):
            iou[a, b] = iou[b, a] = box_iou(corners[kept[a]], corners[kept[b]])
    mean = (iou.sum(axis=1) - 1.0) / (len(kept) - 1)
    best = max(range(len(kept)), key=lambda k: (round(float(mean[k]), 9), scores[kept[k]]))
    return BoxChoice(kept[best], len(kept), n - len(kept), float(mean[best]), ref)
