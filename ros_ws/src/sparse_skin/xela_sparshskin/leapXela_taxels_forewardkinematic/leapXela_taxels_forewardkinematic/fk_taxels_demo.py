#!/usr/bin/env python3
"""Live ROS port of scripts/xela/fk_taxels_demo.py.

Same FK + Open3D force/position visualization, but joint angles and taxel
forces come from ROS topics instead of a sparsh-skin pickle dataset.

Topics (defaults match process_hand_sensors_into_pointcloud / hand_controller):
  - sensor_msgs/JointState on ``xela_joint_publisher``
  - xela_sparshskin_sim/HandSensors on ``hand_sensors``
"""

from __future__ import annotations

import json
from pathlib import Path
import pickle
import threading

import einops
import numpy as np
import pytorch_kinematics as pk
import torch
from scipy.interpolate import CubicSpline

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from xela_sparshskin_sim.msg import HandSensors

# Patch link frames in hand_ss.urdf (same taxel counts as Allegro XELA flatten order).
# Proximal "B" pads use unprefixed names in the Leap URDF.
XELA_FLATTEN_ORDER = {
    "3aftc_palm_link": 30,
    "link_15_4x4_palm_link": 16,
    "link_14_4x4_palm_link": 16,
    "0aftc_palm_link": 30,
    "link_2_4x4_palm_link": 16,
    "link_1A_4x4_palm_link": 16,
    "1B_4x4_palm_link": 16,
    "1aftc_palm_link": 30,
    "link_6_4x4_palm_link": 16,
    "link_5A_4x4_palm_link": 16,
    "5B_4x4_palm_link": 16,
    "2aftc_palm_link": 30,
    "link_10_4x4_palm_link": 16,
    "link_9A_4x4_palm_link": 16,
    "9B_4x4_palm_link": 16,
    "ahr_palm_2_4x6_palm_link": 24,
    "ahr_palm_1_4x6_palm_link": 24,
    "ahr_palm_3_4x6_palm_link": 24,
}

_PATCH_TO_TAXEL_MAP = {
    "3aftc_palm_link": ("TH", "tip", True, 0, False),
    "link_15_4x4_palm_link": ("TH", "ds", False, 4, False),
    "link_14_4x4_palm_link": ("TH", "third", False, 4, False),
    "0aftc_palm_link": ("IF", "tip", True, 0, False),
    "link_2_4x4_palm_link": ("IF", "ds", False, 4, False),
    "link_1A_4x4_palm_link": ("IF", "md", False, 4, False),
    "1B_4x4_palm_link": ("IF", "bs", False, 4, False),
    "1aftc_palm_link": ("MF", "tip", True, 0, False),
    "link_6_4x4_palm_link": ("MF", "ds", False, 4, False),
    "link_5A_4x4_palm_link": ("MF", "md", False, 4, False),
    "5B_4x4_palm_link": ("MF", "px", False, 4, False),
    "2aftc_palm_link": ("RF", "tip", True, 0, False),
    "link_10_4x4_palm_link": ("RF", "ds", False, 4, False),
    "link_9A_4x4_palm_link": ("RF", "md", False, 4, False),
    "9B_4x4_palm_link": ("RF", "bs", False, 4, False),
    "ahr_palm_2_4x6_palm_link": ("Palm", "uspa46_1", False, 4, True),
    "ahr_palm_1_4x6_palm_link": ("Palm", "uspa46_2", False, 4, True),
    "ahr_palm_3_4x6_palm_link": ("Palm", "uspa46_3", False, 4, True),
}


def get_sensor_grid(patch_name):
    if "aftc" in patch_name:
        h, w, d = 0.031, 0.039, 0.029  # numbers taken from mesh boundingbox
        h_res, w_res = 6, 6
        x = np.linspace(0.5 - h_res / 2, h_res / 2 + 0.5, h_res, endpoint=False) * h / h_res
        y = np.linspace(0.5, w_res + 0.5, w_res, endpoint=False) * w / w_res
        xx_, yy_ = np.meshgrid(x, y)
        xx = np.concatenate([xx_[:4, :].flatten(), xx_[-2, 1:-1], xx_[-1, 2:-2]], axis=0)
        yy = np.concatenate([yy_[:4, :].flatten(), yy_[-2, 1:-1], yy_[-1, 2:-2]], axis=0)
    elif "4x4" in patch_name:
        h, w, d = 0.026, 0.024, 0.0044  # numbers taken from mesh boundingbox
        h_res, w_res = 4, 4
        x = np.linspace(0.5, h_res + 0.5, h_res, endpoint=False) * h / h_res
        y = np.linspace(0.5, w_res + 0.5, w_res, endpoint=False) * w / w_res
        xx, yy = np.meshgrid(x, y)
    elif "4x6" in patch_name:
        # Local to ahr_palm_*_4x6_palm_link (pad-edge / link origin).
        # First taxel at (offset_x, offset_y); then 6 cols x 4 rows by spacing.
        # Values match xela 4x6 taxel sites (mjmodel / 4x6.urdf).
        offset_x = 0.00435
        offset_y = 0.00425
        x_dist = 0.00725
        y_dist = 0.00717
        d = 0.0
        n_cols, n_rows = 6, 4
        x = offset_x + np.arange(n_cols) * x_dist
        y = offset_y + np.arange(n_rows) * y_dist
        xx, yy = np.meshgrid(x, y)
    return xx, yy, d


# Leap + Xela skin URDF (hand_ss.urdf from xela_description)
def _default_urdf_path() -> Path:
    candidates = []
    try:
        from ament_index_python.packages import get_package_share_directory

        candidates.append(
            Path(get_package_share_directory("xela_description")) / "urdf" / "hand_ss.urdf"
        )
    except Exception:
        pass
    candidates.extend(
        [
            Path("/workspace/LeapXELA_Hardware_ws/ros_ws/src/xela_description/urdf/hand_ss.urdf"),
            Path("/workspace/LeapXELA_Hardware_ws/ros_ws/install/xela_description/share/xela_description/urdf/hand_ss.urdf"),
        ]
    )
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


DEFAULT_URDF_PATH = _default_urdf_path()
DEFAULT_BASELINE_PATH = Path(
    "/workspace/LeapXELA_Hardware_ws/ros_ws/src/sparse_skin/sparsh-multisensory-touch"
    "/data/sparsh-skin-dataset/pretraining/baseline/xela/data.pkl"
)


def _default_taxel_map_path() -> Path:
    candidates = []
    try:
        from ament_index_python.packages import get_package_share_directory

        candidates.append(
            Path(get_package_share_directory("xela_sparshskin_sim")) / "leap_sensor_taxel_map.json"
        )
    except Exception:
        pass
    candidates.extend(
        [
            Path(
                "/workspace/LeapXELA_Hardware_ws/ros_ws/src/sparse_skin/xela_sparshskin"
                "/xela_sparshskin_sim/src/leap_sensor_taxel_map.json"
            ),
            Path(
                "/workspace/LeapXELA_Hardware_ws/ros_ws/install/xela_sparshskin_sim/share"
                "/xela_sparshskin_sim/leap_sensor_taxel_map.json"
            ),
        ]
    )
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


