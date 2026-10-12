"""Turn a SAM 3 mask into a bounding box aligned with the object's principal axis."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

CLOSE_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
BEST_COLOR = (46, 204, 113)
OTHER_COLOR = (241, 196, 15)
LABEL_COLOR = (255, 255, 255)


@dataclass
class PenBox:
    """Geometry of one pen instance, derived from its mask."""

    mask: np.ndarray
    score: float
    best: bool
    xyxy: tuple[int, int, int, int]
    center: tuple[float, float]
    size: tuple[float, float]
    angle_deg: float
    corners: np.ndarray
    depth_refined: bool = False


def close_mask(mask: np.ndarray) -> np.ndarray:
    """Fill small holes in a uint8 mask."""
    binary = (mask > 0).astype(np.uint8) * 255
    return cv2.morphologyEx(binary, cv2.MORPH_CLOSE, CLOSE_KERNEL)


def refine_mask_with_depth(
    mask: np.ndarray,
    depth_mm: np.ndarray,
    min_depth: float,
    max_depth: float,
    z_mad_scale: float = 4.0,
) -> tuple[np.ndarray, bool]:
    """Drop mask pixels whose aligned depth is invalid or far from the median."""
    if depth_mm.shape[:2] != mask.shape[:2]:
        return mask, False
    depth_m = depth_mm.astype(np.float32) / 1000.0
    valid = (mask > 0) & np.isfinite(depth_m) & (depth_m >= min_depth) & (depth_m <= max_depth)
    if int(valid.sum()) < 20:
        return mask, False
    zs = depth_m[valid]
    median = float(np.median(zs))
    mad = float(np.median(np.abs(zs - median)))
    spread = mad if mad > 1e-4 else 0.01
    thresh = max(0.02, z_mad_scale * spread)
    refined = valid & (np.abs(depth_m - median) <= thresh)
    if int(refined.sum()) < 20:
        return (valid.astype(np.uint8) * 255), True
    return (refined.astype(np.uint8) * 255), True


def principal_axis_rect(xs: np.ndarray, ys: np.ndarray):
    """Fit a rectangle whose long side follows the mask covariance axis."""
    pts = np.column_stack((xs.astype(np.float64), ys.astype(np.float64)))
    mean = pts.mean(axis=0)
    centered = pts - mean
    cov = centered.T @ centered / float(pts.shape[0])
    eigvals, eigvecs = np.linalg.eigh(cov)
    major = eigvecs[:, int(np.argmax(eigvals))]
    if major[0] < 0.0:
        major = -major
    angle = float(np.arctan2(major[1], major[0]))
    along = np.array([np.cos(angle), np.sin(angle)])
    across = np.array([-np.sin(angle), np.cos(angle)])
    local_x = centered @ along
    local_y = centered @ across
    min_x, max_x = float(local_x.min()), float(local_x.max())
    min_y, max_y = float(local_y.min()), float(local_y.max())
    center = mean + 0.5 * (min_x + max_x) * along + 0.5 * (min_y + max_y) * across
    corners = np.array(
        [
            mean + lx * along + ly * across
            for lx, ly in (
                (min_x, min_y),
                (max_x, min_y),
                (max_x, max_y),
                (min_x, max_y),
            )
        ],
        dtype=np.float32,
    )
    return (
        (float(center[0]), float(center[1])),
        (max_x - min_x, max_y - min_y),
        float(np.degrees(angle)),
        corners,
    )


def mask_to_box(mask: np.ndarray, score: float, best: bool) -> PenBox | None:
    """Build a principal-axis bounding box from a binary mask."""
    closed = close_mask(mask)
    ys, xs = np.nonzero(closed)
    if xs.size == 0:
        return None
    x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
    if xs.size < 4:
        cx = 0.5 * (x1 + x2)
        cy = 0.5 * (y1 + y2)
        width, height = float(x2 - x1 + 1), float(y2 - y1 + 1)
        angle_deg = 0.0
        corners = np.array(
            [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
            dtype=np.float32,
        )
        center = (cx, cy)
        size = (width, height)
    else:
        center, size, angle_deg, corners = principal_axis_rect(xs, ys)
    return PenBox(
        mask=closed,
        score=score,
        best=best,
        xyxy=(x1, y1, x2, y2),
        center=center,
        size=size,
        angle_deg=angle_deg,
        corners=corners,
    )


def draw_boxes(rgb: np.ndarray, boxes: list[PenBox]) -> np.ndarray:
    """Overlay masks and principal-axis boxes on an RGB image."""
    vis = rgb.copy()
    overlay = vis.copy()
    for box in boxes:
        color = BEST_COLOR if box.best else OTHER_COLOR
        overlay[box.mask > 0] = color
    vis = cv2.addWeighted(overlay, 0.35, vis, 0.65, 0)
    for box in boxes:
        color = BEST_COLOR if box.best else OTHER_COLOR
        cv2.polylines(vis, [np.round(box.corners).astype(np.int32)], True, color, 2)
        top = int(np.min(box.corners[:, 1]))
        left = int(np.min(box.corners[:, 0]))
        label = f"{'pen' if box.best else 'pen?'} {box.score:.2f}"
        cv2.putText(
            vis,
            label,
            (left, max(top - 8, 16)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            LABEL_COLOR,
            2,
            cv2.LINE_AA,
        )
    return vis
