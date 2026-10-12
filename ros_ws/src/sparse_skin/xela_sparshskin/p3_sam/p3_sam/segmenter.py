"""Run P3-SAM part segmentation on a point cloud."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from p3_sam.upstream import import_auto_mask


@dataclass
class PartBox:
    """Axis-aligned box of one part, in the cloud frame."""

    part_id: int
    min_xyz: list[float]
    max_xyz: list[float]


@dataclass
class PartSegmentation:
    """Point labels and part boxes returned by P3-SAM."""

    points: np.ndarray
    labels: np.ndarray
    part_ids: list[int]
    boxes: list[PartBox]
    unlabeled_points: int = 0

    @property
    def part_count(self) -> int:
        """Count parts with a non-negative point label."""
        return len(self.part_ids)

    @property
    def point_count(self) -> int:
        """Count points that were segmented."""
        return int(self.points.shape[0])


def prepare_points(points: np.ndarray, point_num: int, seed: int) -> np.ndarray:
    """Drop invalid points and keep at most ``point_num`` of the rest."""
    cloud = np.asarray(points, dtype=np.float64)
    if cloud.ndim != 2 or cloud.shape[1] != 3:
        raise ValueError(f"points must have shape (N, 3), got {cloud.shape}")
    valid = np.isfinite(cloud).all(axis=1)
    valid &= np.linalg.norm(cloud, axis=1) > 1e-4
    cloud = cloud[valid]
    if cloud.shape[0] > point_num:
        choice = np.random.default_rng(seed).choice(cloud.shape[0], point_num, replace=False)
        cloud = cloud[choice]
    return np.ascontiguousarray(cloud)


def estimate_normals(points: np.ndarray) -> np.ndarray:
    """Estimate unit normals and aim them back at the camera origin."""
    import open3d as o3d

    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(np.asarray(points, dtype=np.float64))
    cloud.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamKNN(knn=20))
    cloud.orient_normals_towards_camera_location(camera_location=np.zeros(3))
    normals = np.asarray(cloud.normals, dtype=np.float64)
    bad = ~np.isfinite(normals).all(axis=1) | (np.linalg.norm(normals, axis=1) < 1e-8)
    normals[bad] = (0.0, 0.0, 1.0)
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    return normals


@dataclass
class P3SamSegmenter:
    """Load the P3-SAM weights once and segment point clouds."""

    ckpt_path: str = ""
    upstream_root: str = ""
    point_num: int = 20000
    prompt_num: int = 80
    prompt_bs: int = 8
    seed: int = 42
    stage_log: object = field(default=None, init=False, repr=False)
    _auto_mask: object = field(default=None, init=False, repr=False)

    def load(self) -> None:
        """Import the upstream model and move it to CUDA."""
        import os

        import torch

        if not torch.cuda.is_available():
            raise RuntimeError("P3-SAM needs a CUDA GPU")
        torch.cuda.set_device(0)
        auto_mask = import_auto_mask(self._root())
        ckpt = os.path.expanduser(self.ckpt_path) if self.ckpt_path else None
        self._auto_mask = auto_mask.AutoMask(
            ckpt_path=ckpt,
            point_num=self.point_num,
            prompt_num=self.prompt_num,
            threshold=0.95,
            post_process=False,
        )

    def segment(self, points: np.ndarray) -> PartSegmentation:
        """Label ``points`` by part. Coordinates stay in the input frame."""
        if self._auto_mask is None:
            self.load()
        auto_mask = self._module()
        auto_mask.set_seed(self.seed)
        selected = prepare_points(points, self.point_num, self.seed)
        if selected.shape[0] < 32:
            raise ValueError(f"need at least 32 finite points, got {selected.shape[0]}")
        prompt_num = min(self.prompt_num, int(selected.shape[0]))
        if prompt_num < 1:
            raise ValueError("prompt_num must be positive")
        self._stage("estimating normals")
        normals = estimate_normals(selected)
        normalized = auto_mask.normalize_pc(selected.copy())
        self._stage("extracting features")
        labels = _label_points(
            auto_mask,
            self._auto_mask.model,
            normalized,
            normals,
            prompt_num,
            self.prompt_bs,
            self._stage,
        )
        return _pack_result(selected, labels)

    def _root(self):
        from pathlib import Path

        if not self.upstream_root:
            return None
        return Path(self.upstream_root)

    def _module(self):
        return import_auto_mask(self._root())

    def _stage(self, text: str) -> None:
        if self.stage_log is not None:
            self.stage_log(text)


def _label_points(auto_mask, model, points, normals, prompt_num, prompt_bs, stage) -> np.ndarray:
    """Run prompt masks on normalized points and return one label per point."""
    import fpsample

    feats = auto_mask.get_feat(model, points, normals)
    stage("prompting")
    prompt_idx = fpsample.fps_sampling(points, prompt_num)
    prompts = points[prompt_idx]
    mask_columns = []
    iou_scores = []
    batch_count = prompt_num // prompt_bs + 1
    for batch in range(batch_count):
        prompt = prompts[prompt_bs * batch:prompt_bs * (batch + 1)]
        if len(prompt) == 0:
            continue
        mask_1, mask_2, mask_3, pred_iou = auto_mask.get_mask(model, feats, points, prompt)
        stacked = np.stack([mask_1, mask_2, mask_3], axis=-1)
        chosen = np.argmax(pred_iou, axis=-1)
        for index, choice in enumerate(chosen):
            mask_columns.append(stacked[:, index, choice])
            iou_scores.append(float(pred_iou[index, choice]))
    masks = np.stack(mask_columns, axis=-1)
    stage("clustering parts")
    order = np.argsort(-np.asarray(iou_scores))
    mask_sorted = [masks[:, int(index)] for index in order]
    return _cluster_masks(auto_mask, points, mask_sorted)


def _cluster_masks(auto_mask, points, mask_sorted) -> np.ndarray:
    """Merge prompt masks that cover the same points."""
    clusters: dict[int, list[int]] = {}
    for index, mask in enumerate(mask_sorted):
        if not np.any(mask):
            continue
        for key in list(clusters):
            if auto_mask.cal_iou(mask, mask_sorted[key]) > 0.9:
                clusters[key].append(index)
                break
        else:
            clusters[index] = [index]

    kept = [key for key, members in clusters.items() if len(members) > 2]
    merged: dict[int, list[int]] = {}
    used: set[int] = set()
    for index, current in enumerate(kept):
        if index in used:
            continue
        merged[current] = [current]
        for other in range(index + 1, len(kept)):
            if other in used:
                continue
            target = kept[other]
            if not np.any(mask_sorted[target]) or not np.any(mask_sorted[current]):
                continue
            overlap = auto_mask.cal_bbox_iou(points, mask_sorted[target], mask_sorted[current])
            if overlap > 0.5:
                merged[current].append(target)
                used.add(other)

    uncovered = np.ones(points.shape[0], dtype=bool)
    for key in merged:
        uncovered[mask_sorted[key]] = False
    for index, mask in enumerate(mask_sorted):
        if index in merged or not np.any(mask):
            continue
        if auto_mask.cal_single_iou(mask, uncovered) > 0.7:
            merged[index] = [index]
            uncovered[mask] = False

    labels = -np.ones(points.shape[0], dtype=np.int64)
    ranked = sorted(merged, key=lambda key: int(np.count_nonzero(mask_sorted[key])), reverse=True)
    for part_id, key in enumerate(ranked):
        labels[mask_sorted[key]] = part_id
    return labels


def _pack_result(points: np.ndarray, labels: np.ndarray) -> PartSegmentation:
    part_ids = [int(part_id) for part_id in np.unique(labels) if int(part_id) >= 0]
    boxes = []
    for part_id in part_ids:
        selected = points[labels == part_id]
        boxes.append(
            PartBox(
                part_id=part_id,
                min_xyz=selected.min(axis=0).astype(float).tolist(),
                max_xyz=selected.max(axis=0).astype(float).tolist(),
            )
        )
    return PartSegmentation(
        points=points.astype(np.float32),
        labels=labels.astype(np.int64),
        part_ids=part_ids,
        boxes=boxes,
        unlabeled_points=int(np.count_nonzero(labels < 0)),
    )