def _tip_ids_in_fk_grid_order(ids: list[int]) -> list[int]:
    """Reorder hardware tip ids (4-5-6-6-5-4) into ``get_sensor_grid`` aftc order.

    FK tip positions are a 6x6 with distal taper ``(6,6,6,6,4,2)``. Hardware
    ids in ``leap_sensor_taxel_map.json`` / ``LEAP_XELA_ID`` are a centered
    capsule ``(4,5,6,6,5,4)``. Map between them with a 90° CW + vertical flip
    so e.g. FK indices ``23,17,11,5`` ↔ taxels ``0,1,2,3`` and
    ``18,12,6,0`` ↔ ``58,59,60,61`` on the thumb tip.
    """
    if len(ids) != 30:
        raise ValueError(f"tip expected 30 ids, got {len(ids)}")
    grid = np.full((6, 6), -1, dtype=np.int32)
    grid[0, 2:6] = ids[0:4]
    grid[1, 1:6] = ids[4:9]
    grid[2, 0:6] = ids[9:15]
    grid[3, 0:6] = ids[15:21]
    grid[4, 1:6] = ids[21:26]
    grid[5, 2:6] = ids[26:30]
    # out[r, c] = grid[5 - c, 5 - r]
    out = np.full((6, 6), -1, dtype=np.int32)
    for r in range(6):
        for c in range(6):
            out[r, c] = grid[5 - c, 5 - r]
    return (
        out[:4, :].reshape(-1).tolist()
        + out[4, 1:5].tolist()
        + out[5, 2:4].tolist()
    )


def _palm_ids_in_fk_grid_order(ids: list[int], patch: str) -> list[int]:
    """Reorder hardware palm ids (6x4) into ``get_sensor_grid`` 4x6 order.

    JSON / ``LEAP_XELA_ID`` store each ``uspa46_*`` pad as 6 rows of 4. FK
    flattens ``meshgrid`` as 4 rows of 6. Left pads (``uspa46_2``, ``uspa46_3``)
    use 90° CW + vertical flip; the right pad (``uspa46_1``) is a plain
    transpose so FK ``296,302,308,314`` ↔ taxels ``119,120,121,122``.
    """
    if len(ids) != 24:
        raise ValueError(f"palm expected 24 ids, got {len(ids)}")
    hw = np.asarray(ids, dtype=np.int32).reshape(6, 4)
    if patch == "uspa46_1":
        out = hw.T
    else:
        # out[r, c] = hw[5 - c, 3 - r]  (uspa46_2 / uspa46_3)
        out = np.flipud(np.rot90(hw, -1))
    return out.reshape(-1).tolist()


def _flatten_patch_taxel_ids(
    map_dict: dict,
    finger: str,
    patch: str,
    is_tip: bool,
    is_palm: bool = False,
) -> list[int]:
    """Taxel ids for one patch in FK flatten order (matches ``get_sensor_grid``)."""
    patch_dict = map_dict[finger][patch]
    row_keys = sorted(patch_dict.keys(), key=lambda k: int(k))
    ids: list[int] = []
    for key in row_keys:
        ids.extend(int(v) for v in patch_dict[key])
    if is_tip:
        if len(ids) != 30:
            raise ValueError(f"{finger}/{patch} tip expected 30 ids, got {len(ids)}")
        return _tip_ids_in_fk_grid_order(ids)
    if is_palm:
        if len(ids) != 24:
            raise ValueError(f"{finger}/{patch} palm expected 24 ids, got {len(ids)}")
        return _palm_ids_in_fk_grid_order(ids, patch)
    return ids


def _build_taxel_ids_in_fk_order() -> np.ndarray:
    """Hardware taxel ids in ``XELA_FLATTEN_ORDER`` (same order as FK positions).

    Uses ``leap_sensor_taxel_map.json`` via ``_PATCH_TO_TAXEL_MAP`` so 3D labels
    match the white-background reference grid (taxel_pertubation / LEAP_XELA_ID).
    """
    map_path = _default_taxel_map_path()
    if not map_path.is_file():
        raise FileNotFoundError(f"Could not locate leap_sensor_taxel_map.json at {map_path}")

    with map_path.open(encoding="utf-8") as f:
        map_dict = json.load(f)

    taxel_ids: list[int] = []
    for link_name, num_sensors in XELA_FLATTEN_ORDER.items():
        finger, patch, is_tip, _width, is_palm = _PATCH_TO_TAXEL_MAP[link_name]
        ids = _flatten_patch_taxel_ids(map_dict, finger, patch, is_tip, is_palm=is_palm)
        if len(ids) != num_sensors:
            raise ValueError(
                f"{link_name} ({finger}/{patch}): expected {num_sensors} ids, got {len(ids)}"
            )
        taxel_ids.extend(ids)

    out = np.asarray(taxel_ids, dtype=np.int32)
    if out.shape[0] != 368:
        raise ValueError(f"Expected 368 taxel ids, got {out.shape[0]}")
    if not np.array_equal(np.sort(out), np.arange(368)):
        raise ValueError("Taxel ids from map do not cover 0..367 exactly once")
    return out


TAXEL_IDS_IN_FK_ORDER = _build_taxel_ids_in_fk_order()
FK_INDICES = np.arange(TAXEL_IDS_IN_FK_ORDER.shape[0], dtype=np.int32)


# Leap hand hinge joints in MuJoCo / hand_controller / hand_ss.urdf order (16 DoF).
LEAP_JOINT_ORDER = [
    "if_mcp",
    "if_rot",
    "if_pip",
    "if_dip",
    "mf_mcp",
    "mf_rot",
    "mf_pip",
    "mf_dip",
    "rf_mcp",
    "rf_rot",
    "rf_pip",
    "rf_dip",
    "th_cmc",
    "th_axl",
    "th_mcp",
    "th_ipl",
]

# MuJoCo scene places the palm with pos="0 0 0.1" quat="0.707107 -0.707107 0 0"
# (Rx -90°). URDF FK is in the unrotated hand base; apply this to match MuJoCo world
# (Z-up, fingers along +Y) so Open3D aligns with process_hand_sensors_into_pointcloud.
_MUJOCO_PALM_R = np.array(
    [
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.0, -1.0, 0.0],
    ],
    dtype=np.float64,
)
_MUJOCO_PALM_T = np.array([0.0, 0.0, 0.1], dtype=np.float64)


def urdf_base_to_mujoco_world(positions, rotations=None):
    """Map URDF-base FK poses into the MuJoCo world frame used by the sim.

    ``p_w = R_palm @ p_urdf + t_palm``, ``R_w = R_palm @ R_urdf``.
    """
    positions = np.asarray(positions, dtype=np.float64)
    squeeze = positions.ndim == 2
    if squeeze:
        positions = positions[None, ...]
    # (T, S, 3): p' = p @ R^T  <=>  R @ p
    pos_w = np.einsum("ij,tsj->tsi", _MUJOCO_PALM_R, positions) + _MUJOCO_PALM_T
    if rotations is None:
        return pos_w[0] if squeeze else pos_w
    rotations = np.asarray(rotations, dtype=np.float64)
    if rotations.ndim == 3:
        rotations = rotations[None, ...]
    rot_w = np.einsum("ij,tsjk->tsik", _MUJOCO_PALM_R, rotations)
    if squeeze:
        return pos_w[0], rot_w[0]
    return pos_w, rot_w


