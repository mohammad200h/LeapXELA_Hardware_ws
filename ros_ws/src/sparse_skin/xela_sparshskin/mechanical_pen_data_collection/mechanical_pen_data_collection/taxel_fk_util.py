"""Taxel forward kinematics and Open3D taxel meshes, without ROS.

Logic taken from ``leapXela_taxels_forewardkinematic`` (``fk_taxels.py`` and
``fk_taxels_viewer.py``) so recorded bags can be visualized offline:

- ``get_fk_taxel_frames`` maps the 16 Leap joint angles onto 3D positions and
  orientations of all 368 Xela taxels (``hand_ss.urdf`` + per-patch sensor grids),
  in ``XELA_FLATTEN_ORDER``. ``TAXEL_IDS_IN_FK_ORDER`` relates hardware taxel ids
  to that order.
- ``build_taxel_meshes`` builds the same spheres / force arrows / id labels the
  live ``fk_taxels_viewer`` shows.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import einops
import numpy as np

# Only the URDF parser is needed. pytorch_kinematics skips its MJCF parser on ImportError;
# that parser imports MuJoCo, which sets PYOPENGL_PLATFORM=egl when MUJOCO_GL=egl and breaks
# the Qt (GLX) taxel views.
sys.modules.setdefault("pytorch_kinematics.mjcf", None)
import pytorch_kinematics as pk  # noqa: E402
import torch  # noqa: E402

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

NUM_TAXELS = 368

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


# ----------------------------------------------------------------------------- FK


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


def _first_existing(candidates: list[Path]) -> Path:
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


def _share_path(package: str, *parts: str) -> list[Path]:
    try:
        from ament_index_python.packages import get_package_share_directory

        return [Path(get_package_share_directory(package), *parts)]
    except Exception:
        return []


# Leap + Xela skin URDF (hand_ss.urdf from xela_description)
def _default_urdf_path() -> Path:
    return _first_existing(
        _share_path("xela_description", "urdf", "hand_ss.urdf")
        + [
            Path("/workspace/LeapXELA_Hardware_ws/ros_ws/src/xela_description/urdf/hand_ss.urdf"),
            Path(
                "/workspace/LeapXELA_Hardware_ws/ros_ws/install/xela_description/share"
                "/xela_description/urdf/hand_ss.urdf"
            ),
        ]
    )


def _default_taxel_map_path() -> Path:
    return _first_existing(
        _share_path("xela_sparshskin_sim", "leap_sensor_taxel_map.json")
        + [
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


DEFAULT_URDF_PATH = _default_urdf_path()


def _tip_ids_in_fk_grid_order(ids: list[int]) -> list[int]:
    """Reorder hardware tip ids (4-5-6-6-5-4) into ``get_sensor_grid`` aftc order.

    FK tip positions are a 6x6 with distal taper ``(6,6,6,6,4,2)``. Hardware
    ids in ``leap_sensor_taxel_map.json`` / ``LEAP_XELA_ID`` are a centered
    capsule ``(4,5,6,6,5,4)``. Map between them with a 90° CW + vertical flip
    so e.g. FK indices ``23,17,11,5`` <-> taxels ``0,1,2,3`` and
    ``18,12,6,0`` <-> ``58,59,60,61`` on the thumb tip.
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
    return out[:4, :].reshape(-1).tolist() + out[4, 1:5].tolist() + out[5, 2:4].tolist()


