#!/usr/bin/env python3
"""Live Open3D viewer of Leap/Xela taxel positions and forces (``fk_taxels_viewer`` node).

Subscribes:
  - leapxela_sparshskin_msgs/TaxelFrames on ``taxel_frames`` (published by ``fk_taxels``)
"""

from __future__ import annotations

import threading

import numpy as np

import rclpy
from rclpy.node import Node
from leapxela_sparshskin_msgs.msg import TaxelFrames


def _taxel_patch_colors(patch_ids: np.ndarray) -> np.ndarray:
    """Distinct RGB color per tactile patch."""
    patch_ids = np.asarray(patch_ids, dtype=np.int32)
    colors = np.zeros((patch_ids.shape[0], 3), dtype=np.float64)
    n_patches = int(patch_ids.max()) + 1 if patch_ids.size else 1
    for i in range(n_patches):
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
        colors[patch_ids == i] = np.array(rgb) + m
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


def taxel_frames_to_arrays(msg: TaxelFrames) -> dict:
    """Unpack a ``TaxelFrames`` message into numpy arrays (forces ``None`` if absent)."""
    n = len(msg.taxel_ids)
    forces_world = None
    forces_local = None
    if len(msg.forces_world) == 3 * n and len(msg.forces_local) == 3 * n:
        forces_world = np.asarray(msg.forces_world, dtype=np.float64).reshape(n, 3)
        forces_local = np.asarray(msg.forces_local, dtype=np.float64).reshape(n, 3)
    return {
        "taxel_ids": np.asarray(msg.taxel_ids, dtype=np.int32),
        "patch_ids": np.asarray(msg.patch_ids, dtype=np.int32),
        "positions": np.asarray(msg.positions, dtype=np.float64).reshape(n, 3),
        "rotations": np.asarray(msg.rotations, dtype=np.float64).reshape(n, 3, 3),
        "forces_world": forces_world,
        "forces_local": forces_local,
    }


def visulize_live_with_open3d(
    node: "FkTaxelsViewerNode",
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
    """Interactive Open3D viewer of FK taxels and contact forces, driven by live ROS.

    Controls: T taxel IDs, I FK indices, F deform, V vectors, Q quit.
    """
    import open3d as o3d

    force_vmax = 1.0
    patch_colors = None
    _LABEL_COLORS = {
        "taxel": (1.0, 0.92, 0.15),  # yellow — hardware taxel id
        "index": (0.35, 0.95, 1.0),  # cyan — FK flatten index
    }
    ids = {"taxel": None, "index": None}

    def _latest_frame():
        nonlocal force_vmax, patch_colors
        msg = node.get_latest()
        if msg is None:
            return None
        frame = taxel_frames_to_arrays(msg)
        if ids["taxel"] is None or not np.array_equal(ids["taxel"], frame["taxel_ids"]):
            ids["taxel"] = frame["taxel_ids"]
            ids["index"] = np.arange(frame["taxel_ids"].shape[0], dtype=np.int32)
            patch_colors = _taxel_patch_colors(frame["patch_ids"])
        forces_local = frame["forces_local"]
        if forces_local is not None:
            mag = np.linalg.norm(forces_local, axis=-1)
            force_vmax = max(float(np.percentile(mag, 98)), 1e-6)
        return frame["positions"], frame["rotations"], forces_local, frame["forces_world"]

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
        if label_mode is not None:
            labels = _make_taxel_id_labels(
                pos, ids[label_mode], color=_LABEL_COLORS[label_mode]
            )
        else:
            labels = o3d.geometry.TriangleMesh()
        return spheres, arrows, labels

    # Wait until the first TaxelFrames message arrives.
    node.get_logger().info("Waiting for TaxelFrames…")
    while rclpy.ok() and node.get_latest() is None:
        rclpy.spin_once(node, timeout_sec=0.1)

    geom = _frame_geometry(deform=True)
    if geom is None:
        raise RuntimeError("No TaxelFrames received")
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
            print(f"Building {mode} labels (first time may take a moment)…", flush=True)
            _taxel_id_templates(ids[mode])
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


class FkTaxelsViewerNode(Node):
    """Subscribe to ``TaxelFrames`` from ``fk_taxels`` and drive the Open3D viewer."""

    def __init__(self) -> None:
        super().__init__("fk_taxels_viewer")

        topic = self.declare_parameter("taxel_frames_topic", "taxel_frames").value

        self._lock = threading.Lock()
        self._latest: TaxelFrames | None = None
        self._updated = False

        self.create_subscription(TaxelFrames, topic, self._on_taxel_frames, 10)
        self.get_logger().info(f"Listening for TaxelFrames on '{topic}'")

    def _on_taxel_frames(self, msg: TaxelFrames) -> None:
        with self._lock:
            self._latest = msg
            self._updated = True

    def get_latest(self) -> TaxelFrames | None:
        with self._lock:
            return self._latest

    def consume_update_flag(self) -> bool:
        with self._lock:
            updated = self._updated
            self._updated = False
        return updated


def main(args=None):
    rclpy.init(args=args)
    node = FkTaxelsViewerNode()
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