_kinematic_chain = None
_cached_urdf_path = None


def _taxel_patch_colors(num_taxels: int = 368) -> np.ndarray:
    """Distinct RGB color per tactile patch (same order as XELA_FLATTEN_ORDER)."""
    colors = np.zeros((num_taxels, 3), dtype=np.float64)
    n_patches = len(XELA_FLATTEN_ORDER)
    idx = 0
    for i, num_sensors in enumerate(XELA_FLATTEN_ORDER.values()):
        # Evenly spaced hues so neighboring patches are easy to tell apart
        hue = i / n_patches
        h6 = hue * 6.0
        c = 0.95 * 0.75
        x = c * (1.0 - abs(h6 % 2.0 - 1.0))
        m = 0.95 - c
        if h6 < 1:
            rgb = (c, x, 0.0)
        elif h6 < 2:
            rgb = (x, c, 0.0)
        elif h6 < 3:
            rgb = (0.0, c, x)
        elif h6 < 4:
            rgb = (0.0, x, c)
        elif h6 < 5:
            rgb = (x, 0.0, c)
        else:
            rgb = (c, 0.0, x)
        colors[idx : idx + num_sensors] = np.array(rgb) + m
        idx += num_sensors
    return colors


def _force_magnitude_colors(forces_xyz: np.ndarray, vmax: float | None = None) -> np.ndarray:
    """Map |f| to a blue→yellow→red colormap for contact visualization."""
    mag = np.linalg.norm(forces_xyz, axis=-1)
    if vmax is None:
        vmax = float(np.percentile(mag, 98)) if mag.size else 1.0
    vmax = max(vmax, 1e-6)
    t = np.clip(mag / vmax, 0.0, 1.0)
    # dark blue → cyan → yellow → red
    colors = np.zeros((mag.shape[0], 3), dtype=np.float64)
    colors[:, 0] = np.clip(1.5 * t - 0.25, 0.0, 1.0)
    colors[:, 1] = np.clip(1.0 - 2.0 * np.abs(t - 0.5), 0.0, 1.0)
    colors[:, 2] = np.clip(1.0 - 1.5 * t, 0.0, 1.0)
    return colors


def expand_forces_to_368(forces_248: np.ndarray) -> np.ndarray:
    """Map forces.pkl taxels (248, no aftc) onto the full 368-taxel flatten order.

    ``forces.pkl`` stores only flat 4x4 / 4x6 patches. Curved fingertip (aftc)
    slots are filled with zeros.
    """
    forces_248 = np.asarray(forces_248, dtype=np.float64)
    if forces_248.ndim == 2:
        forces_248 = forces_248[None, ...]
    assert forces_248.shape[-2] == 248 and forces_248.shape[-1] == 3, (
        f"Expected forces of shape (T, 248, 3), got {forces_248.shape}"
    )
    t = forces_248.shape[0]
    out = np.zeros((t, 368, 3), dtype=np.float64)
    src = 0
    dst = 0
    for name, n in XELA_FLATTEN_ORDER.items():
        if "aftc" in name:
            dst += n
            continue
        out[:, dst : dst + n] = forces_248[:, src : src + n]
        src += n
        dst += n
    assert src == 248 and dst == 368
    return out


def deform_taxel_positions(
    positions: np.ndarray,
    rotations: np.ndarray,
    forces_local: np.ndarray,
    scale: float = 0.02,
    max_disp: float = 0.015,
) -> np.ndarray:
    """Offset FK taxel positions by contact forces expressed in each sensor frame.

    Bone motion is already in ``positions`` / ``rotations``. Contact deformation
    is modeled as a small displacement ``R @ f`` in the hand base frame
    (shear + normal), scaled for visualization and clipped.

    Parameters
    ----------
    positions : (368, 3) or (T, 368, 3)
    rotations : (368, 3, 3) or (T, 368, 3, 3)
        Sensor-frame axes in the hand base frame (from FK).
    forces_local : (368, 3) or (T, 368, 3)
        Taxel forces in the sensor local frame (Fx, Fy, Fz).
    scale : float
        Meters of displacement per unit force. Use a negative value to flip
        the deformation direction (e.g. indent along -normal).
    max_disp : float
        Per-taxel displacement magnitude cap (meters).
    """
    positions = np.asarray(positions, dtype=np.float64)
    rotations = np.asarray(rotations, dtype=np.float64)
    forces_local = np.asarray(forces_local, dtype=np.float64)
    squeeze = False
    if positions.ndim == 2:
        positions = positions[None, ...]
        rotations = rotations[None, ...]
        forces_local = forces_local[None, ...]
        squeeze = True

    # world_disp[t, s] = R[t, s] @ f[t, s]
    world_disp = np.einsum("tsij,tsj->tsi", rotations, forces_local) * scale
    norms = np.linalg.norm(world_disp, axis=-1, keepdims=True)
    world_disp = np.where(
        norms > max_disp,
        world_disp * (max_disp / (norms + 1e-12)),
        world_disp,
    )
    deformed = positions + world_disp
    return deformed[0] if squeeze else deformed


def _rotation_aligning_z_to(direction: np.ndarray) -> np.ndarray:
    """Return R such that R @ [0,0,1] aligns with ``direction``."""
    v = np.asarray(direction, dtype=np.float64)
    n = np.linalg.norm(v)
    if n < 1e-12:
        return np.eye(3)
    v = v / n
    z = np.array([0.0, 0.0, 1.0])
    dot = float(np.clip(np.dot(z, v), -1.0, 1.0))
    if dot > 0.999999:
        return np.eye(3)
    if dot < -0.999999:
        return np.diag([1.0, -1.0, -1.0])
    axis = np.cross(z, v)
    axis = axis / np.linalg.norm(axis)
    angle = np.arccos(dot)
    x, y, zc = axis
    K = np.array([[0.0, -zc, y], [zc, 0.0, -x], [-y, x, 0.0]])
    return np.eye(3) + np.sin(angle) * K + (1.0 - np.cos(angle)) * (K @ K)


_SPHERE_TEMPLATE = None
# cache_key -> list of (vertices, triangles, text_scale, cache_key)
_TAXEL_ID_TEMPLATES: dict = {}


def _unit_sphere_template(resolution: int = 6):
    """Cached low-res unit sphere (radius=1) for fast taxel mesh builds."""
    global _SPHERE_TEMPLATE
    import open3d as o3d

    if _SPHERE_TEMPLATE is None or _SPHERE_TEMPLATE.get("resolution") != resolution:
        mesh = o3d.geometry.TriangleMesh.create_sphere(radius=1.0, resolution=resolution)
        _SPHERE_TEMPLATE = {
            "resolution": resolution,
            "vertices": np.asarray(mesh.vertices, dtype=np.float64),
            "triangles": np.asarray(mesh.triangles, dtype=np.int32),
        }
    return _SPHERE_TEMPLATE


