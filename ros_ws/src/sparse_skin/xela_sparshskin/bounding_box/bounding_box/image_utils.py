"""
Convert ``sensor_msgs/Image`` without cv_bridge.

The Humble cv_bridge is linked against NumPy 1.x and crashes under NumPy 2.
"""

from __future__ import annotations

import numpy as np
from sensor_msgs.msg import Image

CHANNELS = {"rgb8": 3, "bgr8": 3, "rgba8": 4, "bgra8": 4, "mono8": 1}


def image_msg_to_rgb(msg: Image) -> np.ndarray:
    """Return an (H, W, 3) uint8 RGB array from a color image message."""
    channels = CHANNELS.get(msg.encoding)
    if channels is None:
        raise ValueError(f"Unsupported image encoding '{msg.encoding}'")
    rows = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)
    pixels = rows[:, : msg.width * channels].reshape(msg.height, msg.width, channels)
    if msg.encoding.startswith("bgr"):
        pixels = pixels[..., [2, 1, 0]]
    elif channels == 4:
        pixels = pixels[..., :3]
    if channels == 1:
        pixels = np.repeat(pixels, 3, axis=2)
    return np.ascontiguousarray(pixels)


def depth_msg_to_mm(msg: Image) -> np.ndarray:
    """Return an (H, W) uint16 depth image in millimetres."""
    if msg.encoding not in ("16UC1", "mono16"):
        raise ValueError(f"Unsupported depth encoding '{msg.encoding}'")
    buf = np.frombuffer(msg.data, dtype=np.uint8)
    dtype = np.dtype(">u2" if msg.is_bigendian else "<u2")
    packed = buf.reshape(msg.height, msg.step)[:, : msg.width * 2].copy()
    return packed.view(dtype).reshape(msg.height, msg.width)


def rgb_to_image_msg(rgb: np.ndarray, header) -> Image:
    """Pack an (H, W, 3) RGB array into a ``sensor_msgs/Image``."""
    height, width = rgb.shape[:2]
    msg = Image(header=header, height=height, width=width, encoding="rgb8")
    msg.step = width * 3
    msg.data = np.ascontiguousarray(rgb).tobytes()
    return msg


def mask_to_image_msg(mask: np.ndarray, header) -> Image:
    """Pack a uint8 mask into a mono8 ``sensor_msgs/Image``."""
    binary = np.ascontiguousarray((mask > 0).astype(np.uint8) * 255)
    height, width = binary.shape[:2]
    msg = Image(header=header, height=height, width=width, encoding="mono8")
    msg.step = width
    msg.data = binary.tobytes()
    return msg
