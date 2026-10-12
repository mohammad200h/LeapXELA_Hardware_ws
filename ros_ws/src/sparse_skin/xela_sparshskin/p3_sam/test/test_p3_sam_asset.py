#!/usr/bin/env python3
"""Check point-cloud preparation, normals, and part messages."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
from sensor_msgs.msg import PointField
from sensor_msgs_py import point_cloud2
from std_msgs.msg import Header

PKG_ROOT = Path(__file__).resolve().parents[1]
if str(PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(PKG_ROOT))

from p3_sam.messages import cloud_points, parts_cloud, parts_json  # noqa: E402
from p3_sam.segmenter import (  # noqa: E402
    PartBox,
    PartSegmentation,
    _cluster_masks,
    estimate_normals,
    prepare_points,
)
from p3_sam.upstream import _ScatterShim  # noqa: E402


def test_segment_csr_mean_and_max():
    """The Sonata shim matches a hand-reduced CSR segment."""
    src = torch.tensor([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    indptr = torch.tensor([0, 2, 3])
    mean = _ScatterShim.segment_csr(src, indptr, reduce="mean")
    maximum = _ScatterShim.segment_csr(src, indptr, reduce="max")
    assert torch.allclose(mean, torch.tensor([[2.0, 3.0], [5.0, 6.0]]))
    assert torch.allclose(maximum, torch.tensor([[3.0, 4.0], [5.0, 6.0]]))


def test_prepare_points_drops_invalid_and_caps_count():
    """Zeros and non-finite points are removed before the cap is applied."""
    points = np.zeros((100, 3), dtype=np.float64)
    points[10:50] = np.random.default_rng(0).normal(size=(40, 3)) + np.array([0.0, 0.0, 1.0])
    points[0] = np.nan
    selected = prepare_points(points, point_num=10, seed=1)
    assert selected.shape == (10, 3)
    assert np.isfinite(selected).all()
    assert np.linalg.norm(selected, axis=1).min() > 1e-4


def test_normals_on_a_frontal_plane_point_at_the_camera():
    """A plane in front of the origin gets normals aimed back at the camera."""
    axis = np.linspace(-0.1, 0.1, 25)
    grid_x, grid_y = np.meshgrid(axis, axis)
    points = np.stack(
        [grid_x.ravel(), grid_y.ravel(), np.ones(grid_x.size)],
        axis=1,
    )
    normals = estimate_normals(points)
    assert normals.shape == points.shape
    assert np.allclose(np.linalg.norm(normals, axis=1), 1.0, atol=1e-5)
    assert float(normals[:, 2].mean()) < -0.5


def test_three_agreeing_prompts_become_one_part():
    """Masks need three agreeing prompts before they count as a part."""
    points = np.array([[0.0, 0.0, 1.0], [0.1, 0.0, 1.0], [0.0, 0.1, 1.0]])
    shared = np.array([True, True, False])
    labels = _cluster_masks(_MaskMath(), points, [shared, shared, shared])
    assert labels.tolist() == [0, 0, -1]


def test_parts_json_and_cloud_follow_the_point_labels():
    """The published cloud has one colored point per segmented point."""
    result = PartSegmentation(
        points=np.array([[0.0, 0.0, 1.0], [0.2, 0.0, 1.0]], dtype=np.float32),
        labels=np.array([0, -1]),
        part_ids=[0],
        boxes=[PartBox(0, [0.0, 0.0, 1.0], [0.0, 0.0, 1.0])],
        unlabeled_points=1,
    )
    payload = json.loads(parts_json(result, 15.0))
    assert payload["point_count"] == 2
    assert payload["part_count"] == 1
    assert payload["unlabeled_points"] == 1
    assert payload["latency_ms"] == 15.0
    header = Header()
    header.frame_id = "camera_color_optical_frame"
    cloud = parts_cloud(result, header)
    assert cloud.header.frame_id == "camera_color_optical_frame"
    assert len(cloud_points(cloud)) == 2


def test_cloud_points_reads_xyz():
    """Point fields round-trip through a PointCloud2."""
    header = Header()
    header.frame_id = "camera_color_optical_frame"
    fields = [
        PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
        PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
        PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
    ]
    cloud = point_cloud2.create_cloud(header, fields, [(1.0, 2.0, 3.0)])
    assert cloud_points(cloud).tolist() == [[1.0, 2.0, 3.0]]


class _MaskMath:
    """Stand-in for the mask overlap helpers in the upstream demo."""

    @staticmethod
    def cal_iou(mask_a, mask_b):
        """Return the overlap of two boolean masks."""
        union = np.logical_or(mask_a, mask_b).sum()
        if union == 0:
            return 0.0
        return float(np.logical_and(mask_a, mask_b).sum() / union)

    @staticmethod
    def cal_bbox_iou(points, mask_a, mask_b):
        """Return no box overlap so the test only checks prompt agreement."""
        del points, mask_a, mask_b
        return 0.0

    @staticmethod
    def cal_single_iou(mask_a, mask_b):
        """Return how much of ``mask_a`` sits inside ``mask_b``."""
        total = np.sum(mask_a)
        if total == 0:
            return 0.0
        return float(np.logical_and(mask_a, mask_b).sum() / total)