def _taxel_id_templates(taxel_ids: np.ndarray, text_scale: float = 0.00022):
    """Cached per-label text meshes (vertices centered at origin)."""
    import open3d as o3d

    taxel_ids = np.asarray(taxel_ids, dtype=np.int32)
    cache_key = (tuple(taxel_ids.tolist()), float(text_scale))
    cached = _TAXEL_ID_TEMPLATES.get(cache_key)
    if cached is not None:
        return cached

    templates = []
    for tid in taxel_ids.tolist():
        mesh = o3d.t.geometry.TriangleMesh.create_text(str(tid), depth=0.0).to_legacy()
        verts = np.asarray(mesh.vertices, dtype=np.float64)
        tris = np.asarray(mesh.triangles, dtype=np.int32)
        verts = (verts - verts.mean(axis=0)) * text_scale
        templates.append((verts, tris, text_scale, cache_key))
    _TAXEL_ID_TEMPLATES[cache_key] = templates
    return templates


def _make_taxel_id_labels(
    positions: np.ndarray,
    taxel_ids: np.ndarray,
    color=(1.0, 0.92, 0.15),
    z_offset: float = 0.002,
):
    """Merged TriangleMesh of numeric text labels at each taxel position."""
    import open3d as o3d

    positions = np.asarray(positions, dtype=np.float64)
    templates = _taxel_id_templates(taxel_ids=taxel_ids)
    vert_chunks = []
    tri_chunks = []
    offset = 0
    for i, p in enumerate(positions):
        v0, t0, _, _ = templates[i]
        vert_chunks.append(v0 + (p + np.array([0.0, 0.0, z_offset])))
        tri_chunks.append(t0 + offset)
        offset += v0.shape[0]

    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(np.concatenate(vert_chunks, axis=0))
    mesh.triangles = o3d.utility.Vector3iVector(np.concatenate(tri_chunks, axis=0))
    mesh.paint_uniform_color(list(color))
    mesh.compute_vertex_normals()
    return mesh


def _make_taxel_spheres(
    positions: np.ndarray,
    colors: np.ndarray,
    radius: float = 0.002,
    resolution: int = 6,
):
    """Merged TriangleMesh of colored spheres (one per taxel)."""
    import open3d as o3d

    positions = np.asarray(positions, dtype=np.float64)
    colors = np.asarray(colors, dtype=np.float64)
    tmpl = _unit_sphere_template(resolution)
    v0 = tmpl["vertices"]  # (M, 3)
    t0 = tmpl["triangles"]  # (F, 3)
    m = v0.shape[0]
    n = positions.shape[0]

    vertices = (v0[None, :, :] * radius + positions[:, None, :]).reshape(-1, 3)
    triangles = (t0[None, :, :] + (np.arange(n, dtype=np.int32) * m)[:, None, None]).reshape(-1, 3)
    vertex_colors = np.repeat(colors, m, axis=0)

    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(vertices)
    mesh.triangles = o3d.utility.Vector3iVector(triangles)
    mesh.vertex_colors = o3d.utility.Vector3dVector(vertex_colors)
    mesh.compute_vertex_normals()
    return mesh


def _make_force_arrows(
    positions: np.ndarray,
    forces_world: np.ndarray,
    arrow_scale: float = 0.08,
    max_len: float = 0.045,
    min_mag: float = 0.01,
    cylinder_radius: float = 0.0012,
    cone_radius: float = 0.0024,
):
    """Merged TriangleMesh of thick 3D arrows for each taxel force."""
    import open3d as o3d

    positions = np.asarray(positions, dtype=np.float64)
    forces_world = np.asarray(forces_world, dtype=np.float64)
    mag = np.linalg.norm(forces_world, axis=-1)
    keep = mag >= min_mag
    mesh = o3d.geometry.TriangleMesh()
    if not np.any(keep):
        return mesh

    origins = positions[keep]
    vecs = forces_world[keep] * arrow_scale
    lengths = np.linalg.norm(vecs, axis=-1)
    scale = np.ones_like(lengths)
    too_long = lengths > max_len
    scale[too_long] = max_len / (lengths[too_long] + 1e-12)
    vecs = vecs * scale[:, None]
    lengths = np.linalg.norm(vecs, axis=-1)
    cols = _force_magnitude_colors(forces_world[keep])

    for origin, vec, length, color in zip(origins, vecs, lengths, cols):
        if length < 1e-8:
            continue
        # Open3D arrows point along +Z; split length into shaft + tip.
        cone_h = min(0.35 * length, 0.012)
        cyl_h = max(length - cone_h, length * 0.5)
        arrow = o3d.geometry.TriangleMesh.create_arrow(
            cylinder_radius=cylinder_radius,
            cone_radius=cone_radius,
            cylinder_height=cyl_h,
            cone_height=cone_h,
            resolution=12,
            cylinder_split=1,
            cone_split=1,
        )
        arrow.rotate(_rotation_aligning_z_to(vec), center=np.zeros(3))
        arrow.translate(origin)
        arrow.paint_uniform_color(color.tolist())
        mesh += arrow

    if len(mesh.vertices) > 0:
        mesh.compute_vertex_normals()
    return mesh


