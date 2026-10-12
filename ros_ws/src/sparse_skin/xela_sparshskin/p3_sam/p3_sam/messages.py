"""Convert a part segmentation into ROS messages."""

from __future__ import annotations

import json
import struct

import numpy as np
from sensor_msgs.msg import PointCloud2, PointField
from sensor_msgs_py import point_cloud2
from std_msgs.msg import Header, String

from p3_sam.segmenter import PartSegmentation


def parts_json(result: PartSegmentation, latency_ms: float) -> str:
    """Serialize part ids and boxes."""
    payload = {
        "point_count": result.point_count,
        "part_count": result.part_count,
        "part_ids": result.part_ids,
        "unlabeled_points": result.unlabeled_points,
        "latency_ms": latency_ms,
        "boxes": [
            {"id": box.part_id, "min": box.min_xyz, "max": box.max_xyz}
            for box in result.boxes
        ],
    }
    return json.dumps(payload)


def parts_string(result: PartSegmentation, latency_ms: float) -> String:
    """Wrap :func:`parts_json` in a ``std_msgs/String``."""
    return String(data=parts_json(result, latency_ms))


def parts_cloud(result: PartSegmentation, header: Header) -> PointCloud2:
    """Publish the segmented points, colored by part."""
    fields = [
        PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
        PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
        PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
        PointField(name="rgb", offset=12, datatype=PointField.FLOAT32, count=1),
    ]
    packed = np.zeros(result.point_count, dtype=np.float32)
    for part_id in np.unique(result.labels):
        red, green, blue = _part_color(int(part_id))
        packed[result.labels == part_id] = _pack_rgb(red, green, blue)
    cloud = np.concatenate([result.points.astype(np.float32), packed[:, None]], axis=1)
    return point_cloud2.create_cloud(header, fields, cloud.tolist())


def cloud_points(msg: PointCloud2) -> np.ndarray:
    """Read xyz from a ``PointCloud2``, dropping non-finite points."""
    rows = point_cloud2.read_points(msg, field_names=("x", "y", "z"), skip_nans=True)
    if len(rows) == 0:
        return np.zeros((0, 3), dtype=np.float64)
    return np.stack([rows["x"], rows["y"], rows["z"]], axis=1).astype(np.float64)


def _pack_rgb(red: int, green: int, blue: int) -> float:
    return struct.unpack("f", struct.pack("I", (red << 16) | (green << 8) | blue))[0]


def _part_color(part_id: int) -> tuple[int, int, int]:
    if part_id < 0:
        return (40, 40, 40)
    color = np.random.default_rng(part_id + 1).integers(40, 255, size=3)
    return int(color[0]), int(color[1]), int(color[2])
