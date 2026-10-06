"""Image and events helpers shared by the JEV detectors."""

from __future__ import annotations

import json
import os

import numpy as np
from ament_index_python.packages import get_package_share_directory
from PIL import Image as PILImage
from sensor_msgs.msg import Image

# cv_bridge is not used: the Humble build is linked against NumPy 1.x and crashes under NumPy 2.
CHANNELS = {"rgb8": 3, "bgr8": 3, "rgba8": 4, "bgra8": 4, "mono8": 1}


def image_msg_to_pil(msg: Image) -> PILImage.Image:
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
    return PILImage.fromarray(np.ascontiguousarray(pixels))


def zoom_crop(
    image: PILImage.Image, zoom: float, center_x: float, center_y: float
) -> PILImage.Image:
    if zoom <= 1.0:
        return image
    width, height = image.size
    crop_w, crop_h = round(width / zoom), round(height / zoom)
    left = min(max(round(center_x * width - crop_w / 2), 0), width - crop_w)
    top = min(max(round(center_y * height - crop_h / 2), 0), height - crop_h)
    return image.crop((left, top, left + crop_w, top + crop_h))


def pil_to_image_msg(image: PILImage.Image, header) -> Image:
    msg = Image(header=header, height=image.height, width=image.width, encoding="rgb8")
    msg.step = image.width * 3
    msg.data = image.tobytes()
    return msg


def default_events_file() -> str:
    return os.path.join(get_package_share_directory("jev_event_detector"), "events.json")


def load_events(events_file: str) -> dict:
    with open(events_file) as f:
        return json.load(f)["events"]