def visulize_with_open3d(
    joint_angles,
    forces_local=None,
    start_frame: int = 0,
    step: int = 1,
    jump: int = 10,
    sphere_radius: float = 0.001,
    deform_scale: float = 0.02,
    max_disp: float = 0.015,
    color_by_force: bool = True,
    show_force_vectors: bool = True,
    arrow_scale: float = 0.08,
    arrow_max_len: float = 0.045,
    arrow_min_mag: float = 0.01,
    arrow_cylinder_radius: float = 0.0012,
    arrow_cone_radius: float = 0.0024,
):
    """Interactive Open3D viewer: FK skin + optional contact deformation.

    Taxels are drawn as spheres. Contact forces are drawn as thick 3D arrows.

    Controls
    --------
    Right arrow / D : next timestep (+``step``)
    Left arrow  / A : previous timestep (-``step``)
    Up arrow    / W : jump forward (+``jump``)
    Down arrow  / S : jump backward (-``jump``)
    T               : toggle contact deformation on/off
    V               : toggle force vectors on/off
    Q / Esc         : quit (close window)
    """
    import open3d as o3d

    joint_angles = np.asarray(joint_angles, dtype=np.float32)
    if joint_angles.ndim != 2 or joint_angles.shape[-1] != 16:
        raise ValueError(f"Expected joint_angles of shape (T, 16), got {joint_angles.shape}")

    num_frames = joint_angles.shape[0]
    frame_idx = int(np.clip(start_frame, 0, num_frames - 1))
    patch_colors = _taxel_patch_colors()

    if forces_local is not None:
        forces_local = np.asarray(forces_local, dtype=np.float64)
        if forces_local.ndim != 3 or forces_local.shape[0] != num_frames or forces_local.shape[1:] != (368, 3):
            raise ValueError(
                f"Expected forces_local of shape ({num_frames}, 368, 3), got {forces_local.shape}"
            )
        force_vmax = float(np.percentile(np.linalg.norm(forces_local, axis=-1), 98))
    else:
        force_vmax = 1.0

    def _frame_geometry(t: int, deform: bool):
        pos, rot = get_fk_taxel_frames(joint_angles[t])
        pos, rot = pos[0], rot[0]
        forces_world = None
        if forces_local is not None:
            forces_world = np.einsum("nij,nj->ni", rot, forces_local[t])
        if deform and forces_local is not None:
            pos = deform_taxel_positions(
                pos, rot, forces_local[t], scale=deform_scale, max_disp=max_disp
            )
            if color_by_force:
                cols = _force_magnitude_colors(forces_local[t], vmax=force_vmax)
            else:
                cols = patch_colors
        else:
            cols = patch_colors
        return pos, cols, forces_world

    def _build_meshes(pos, cols, forces_world, vectors: bool):
        spheres = _make_taxel_spheres(pos, cols, radius=sphere_radius)
        if vectors and forces_world is not None:
            arrows = _make_force_arrows(
                pos,
                forces_world,
                arrow_scale=arrow_scale,
                max_len=arrow_max_len,
                min_mag=arrow_min_mag,
                cylinder_radius=arrow_cylinder_radius,
                cone_radius=arrow_cone_radius,
            )
        else:
            arrows = o3d.geometry.TriangleMesh()
        return spheres, arrows

    deform_on = forces_local is not None
    vectors_on = show_force_vectors and forces_local is not None
    pts, cols, forces_w = _frame_geometry(frame_idx, deform_on)
    spheres, arrows = _build_meshes(pts, cols, forces_w, vectors_on)

    base_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.04)
    state = {
        "t": frame_idx,
        "spheres": spheres,
        "arrows": arrows,
        "deform": deform_on,
        "vectors": vectors_on,
        "arrows_added": False,
    }

    def _refresh_geometries(vis):
        pts_t, cols_t, forces_w_t = _frame_geometry(state["t"], state["deform"])
        new_spheres, new_arrows = _build_meshes(
            pts_t, cols_t, forces_w_t, state["vectors"]
        )

        vis.remove_geometry(state["spheres"], reset_bounding_box=False)
        state["spheres"] = new_spheres
        vis.add_geometry(state["spheres"], reset_bounding_box=False)

        if state["arrows_added"]:
            vis.remove_geometry(state["arrows"], reset_bounding_box=False)
            state["arrows_added"] = False
        state["arrows"] = new_arrows
        if state["vectors"] and len(new_arrows.vertices) > 0:
            vis.add_geometry(state["arrows"], reset_bounding_box=False)
            state["arrows_added"] = True

        vis.update_renderer()
        mode = "deformed" if state["deform"] else "FK-only"
        vec = "vectors-on" if state["vectors"] else "vectors-off"
        print(f"timestep {state['t']}/{num_frames - 1}  [{mode}, {vec}]", flush=True)

    def _set_frame(vis, new_t: int) -> bool:
        new_t = int(np.clip(new_t, 0, num_frames - 1))
        if new_t == state["t"]:
            return False
        state["t"] = new_t
        _refresh_geometries(vis)
        return False

    def on_next(vis):
        return _set_frame(vis, state["t"] + step)

    def on_prev(vis):
        return _set_frame(vis, state["t"] - step)

    def on_jump_fwd(vis):
        return _set_frame(vis, state["t"] + jump)

    def on_jump_back(vis):
        return _set_frame(vis, state["t"] - jump)

    def on_toggle_deform(vis):
        if forces_local is None:
            print("No taxel forces loaded — deformation unavailable", flush=True)
            return False
        state["deform"] = not state["deform"]
        _refresh_geometries(vis)
        return False

    def on_toggle_vectors(vis):
        if forces_local is None:
            print("No taxel forces loaded — vectors unavailable", flush=True)
            return False
        state["vectors"] = not state["vectors"]
        _refresh_geometries(vis)
        return False

    def on_quit(vis):
        vis.close()
        return False

    vis = o3d.visualization.VisualizerWithKeyCallback()
    vis.create_window(
        window_name="Xela taxel FK + forces — ←/→ step, T deform, V vectors",
        width=1280,
        height=900,
    )
    vis.add_geometry(spheres)
    vis.add_geometry(base_frame)
    if vectors_on and len(arrows.vertices) > 0:
        vis.add_geometry(arrows, reset_bounding_box=False)
        state["arrows_added"] = True

    # Arrow keys (GLFW) + WASD fallbacks
    vis.register_key_callback(262, on_next)       # RIGHT
    vis.register_key_callback(263, on_prev)       # LEFT
    vis.register_key_callback(265, on_jump_fwd)   # UP
    vis.register_key_callback(264, on_jump_back)  # DOWN
    vis.register_key_callback(ord("D"), on_next)
    vis.register_key_callback(ord("A"), on_prev)
    vis.register_key_callback(ord("W"), on_jump_fwd)
    vis.register_key_callback(ord("S"), on_jump_back)
    vis.register_key_callback(ord("T"), on_toggle_deform)
    vis.register_key_callback(ord("V"), on_toggle_vectors)
    vis.register_key_callback(ord("Q"), on_quit)

    opt = vis.get_render_option()
    opt.mesh_show_back_face = True
    opt.background_color = np.array([0.08, 0.08, 0.1])

    center = pts.mean(axis=0)
    ctr = vis.get_view_control()
    ctr.set_lookat(center.tolist())
    # Match MuJoCo scene side view: hand extends in +Y, Z up.
    ctr.set_front([-0.55, -0.75, 0.35])
    ctr.set_up([0.0, 0.0, 1.0])
    ctr.set_zoom(0.55)

    print(
        f"Interactive FK+deform viewer | {num_frames} frames | "
        f"start t={state['t']} | deform={'on' if state['deform'] else 'off'} | "
        f"vectors={'on' if state['vectors'] else 'off'}\n"
        "  ←/→ or A/D : step ±1\n"
        "  ↑/↓ or W/S : jump ±10\n"
        "  T          : toggle contact deformation\n"
        "  V          : toggle force vectors\n"
        "  Q          : quit",
        flush=True,
    )
    vis.run()
    vis.destroy_window()


def _get_kinematic_chain(urdf_path=None):
    global _kinematic_chain, _cached_urdf_path
    urdf_path = Path(urdf_path) if urdf_path is not None else DEFAULT_URDF_PATH
    urdf_path = urdf_path.resolve()
    if _kinematic_chain is None or _cached_urdf_path != urdf_path:
        assert urdf_path.exists(), f"URDF not found at {urdf_path}"
        # hand_ss.urdf may have leading whitespace before the XML declaration.
        urdf_text = urdf_path.read_text().lstrip()
        _kinematic_chain = pk.build_chain_from_urdf(urdf_text)
        _cached_urdf_path = urdf_path
    return _kinematic_chain


