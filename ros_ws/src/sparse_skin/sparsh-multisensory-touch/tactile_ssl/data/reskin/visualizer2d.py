"""Minimal ReSkin-style 2D magfield helpers.

Upstream Sparsh (`facebookresearch/sparsh-multisensory-touch`) imports
`tactile_ssl.data.reskin.visualizer2d.plot_magnetic_heatmap` from
`tactile_ssl/data/xela/visualizer.py`, but the `reskin` package was never
published in that repo. This module restores the expected import path with
an implementation matching the call site in `create_magfield_image`.
"""

from __future__ import annotations

import numpy as np
from matplotlib import cm
from scipy.interpolate import griddata


def plot_magnetic_heatmap(
    magfield: np.ndarray,
    coords: np.ndarray,
    resolution: int,
    height: float,
    width: float,
    scale: float = 0.1,
    colormap: str = "jet",
) -> np.ndarray:
    """Rasterize a magnetic-field heatmap over a planar patch.

    Args:
        magfield: (N, 3) or (N,) field values at taxel locations.
        coords: (N, 2) taxel XY positions in millimeters.
        resolution: Output image size (pixels along height).
        height: Patch height in millimeters.
        width: Patch width in millimeters.
        scale: Unused legacy arg kept for API compatibility with Sparsh.
        colormap: Matplotlib colormap name.

    Returns:
        HxWx3 uint8 RGB image.
    """
    del scale  # Sparsh passes scale=0.1; kept for signature compatibility.
    coords = np.asarray(coords, dtype=np.float64)
    magfield = np.asarray(magfield, dtype=np.float64)
    if magfield.ndim == 2:
        values = np.linalg.norm(magfield, axis=-1)
    else:
        values = magfield.reshape(-1)

    aspect = width / max(height, 1e-6)
    h_px = int(resolution)
    w_px = max(int(round(resolution * aspect)), 1)

    grid_y, grid_x = np.mgrid[0:h_px, 0:w_px]
    sample_x = coords[:, 0] / max(width, 1e-6) * (w_px - 1)
    sample_y = coords[:, 1] / max(height, 1e-6) * (h_px - 1)

    if len(values) >= 3:
        grid = griddata(
            np.stack([sample_x, sample_y], axis=-1),
            values,
            (grid_x, grid_y),
            method="linear",
            fill_value=0.0,
        )
    else:
        grid = np.zeros((h_px, w_px), dtype=np.float64)

    vmax = np.max(np.abs(grid)) if np.any(grid) else 1.0
    normed = np.clip(grid / max(vmax, 1e-6), 0.0, 1.0)
    rgba = cm.get_cmap(colormap)(normed)
    rgb = (rgba[..., :3] * 255).astype(np.uint8)
    return np.flipud(rgb)
