from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import gradio as gr
import numpy as np


def _load_sample(
    h5_path: Path, stream: str, index: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[List[Any]], Dict[str, Any]]:
    try:
        import h5py  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "This visualizer requires 'h5py'. Install it (e.g. `pip install h5py`)."
        ) from e

    idx_key = f"{int(index):06d}"
    with h5py.File(h5_path, "r") as f:
        grp = f[stream][idx_key]

        norm = np.asarray(grp["normalized_image"])

        st = grp["state"]
        names = [n.decode("utf-8") if isinstance(n, (bytes, bytearray)) else str(n) for n in st["name"][()]]
        pos = np.asarray(st["position"][()], dtype=np.float64).tolist()
        vel = np.asarray(st["velocity"][()], dtype=np.float64).tolist()
        eff = np.asarray(st["effort"][()], dtype=np.float64).tolist()

        rows: List[List[Any]] = []
        for i, name in enumerate(names):
            rows.append(
                [
                    name,
                    pos[i] if i < len(pos) else None,
                    vel[i] if i < len(vel) else None,
                    eff[i] if i < len(eff) else None,
                ]
            )

        meta: Dict[str, Any] = {
            "stream": stream,
            "index": int(index),
            "index_key": idx_key,
            "normalized_image_attrs": {
                k: _jsonable(grp["normalized_image"].attrs.get(k)) for k in grp["normalized_image"].attrs.keys()
            },
            "state_attrs": {k: _jsonable(st.attrs.get(k)) for k in st.attrs.keys()},
        }

    norm_u8 = _to_uint8_image(norm)
    ch0 = _upscale_for_display(_channel_to_rgb(norm_u8, 0), target_height=420)
    ch1 = _upscale_for_display(_channel_to_rgb(norm_u8, 1), target_height=420)
    ch2 = _upscale_for_display(_channel_to_rgb(norm_u8, 2), target_height=420)
    return ch0, ch1, ch2, rows, meta


def _jsonable(v: Any) -> Any:
    if isinstance(v, (np.generic,)):
        return v.item()
    if isinstance(v, (bytes, bytearray)):
        try:
            return v.decode("utf-8")
        except Exception:
            return repr(v)
    return v


def _to_uint8_image(arr: np.ndarray) -> np.ndarray:
    a = np.asarray(arr)
    if a.ndim == 2:
        a = a[:, :, None]
    if a.shape[-1] == 1:
        a = np.repeat(a, 3, axis=-1)
    if a.dtype == np.uint8:
        return a

    a = a.astype(np.float32, copy=False)
    if not np.isfinite(a).any():
        return np.zeros_like(a, dtype=np.uint8)

    lo = float(np.nanmin(a))
    hi = float(np.nanmax(a))
    if hi <= lo:
        return np.zeros(a.shape, dtype=np.uint8)

    a = (a - lo) / (hi - lo)
    a = np.clip(a, 0.0, 1.0)
    return (a * 255.0).round().astype(np.uint8)


def _upscale_for_display(img: np.ndarray, target_height: int = 420, max_scale: int = 50) -> np.ndarray:
    """
    The XELA images are tiny (e.g. 26x31). Gradio displays at native resolution,
    so we upscale with nearest-neighbor to make them visually inspectable.
    """
    a = np.asarray(img)
    if a.ndim != 3:
        return a
    h = int(a.shape[0])
    if h <= 0:
        return a
    scale = int(np.ceil(float(target_height) / float(h)))
    scale = max(1, min(scale, int(max_scale)))
    if scale == 1:
        return a
    a = np.repeat(a, scale, axis=0)
    a = np.repeat(a, scale, axis=1)
    return a


def _channel_to_rgb(norm_u8_rgb: np.ndarray, channel: int) -> np.ndarray:
    a = np.asarray(norm_u8_rgb)
    if a.ndim != 3 or a.shape[-1] < 3:
        raise ValueError(f"Expected HxWx3 image, got shape={a.shape}.")
    c = int(channel)
    c = 0 if c < 0 else (2 if c > 2 else c)
    g = a[:, :, c].astype(np.uint8, copy=False)

    try:
        from matplotlib import cm  # type: ignore

        rgba = cm.get_cmap("viridis_r")(g.astype(np.float32) / 255.0)
        rgb = (rgba[:, :, :3] * 255.0).round().astype(np.uint8)
        return rgb
    except Exception:
        z = np.zeros_like(g)
        return np.stack([z, g, z], axis=-1)