def get_fk_taxel_frames(joint_angles, urdf_path=None, mujoco_world: bool = True):
    """FK taxel positions and orientations from Leap joint angles.

    Runs FK on ``hand_ss.urdf``, then maps each patch link frame onto its
    sensor grid. By default, results are transformed into the MuJoCo world
    frame (same palm ``pos``/``quat`` as ``leapXela_generated_flex_sensor.xml``)
    so they match ``process_hand_sensors_into_pointcloud`` / ``HandSensors``.

    Parameters
    ----------
    joint_angles : array-like, shape (16,) or (T, 16)
        Leap joint positions (radians) in ``LEAP_JOINT_ORDER``.
    urdf_path : path-like, optional
        Path to ``hand_ss.urdf``. Defaults to xela_description share.
    mujoco_world : bool
        If True (default), map URDF-base poses into MuJoCo world (Z-up).

    Returns
    -------
    sensor_positions : np.ndarray, shape (T, 368, 3)
        XYZ positions of all taxels (MuJoCo world if ``mujoco_world``).
    sensor_rotations : np.ndarray, shape (T, 368, 3, 3)
        Rotation matrices (sensor local → world/base) for each taxel.
    """
    joint_angles = np.asarray(joint_angles, dtype=np.float32)
    if joint_angles.ndim == 1:
        joint_angles = joint_angles[None, :]
    assert joint_angles.ndim == 2 and joint_angles.shape[-1] == 16, (
        f"Expected joint_angles of shape (T, 16) or (16,), got {joint_angles.shape}"
    )

    kinematic_chain = _get_kinematic_chain(urdf_path)
    # Dict keyed by Leap joint name so order matches hand_ss.urdf regardless of
    # serial-chain enumeration quirks.
    joint_angles_t = torch.tensor(joint_angles).float()
    joint_dict = {
        name: joint_angles_t[:, i] for i, name in enumerate(LEAP_JOINT_ORDER)
    }
    joint_poses = kinematic_chain.forward_kinematics(joint_dict)

    positions = []
    rotations = []
    for k, num_sensors in XELA_FLATTEN_ORDER.items():
        joint_pose = joint_poses[k].get_matrix().numpy()  # (T, 4, 4)
        xx, yy, d = get_sensor_grid(k)
        sensor_local = np.stack([xx.flatten(), yy.flatten()], axis=-1)
        sensor_local = np.concatenate(
            [sensor_local, np.zeros_like(sensor_local)], axis=-1
        )
        sensor_local[..., -2] = d
        sensor_local[..., -1] = 1  # (S, 4) homogeneous

        t = joint_pose.shape[0]
        pose_rep = einops.repeat(joint_pose, "t i j -> t s i j", s=num_sensors)
        pose_flat = einops.rearrange(pose_rep, "t s i j -> (t s) i j")
        local_flat = einops.repeat(sensor_local, "s c -> (t s) c", t=t)
        world_h = np.einsum("m i j, m j -> m i", pose_flat, local_flat)

        pose_flat[..., :, 3] = world_h
        pose_ts = einops.rearrange(pose_flat, "(t s) i j -> t s i j", s=num_sensors)
        positions.append(pose_ts[..., :3, 3])
        rotations.append(pose_ts[..., :3, :3])

    positions = np.concatenate(positions, axis=1)
    rotations = np.concatenate(rotations, axis=1)
    if mujoco_world:
        positions, rotations = urdf_base_to_mujoco_world(positions, rotations)
    return positions, rotations


def get_fk_taxels(joint_angles, urdf_path=None, mujoco_world: bool = True):
    """Forward-kinematics of all Xela taxel positions from Leap joint angles.

    Run FK on ``hand_ss.urdf``, then map each patch link frame onto its sensor
    grid. Defaults to MuJoCo world coordinates (see ``get_fk_taxel_frames``).

    Parameters
    ----------
    joint_angles : array-like, shape (16,) or (T, 16)
        Leap joint positions (radians) in ``LEAP_JOINT_ORDER``.
    urdf_path : path-like, optional
        Path to ``hand_ss.urdf``. Defaults to xela_description share.
    mujoco_world : bool
        If True (default), map into MuJoCo world (Z-up).

    Returns
    -------
    sensor_positions : np.ndarray, shape (T, 368, 3)
        XYZ positions of all taxels (same flatten order as ``XELA_FLATTEN_ORDER``).
    """
    positions, _ = get_fk_taxel_frames(
        joint_angles, urdf_path=urdf_path, mujoco_world=mujoco_world
    )
    return positions


def load_allegro_data(path):
    """Load Allegro hand joint states from a sequence dir or allegro pickle.

    Expects either:
      - a sequence folder containing ``allegro/data.pkl``
      - an ``allegro/`` folder containing ``data.pkl``
      - a path directly to ``data.pkl``

    Returns
    -------
    dict with keys:
      - timestamps: (T,)
      - joint_angles: (T, 16)
      - joint_effort: (T, 16)
      - joint_states: (T, 33) raw [t, q..., effort...]
    """
    path = Path(path)
    if path.is_file():
        pkl_path = path
    elif (path / "allegro" / "data.pkl").exists():
        pkl_path = path / "allegro" / "data.pkl"
    elif (path / "data.pkl").exists():
        pkl_path = path / "data.pkl"
    else:
        raise FileNotFoundError(
            f"Allegro data not found at {path} "
            "(expected allegro/data.pkl, data.pkl, or a pickle file)"
        )

    with open(pkl_path, "rb") as f:
        allegro_dict = pickle.load(f)

    joint_states = np.asarray(allegro_dict["joint_states"])
    return {
        "timestamps": joint_states[:, 0],
        "joint_angles": joint_states[:, 1:17],
        "joint_effort": joint_states[:, 17:],
        "joint_states": joint_states,
    }


def load_xela_data(path, baseline_path=None, subtract_force_baseline: bool = True):
    """Load Xela magfield + force taxel streams from a sequence directory.

    Expects ``xela/data.pkl`` (368 taxels) and optionally ``xela/forces.pkl``
    (248 taxels — flat patches only). Forces are expanded to 368 with zeros on
    aftc fingertip slots.

    Returns
    -------
    dict with keys:
      - timestamps: (T,)
      - magfield: (T, 368, 3) raw magnetic readings
      - magfield_delta: (T, 368, 3) baseline-subtracted (if baseline found)
      - forces: (T, 368, 3) local-frame forces (zeros on aftc if missing)
    """
    path = Path(path)
    if (path / "xela" / "data.pkl").exists():
        xela_dir = path / "xela"
    elif (path / "data.pkl").exists():
        xela_dir = path
    else:
        raise FileNotFoundError(
            f"Xela data not found at {path} (expected xela/data.pkl or data.pkl)"
        )

    with open(xela_dir / "data.pkl", "rb") as f:
        mag = np.asarray(pickle.load(f), dtype=np.float64)
    assert mag.ndim == 3 and mag.shape[1:] == (368, 4), (
        f"Expected magfield (T, 368, 4), got {mag.shape}"
    )
    timestamps = mag[:, 0, 0]
    magfield = mag[:, :, 1:4]

    magfield_delta = None
    baseline_path = Path(baseline_path) if baseline_path is not None else DEFAULT_BASELINE_PATH
    if baseline_path.exists():
        with open(baseline_path, "rb") as f:
            baseline = np.asarray(pickle.load(f), dtype=np.float64)
        baseline_mean = baseline[:, :, 1:4].mean(axis=0)
        magfield_delta = magfield - baseline_mean[None, ...]

    forces_368 = np.zeros((mag.shape[0], 368, 3), dtype=np.float64)
    forces_path = xela_dir / "forces.pkl"
    if forces_path.exists():
        with open(forces_path, "rb") as f:
            forces = np.asarray(pickle.load(f), dtype=np.float64)
        assert forces.shape[0] == mag.shape[0] and forces.shape[1:] == (248, 4), (
            f"Expected forces (T, 248, 4) aligned with magfield, got {forces.shape}"
        )
        forces_xyz = forces[:, :, 1:4]
        if subtract_force_baseline:
            # Use early no-/low-contact frames as a per-taxel bias estimate.
            n_base = min(30, forces_xyz.shape[0])
            forces_xyz = forces_xyz - forces_xyz[:n_base].mean(axis=0, keepdims=True)
        forces_368 = expand_forces_to_368(forces_xyz)

    return {
        "timestamps": timestamps,
        "magfield": magfield,
        "magfield_delta": magfield_delta,
        "forces": forces_368,
    }