def _palm_ids_in_fk_grid_order(ids: list[int], patch: str) -> list[int]:
    """Reorder hardware palm ids (6x4) into ``get_sensor_grid`` 4x6 order.

    JSON / ``LEAP_XELA_ID`` store each ``uspa46_*`` pad as 6 rows of 4. FK
    flattens ``meshgrid`` as 4 rows of 6. Left pads (``uspa46_2``, ``uspa46_3``)
    use 90° CW + vertical flip; the right pad (``uspa46_1``) is a plain
    transpose so FK ``296,302,308,314`` <-> taxels ``119,120,121,122``.
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
    map_dict: dict, finger: str, patch: str, is_tip: bool, is_palm: bool = False
) -> list[int]:
    """Taxel ids for one patch in FK flatten order (matches ``get_sensor_grid``)."""
    patch_dict = map_dict[finger][patch]
    ids: list[int] = []
    for key in sorted(patch_dict.keys(), key=lambda k: int(k)):
        ids.extend(int(v) for v in patch_dict[key])
    if is_tip:
        return _tip_ids_in_fk_grid_order(ids)
    if is_palm:
        return _palm_ids_in_fk_grid_order(ids, patch)
    return ids


def _build_taxel_ids_in_fk_order() -> np.ndarray:
    """Hardware taxel ids in ``XELA_FLATTEN_ORDER`` (same order as FK positions)."""
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
    if not np.array_equal(np.sort(out), np.arange(NUM_TAXELS)):
        raise ValueError(f"Taxel ids from map do not cover 0..{NUM_TAXELS - 1} exactly once")
    return out


TAXEL_IDS_IN_FK_ORDER = _build_taxel_ids_in_fk_order()
PATCH_IDS_IN_FK_ORDER = np.repeat(
    np.arange(len(XELA_FLATTEN_ORDER), dtype=np.uint8), list(XELA_FLATTEN_ORDER.values())
)

# MuJoCo scene places the palm with pos="0 0 0.1" quat="0.707107 -0.707107 0 0"
# (Rx -90°). URDF FK is in the unrotated hand base; apply this to match MuJoCo world
# (Z-up, fingers along +Y).
_MUJOCO_PALM_R = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]], dtype=np.float64)
_MUJOCO_PALM_T = np.array([0.0, 0.0, 0.1], dtype=np.float64)


def urdf_base_to_mujoco_world(positions, rotations=None):
    """``p_w = R_palm @ p_urdf + t_palm``, ``R_w = R_palm @ R_urdf``."""
    positions = np.asarray(positions, dtype=np.float64)
    squeeze = positions.ndim == 2
    if squeeze:
        positions = positions[None, ...]
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


def get_kinematic_chain(urdf_path=None):
    global _kinematic_chain, _cached_urdf_path
    urdf_path = Path(urdf_path) if urdf_path is not None else DEFAULT_URDF_PATH
    urdf_path = urdf_path.resolve()
    if _kinematic_chain is None or _cached_urdf_path != urdf_path:
        assert urdf_path.exists(), f"URDF not found at {urdf_path}"
        # hand_ss.urdf may have leading whitespace before the XML declaration.
        _kinematic_chain = pk.build_chain_from_urdf(urdf_path.read_text().lstrip())
        _cached_urdf_path = urdf_path
    return _kinematic_chain


def get_fk_taxel_frames(joint_angles, urdf_path=None, mujoco_world: bool = True):
    """FK taxel positions and orientations from Leap joint angles.

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
    sensor_rotations : np.ndarray, shape (T, 368, 3, 3)
        Rotation matrices (sensor local -> world/base) for each taxel.
    """
    joint_angles = np.asarray(joint_angles, dtype=np.float32)
    if joint_angles.ndim == 1:
        joint_angles = joint_angles[None, :]
    assert joint_angles.ndim == 2 and joint_angles.shape[-1] == 16, (
        f"Expected joint_angles of shape (T, 16) or (16,), got {joint_angles.shape}"
    )

    kinematic_chain = get_kinematic_chain(urdf_path)
    # Dict keyed by Leap joint name so order matches hand_ss.urdf regardless of
    # serial-chain enumeration quirks.
    joint_angles_t = torch.tensor(joint_angles).float()
    joint_dict = {name: joint_angles_t[:, i] for i, name in enumerate(LEAP_JOINT_ORDER)}
    joint_poses = kinematic_chain.forward_kinematics(joint_dict)

    positions = []
    rotations = []
    for k, num_sensors in XELA_FLATTEN_ORDER.items():
        joint_pose = joint_poses[k].get_matrix().numpy()  # (T, 4, 4)
        xx, yy, d = get_sensor_grid(k)
        sensor_local = np.stack([xx.flatten(), yy.flatten()], axis=-1)
        sensor_local = np.concatenate([sensor_local, np.zeros_like(sensor_local)], axis=-1)
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


def world_forces_to_local(forces_world: np.ndarray, rotations: np.ndarray) -> np.ndarray:
    """``f_local = R^T @ f_world`` with ``R`` sensor-local -> world (from FK)."""
    return np.einsum("nji,nj->ni", np.asarray(rotations), np.asarray(forces_world))


def local_forces_to_world(forces_local: np.ndarray, rotations: np.ndarray) -> np.ndarray:
    """``f_world = R @ f_local`` with ``R`` sensor-local -> world (from FK)."""
    return np.einsum("nij,nj->ni", np.asarray(rotations), np.asarray(forces_local))


def joint_angles_in_fk_order(
    names: list[str], positions: np.ndarray, joint_names: list[str] = LEAP_JOINT_ORDER
) -> np.ndarray:
    """Reorder joint positions ``(..., J)`` named ``names`` into ``(..., 16)`` FK order.

    Same rule as ``fk_taxels.joint_state_to_angles``: match by name, otherwise fall
    back to positional order.
    """
    positions = np.asarray(positions, dtype=np.float32)
    index = {n: i for i, n in enumerate(names)}
    out = np.zeros(positions.shape[:-1] + (16,), dtype=np.float32)
    for i, name in enumerate(joint_names[:16]):
        if name in index:
            out[..., i] = positions[..., index[name]]
        elif i < positions.shape[-1]:
            out[..., i] = positions[..., i]
    return np.nan_to_num(out)


def taxel_readings_to_local_forces(
    readings_by_id: np.ndarray, baseline_by_id: np.ndarray, counts_per_unit: float
) -> np.ndarray:
    """Raw Xela (x, y, z) readings indexed by hardware id -> (368, 3) in FK order.

    The change from ``baseline`` is used as the sensor-local force, scaled down by
    ``counts_per_unit`` so it fits the deformation / arrow scales of the FK viewer.
    """
    delta = (np.asarray(readings_by_id, np.float64) - baseline_by_id) / counts_per_unit
    return delta[TAXEL_IDS_IN_FK_ORDER]


# ---------------------------------------------------------------- Open3D meshes


def taxel_patch_colors(patch_ids: np.ndarray) -> np.ndarray:
    """Distinct RGB color per tactile patch."""
    patch_ids = np.asarray(patch_ids, dtype=np.int32)
    colors = np.zeros((patch_ids.shape[0], 3), dtype=np.float64)
    n_patches = int(patch_ids.max()) + 1 if patch_ids.size else 1
    for i in range(n_patches):
        # Evenly spaced hues so neighboring patches are easy to tell apart
        h6 = i / n_patches * 6.0
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
        colors[patch_ids == i] = np.array(rgb) + m
    return colors


def force_magnitude_colors(forces_xyz: np.ndarray, vmax: float | None = None) -> np.ndarray:
    """Map |f| to a blue -> yellow -> red colormap for contact visualization."""
    mag = np.linalg.norm(forces_xyz, axis=-1)
    if vmax is None:
        vmax = float(np.percentile(mag, 98)) if mag.size else 1.0
    vmax = max(vmax, 1e-6)
    t = np.clip(mag / vmax, 0.0, 1.0)
    colors = np.zeros((mag.shape[0], 3), dtype=np.float64)
    colors[:, 0] = np.clip(1.5 * t - 0.25, 0.0, 1.0)
    colors[:, 1] = np.clip(1.0 - 2.0 * np.abs(t - 0.5), 0.0, 1.0)
    colors[:, 2] = np.clip(1.0 - 1.5 * t, 0.0, 1.0)
    return colors


def deform_taxel_positions(
    positions: np.ndarray,
    rotations: np.ndarray,
    forces_local: np.ndarray,
    scale: float = 0.02,
    max_disp: float = 0.015,
) -> np.ndarray:
    """Offset FK taxel positions by ``R @ f_local * scale``, clipped to ``max_disp``."""
    positions = np.asarray(positions, dtype=np.float64)
    rotations = np.asarray(rotations, dtype=np.float64)
    forces_local = np.asarray(forces_local, dtype=np.float64)
    squeeze = positions.ndim == 2
    if squeeze:
        positions, rotations, forces_local = positions[None], rotations[None], forces_local[None]

    world_disp = np.einsum("tsij,tsj->tsi", rotations, forces_local) * scale
    norms = np.linalg.norm(world_disp, axis=-1, keepdims=True)
    world_disp = np.where(norms > max_disp, world_disp * (max_disp / (norms + 1e-12)), world_disp)
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


def taxel_id_templates(taxel_ids: np.ndarray, text_scale: float = 0.00022):
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
        templates.append(((verts - verts.mean(axis=0)) * text_scale, tris))
    _TAXEL_ID_TEMPLATES[cache_key] = templates
    return templates


def make_taxel_id_labels(positions, taxel_ids, color=(1.0, 0.92, 0.15), z_offset: float = 0.002):
    """Merged TriangleMesh of numeric text labels at each taxel position."""
    import open3d as o3d

    templates = taxel_id_templates(taxel_ids)
    vert_chunks, tri_chunks, offset = [], [], 0
    for p, (v0, t0) in zip(np.asarray(positions, dtype=np.float64), templates):
        vert_chunks.append(v0 + (p + np.array([0.0, 0.0, z_offset])))
        tri_chunks.append(t0 + offset)
        offset += v0.shape[0]
    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(np.concatenate(vert_chunks, axis=0))
    mesh.triangles = o3d.utility.Vector3iVector(np.concatenate(tri_chunks, axis=0))
    mesh.paint_uniform_color(list(color))
    mesh.compute_vertex_normals()
    return mesh


def make_taxel_spheres(positions, colors, radius: float = 0.002, resolution: int = 6):
    """Merged TriangleMesh of colored spheres (one per taxel)."""
    import open3d as o3d

    positions = np.asarray(positions, dtype=np.float64)
    tmpl = _unit_sphere_template(resolution)
    v0, t0 = tmpl["vertices"], tmpl["triangles"]
    m, n = v0.shape[0], positions.shape[0]
    vertices = (v0[None, :, :] * radius + positions[:, None, :]).reshape(-1, 3)
    triangles = (t0[None, :, :] + (np.arange(n, dtype=np.int32) * m)[:, None, None]).reshape(-1, 3)
    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(vertices)
    mesh.triangles = o3d.utility.Vector3iVector(triangles)
    mesh.vertex_colors = o3d.utility.Vector3dVector(np.repeat(np.asarray(colors, np.float64), m, axis=0))
    mesh.compute_vertex_normals()
    return mesh


def force_vector_segments(
    positions,
    forces_world,
    arrow_scale: float = 0.08,
    max_len: float = 0.045,
    min_mag: float = 0.01,
):
    """(starts, ends, colors) of the taxel force vectors drawn by ``make_force_arrows``.

    Only taxels with ``|f| >= min_mag`` are returned; vectors are ``f * arrow_scale``
    clipped to ``max_len``, colored by ``force_magnitude_colors``.
    """
    positions = np.asarray(positions, dtype=np.float64)
    forces_world = np.asarray(forces_world, dtype=np.float64)
    keep = np.linalg.norm(forces_world, axis=-1) >= min_mag
    if not np.any(keep):
        return np.empty((0, 3)), np.empty((0, 3)), np.empty((0, 3))
    vecs = forces_world[keep] * arrow_scale
    lengths = np.linalg.norm(vecs, axis=-1)
    vecs = vecs * np.where(lengths > max_len, max_len / (lengths + 1e-12), 1.0)[:, None]
    starts = positions[keep]
    return starts, starts + vecs, force_magnitude_colors(forces_world[keep])


def make_force_arrows(
    positions,
    forces_world,
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
    keep = np.linalg.norm(forces_world, axis=-1) >= min_mag
    mesh = o3d.geometry.TriangleMesh()
    if not np.any(keep):
        return mesh

    vecs = forces_world[keep] * arrow_scale
    lengths = np.linalg.norm(vecs, axis=-1)
    scale = np.where(lengths > max_len, max_len / (lengths + 1e-12), 1.0)
    vecs = vecs * scale[:, None]
    lengths = np.linalg.norm(vecs, axis=-1)
    cols = force_magnitude_colors(forces_world[keep])

    for origin, vec, length, color in zip(positions[keep], vecs, lengths, cols):
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


LABEL_COLORS = {
    "taxel": (1.0, 0.92, 0.15),  # yellow - hardware taxel id
    "index": (0.35, 0.95, 1.0),  # cyan - FK flatten index
}


def build_taxel_meshes(
    positions: np.ndarray,
    rotations: np.ndarray,
    forces_local: np.ndarray | None,
    deform: bool = True,
    vectors: bool = True,
    label_mode: str | None = None,
    sphere_radius: float = 0.001,
    deform_scale: float = 0.02,
    max_disp: float = 0.015,
    color_by_force: bool = True,
    arrow_scale: float = 0.08,
    arrow_max_len: float = 0.045,
    arrow_min_mag: float = 0.01,
    arrow_cylinder_radius: float = 0.0012,
    arrow_cone_radius: float = 0.0024,
):
    """Spheres, force arrows and labels for one FK frame, as in ``fk_taxels_viewer``.

    ``label_mode`` is ``None``, ``"taxel"`` (hardware ids) or ``"index"`` (FK order).
    """
    import open3d as o3d

    patch_colors = taxel_patch_colors(PATCH_IDS_IN_FK_ORDER)
    pos = positions
    cols = patch_colors
    forces_world = None
    if forces_local is not None:
        forces_world = local_forces_to_world(forces_local, rotations)
        if deform:
            force_vmax = max(float(np.percentile(np.linalg.norm(forces_local, axis=-1), 98)), 1e-6)
            pos = deform_taxel_positions(
                positions, rotations, forces_local, scale=deform_scale, max_disp=max_disp
            )
            if color_by_force:
                cols = force_magnitude_colors(forces_local, vmax=force_vmax)

    spheres = make_taxel_spheres(pos, cols, radius=sphere_radius)
    if vectors and forces_world is not None:
        arrows = make_force_arrows(
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
    if label_mode is not None:
        ids = TAXEL_IDS_IN_FK_ORDER if label_mode == "taxel" else np.arange(NUM_TAXELS)
        labels = make_taxel_id_labels(pos, ids, color=LABEL_COLORS[label_mode])
    else:
        labels = o3d.geometry.TriangleMesh()
    return spheres, arrows, labels