def _get_stream_and_count(h5_path: Path) -> Tuple[str, int]:
    try:
        import h5py  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "This visualizer requires 'h5py'. Install it (e.g. `pip install h5py`)."
        ) from e

    with h5py.File(h5_path, "r") as f:
        streams = list(f.keys())
        if not streams:
            raise RuntimeError(f"No top-level groups found in {h5_path}.")
        stream = streams[0]
        g = f[stream]
        idxs = sorted([k for k in g.keys() if str(k).isdigit()])
        return stream, len(idxs)


def main() -> None:
    default_h5 = Path(__file__).resolve().parent / "xela_data.h5"
    if not default_h5.exists():
        default_h5 = Path.cwd() / "xela_data.h5"

    stream, n = _get_stream_and_count(default_h5)
    if n <= 0:
        raise RuntimeError(f"No samples found in {default_h5} under stream '{stream}'.")

    with gr.Blocks(title="XELA dataset visualizer") as demo:
        gr.Markdown("## XELA dataset visualizer")

        with gr.Row():
            h5_path_in = gr.Textbox(
                label="HDF5 path",
                value=str(default_h5),
                interactive=True,
            )
            stream_in = gr.Textbox(
                label="Stream (top-level group)",
                value=stream,
                interactive=True,
            )

        idx = gr.Slider(
            label="current_index",
            minimum=0,
            maximum=max(0, n - 1),
            value=0,
            step=1,
        )

        with gr.Row(equal_height=True):
            ch0_out = gr.Image(label="normalized_image x", type="numpy", height=420)
            ch1_out = gr.Image(label="normalized_image y", type="numpy", height=420)
            ch2_out = gr.Image(label="normalized_image z", type="numpy", height=420)

        state_out = gr.Dataframe(
            label="state",
            value=[["", None, None, None]],
            headers=["name", "position", "velocity", "effort"],
            datatype=["str", "number", "number", "number"],
            interactive=False,
            wrap=True,
        )
        meta_out = gr.JSON(label="metadata")

        def update(h5_path: str, stream_name: str, index: int):
            ch0, ch1, ch2, rows, meta = _load_sample(Path(h5_path), stream_name, int(index))
            return ch0, ch1, ch2, rows, meta

        idx.change(
            update,
            inputs=[h5_path_in, stream_in, idx],
            outputs=[ch0_out, ch1_out, ch2_out, state_out, meta_out],
        )

        def refresh(h5_path: str, stream_name: str):
            p = Path(h5_path)
            # if stream_name invalid, fall back to first group
            try:
                import h5py  # type: ignore
            except Exception as e:
                raise RuntimeError(
                    "This visualizer requires 'h5py'. Install it (e.g. `pip install h5py`)."
                ) from e
            with h5py.File(p, "r") as f:
                if stream_name not in f:
                    streams = list(f.keys())
                    if not streams:
                        raise RuntimeError(f"No top-level groups found in {p}.")
                    stream_name = streams[0]
                g = f[stream_name]
                idxs = sorted([k for k in g.keys() if str(k).isdigit()])
                n_local = len(idxs)
            if n_local <= 0:
                raise RuntimeError(f"No samples found in {p} under stream '{stream_name}'.")
            # update slider range and also load index 0
            ch0, ch1, ch2, rows, meta = _load_sample(p, stream_name, 0)
            return (
                stream_name,
                gr.Slider(minimum=0, maximum=max(0, n_local - 1), value=0, step=1, label="current_index"),
                ch0,
                ch1,
                ch2,
                rows,
                meta,
            )

        refresh_btn = gr.Button("Reload file / refresh index range")
        refresh_btn.click(
            refresh,
            inputs=[h5_path_in, stream_in],
            outputs=[stream_in, idx, ch0_out, ch1_out, ch2_out, state_out, meta_out],
        )

    demo.launch()


if __name__ == "__main__":
    main()