def align_joints_to_timestamps(allegro_data, target_timestamps):
    """Interpolate Allegro joint angles onto Xela (or other) timestamps."""
    t_src = np.asarray(allegro_data["timestamps"], dtype=np.float64)
    q_src = np.asarray(allegro_data["joint_angles"], dtype=np.float64)
    t_dst = np.asarray(target_timestamps, dtype=np.float64)
    spline = CubicSpline(t_src, q_src, axis=0)
    # Clamp query times to the Allegro span to avoid extrapolation blow-ups.
    t_query = np.clip(t_dst, t_src[0], t_src[-1])
    return spline(t_query).astype(np.float32)


def joint_state_to_angles(msg: JointState, joint_names: list[str]) -> np.ndarray:
    """Extract a (16,) joint vector in ``joint_names`` order from JointState."""
    name_to_pos = {
        n: float(p) for n, p in zip(msg.name, msg.position) if np.isfinite(p)
    }
    q = np.zeros(16, dtype=np.float32)
    for i, name in enumerate(joint_names[:16]):
        if name in name_to_pos:
            q[i] = name_to_pos[name]
        elif i < len(msg.position):
            # Fall back to positional order when names do not match.
            q[i] = float(msg.position[i])
    return q


def hand_sensors_to_forces_world(msg: HandSensors) -> np.ndarray:
    """Pack HandSensors texels into (368, 3) forces in FK flatten order.

    ``process_hand_sensors_into_pointcloud`` publishes contact / xfrc forces in
    the world frame, keyed by hardware ``taxel_id``. Values are reordered to
    match ``XELA_FLATTEN_ORDER`` / ``TAXEL_IDS_IN_FK_ORDER`` so they align with
    FK positions and rotations.
    """
    by_id = np.zeros((368, 3), dtype=np.float64)
    for texel in msg.texels:
        tid = int(texel.taxel_id)
        if 0 <= tid < 368:
            by_id[tid, 0] = float(texel.fx)
            by_id[tid, 1] = float(texel.fy)
            by_id[tid, 2] = float(texel.fz)
    return by_id[TAXEL_IDS_IN_FK_ORDER]


def world_forces_to_local(forces_world: np.ndarray, rotations: np.ndarray) -> np.ndarray:
    """Convert world-frame taxel forces to sensor-local using FK rotations.

    ``rotations`` maps sensor-local → hand/world (from ``get_fk_taxel_frames``),
    so ``f_local = R^T @ f_world``.
    """
    forces_world = np.asarray(forces_world, dtype=np.float64)
    rotations = np.asarray(rotations, dtype=np.float64)
    return np.einsum("nji,nj->ni", rotations, forces_world)


def visulize_live_with_open3d(
    node: "FkTaxelsDemoNode",
    sphere_radius: float = 0.001,
    deform_scale: float = 0.02,
    max_disp: float = 0.015,
    color_by_force: bool = True,
    show_force_vectors: bool = True,
    arrow_scale: float = 0.08,
    arrow_max_len: float = 0.045,
    arrow_min_mag: float = 0.01,
    arrow_cylinder_radius: float = 0.0012,
    arrow_cone_radius: float = 0.0024,
):
    """Same Open3D visualization as ``visulize_with_open3d``, driven by live ROS.

    Controls: T taxel IDs, I FK indices, F deform, V vectors, Q quit.
    """
    import open3d as o3d

    patch_colors = _taxel_patch_colors()
    force_vmax = 1.0
    _LABEL_COLORS = {
        "taxel": (1.0, 0.92, 0.15),  # yellow — hardware taxel id
        "index": (0.35, 0.95, 1.0),  # cyan — FK flatten index
    }

    def _latest_frame():
        nonlocal force_vmax
        q, f_world = node.get_latest()
        if q is None:
            return None
        pos, rot = get_fk_taxel_frames(q)
        pos, rot = pos[0], rot[0]
        forces_local = None
        forces_world = None
        if f_world is not None:
            forces_local = world_forces_to_local(f_world, rot)
            forces_world = f_world
            mag = np.linalg.norm(forces_local, axis=-1)
            force_vmax = max(float(np.percentile(mag, 98)), 1e-6)
        return pos, rot, forces_local, forces_world

    def _frame_geometry(deform: bool):
        frame = _latest_frame()
        if frame is None:
            return None
        pos, rot, forces_local, forces_world = frame
        if deform and forces_local is not None:
            pos = deform_taxel_positions(
                pos, rot, forces_local, scale=deform_scale, max_disp=max_disp
            )
            cols = (
                _force_magnitude_colors(forces_local, vmax=force_vmax)
                if color_by_force
                else patch_colors
            )
        else:
            cols = patch_colors
        return pos, cols, forces_world

    def _build_meshes(pos, cols, forces_world, vectors: bool, label_mode: str | None):
        spheres = _make_taxel_spheres(pos, cols, radius=sphere_radius)
        if vectors and forces_world is not None:
            arrows = _make_force_arrows(
                pos,
                forces_world,
                arrow_scale=arrow_scale,
                max_len=arrow_max_len,
                min_mag=arrow_min_mag,
                cylinder_radius=arrow_cylinder_radius,
                cone_radius=arrow_cone_radius,
            )
        else:
            arrows = o3d.geometry.TriangleMesh()
        if label_mode == "taxel":
            labels = _make_taxel_id_labels(
                pos, TAXEL_IDS_IN_FK_ORDER, color=_LABEL_COLORS["taxel"]
            )
        elif label_mode == "index":
            labels = _make_taxel_id_labels(pos, FK_INDICES, color=_LABEL_COLORS["index"])
        else:
            labels = o3d.geometry.TriangleMesh()
        return spheres, arrows, labels

    # Wait until the first joint sample arrives.
    node.get_logger().info("Waiting for joint + sensor topics…")
    while rclpy.ok() and node.get_latest()[0] is None:
        rclpy.spin_once(node, timeout_sec=0.1)

    geom = _frame_geometry(deform=True)
    if geom is None:
        raise RuntimeError("No joint data received")
    pts, cols, forces_w = geom
    deform_on = forces_w is not None
    vectors_on = show_force_vectors and forces_w is not None
    label_mode = None  # None | "taxel" | "index"
    spheres, arrows, labels = _build_meshes(pts, cols, forces_w, vectors_on, label_mode)

    base_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.04)
    state = {
        "spheres": spheres,
        "arrows": arrows,
        "labels": labels,
        "deform": deform_on,
        "vectors": vectors_on,
        "label_mode": label_mode,
        "arrows_added": False,
        "labels_added": False,
        "follow_live": True,
    }

    def _refresh_geometries(vis):
        frame = _frame_geometry(state["deform"])
        if frame is None:
            return
        pts_t, cols_t, forces_w_t = frame
        new_spheres, new_arrows, new_labels = _build_meshes(
            pts_t, cols_t, forces_w_t, state["vectors"], state["label_mode"]
        )

        vis.remove_geometry(state["spheres"], reset_bounding_box=False)
        state["spheres"] = new_spheres
        vis.add_geometry(state["spheres"], reset_bounding_box=False)

        if state["arrows_added"]:
            vis.remove_geometry(state["arrows"], reset_bounding_box=False)
            state["arrows_added"] = False
        state["arrows"] = new_arrows
        if state["vectors"] and len(new_arrows.vertices) > 0:
            vis.add_geometry(state["arrows"], reset_bounding_box=False)
            state["arrows_added"] = True

        if state["labels_added"]:
            vis.remove_geometry(state["labels"], reset_bounding_box=False)
            state["labels_added"] = False
        state["labels"] = new_labels
        if state["label_mode"] is not None and len(new_labels.vertices) > 0:
            vis.add_geometry(state["labels"], reset_bounding_box=False)
            state["labels_added"] = True
        vis.update_renderer()

    def _set_label_mode(vis, mode: str):
        """Toggle ``mode`` on/off; switching modes replaces the other."""
        if state["label_mode"] == mode:
            state["label_mode"] = None
        else:
            state["label_mode"] = mode
            ids = TAXEL_IDS_IN_FK_ORDER if mode == "taxel" else FK_INDICES
            print(f"Building {mode} labels (first time may take a moment)…", flush=True)
            _taxel_id_templates(ids)
        print(f"labels={state['label_mode'] or 'off'}", flush=True)
        _refresh_geometries(vis)
        return False

    def on_toggle_taxel_ids(vis):
        return _set_label_mode(vis, "taxel")

    def on_toggle_fk_indices(vis):
        return _set_label_mode(vis, "index")

    def on_toggle_deform(vis):
        state["deform"] = not state["deform"]
        print(f"deform={'on' if state['deform'] else 'off'}", flush=True)
        _refresh_geometries(vis)
        return False

    def on_toggle_vectors(vis):
        state["vectors"] = not state["vectors"]
        _refresh_geometries(vis)
        return False

    def on_quit(vis):
        vis.close()
        return False

    def on_tick(vis):
        if not rclpy.ok():
            vis.close()
            return False
        rclpy.spin_once(node, timeout_sec=0.0)
        if state["follow_live"] and node.consume_update_flag():
            _refresh_geometries(vis)
        return False

    vis = o3d.visualization.VisualizerWithKeyCallback()
    vis.create_window(
        window_name="Xela taxel FK + forces (live ROS) — T ids, I index, F deform, V vectors",
        width=1280,
        height=900,
    )
    vis.add_geometry(spheres)
    vis.add_geometry(base_frame)
    if vectors_on and len(arrows.vertices) > 0:
        vis.add_geometry(arrows, reset_bounding_box=False)
        state["arrows_added"] = True

    vis.register_key_callback(ord("T"), on_toggle_taxel_ids)
    vis.register_key_callback(ord("I"), on_toggle_fk_indices)
    vis.register_key_callback(ord("F"), on_toggle_deform)
    vis.register_key_callback(ord("V"), on_toggle_vectors)
    vis.register_key_callback(ord("Q"), on_quit)
    vis.register_animation_callback(on_tick)

    opt = vis.get_render_option()
    opt.mesh_show_back_face = True
    opt.background_color = np.array([0.08, 0.08, 0.1])

    center = pts.mean(axis=0)
    ctr = vis.get_view_control()
    ctr.set_lookat(center.tolist())
    # Match MuJoCo scene side view: hand extends in +Y, Z up.
    ctr.set_front([-0.55, -0.75, 0.35])
    ctr.set_up([0.0, 0.0, 1.0])
    ctr.set_zoom(0.55)

    print(
        "Live FK+deform viewer (ROS)\n"
        "  T : toggle hardware taxel id labels (yellow)\n"
        "  I : toggle FK flatten index labels (cyan)\n"
        "  F : toggle contact deformation\n"
        "  V : toggle force vectors\n"
        "  Q : quit",
        flush=True,
    )
    vis.run()
    vis.destroy_window()


class FkTaxelsDemoNode(Node):
    """Subscribe to joint + HandSensors topics and drive the FK visualizer."""

    def __init__(self) -> None:
        super().__init__("fk_taxels_demo")

        joint_topic = self.declare_parameter("joint_topic", "xela_joint_publisher").value
        sensors_topic = self.declare_parameter("hand_sensors_topic", "hand_sensors").value
        urdf_path = self.declare_parameter("urdf_path", str(DEFAULT_URDF_PATH)).value
        joint_names = self.declare_parameter("joint_names", LEAP_JOINT_ORDER).value

        self._joint_names = list(joint_names)
        self._urdf_path = Path(urdf_path)
        self._lock = threading.Lock()
        self._joint_angles: np.ndarray | None = None
        self._forces_world: np.ndarray | None = None
        self._updated = False

        # Warm the FK chain once so the first frame is fast.
        if self._urdf_path.exists():
            _get_kinematic_chain(self._urdf_path)
        else:
            self.get_logger().warn(f"URDF not found at {self._urdf_path}")

        self.create_subscription(JointState, joint_topic, self._on_joint_state, 10)
        self.create_subscription(HandSensors, sensors_topic, self._on_hand_sensors, 10)

        self.get_logger().info(
            f"Listening for joints on '{joint_topic}' and sensors on '{sensors_topic}'"
        )

    def _on_joint_state(self, msg: JointState) -> None:
        q = joint_state_to_angles(msg, self._joint_names)
        with self._lock:
            self._joint_angles = q
            self._updated = True

    def _on_hand_sensors(self, msg: HandSensors) -> None:
        forces = hand_sensors_to_forces_world(msg)
        with self._lock:
            self._forces_world = forces
            self._updated = True

    def get_latest(self):
        with self._lock:
            q = None if self._joint_angles is None else self._joint_angles.copy()
            f = None if self._forces_world is None else self._forces_world.copy()
        return q, f

    def consume_update_flag(self) -> bool:
        with self._lock:
            updated = self._updated
            self._updated = False
        return updated


def main(args=None):
    rclpy.init(args=args)
    node = FkTaxelsDemoNode()
    try:
        visulize_live_with_open3d(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
