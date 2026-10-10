#!/usr/bin/env python3
"""Run the bounding-box node on fake RealSense frames (no camera)."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import pytest
import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import Header, String

PKG_ROOT = Path(__file__).resolve().parents[1]
if str(PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(PKG_ROOT))

try:
    from vision_msgs.msg import Detection2DArray
except ImportError:  # pragma: no cover - optional on hosts without vision_msgs
    Detection2DArray = None

WIDTH = 640
HEIGHT = 480
IMAGE_TOPIC = "/camera/color/image_raw"
DEPTH_TOPIC = "/camera/aligned_depth_to_color/image_raw"
BOXES_TOPIC = "/bounding_box/boxes"
MASK_TOPIC = "/bounding_box/mask"
ANNOTATED_TOPIC = "/bounding_box/image"
DETECTIONS_TOPIC = "/bounding_box/detections"
PEN_DEPTH_MM = 400
BG_DEPTH_MM = 800
MIN_IOU = 0.25
WAIT_TIMEOUT_SEC = 90.0


def _resolve_sam3_weights() -> Path | None:
    """Return the first existing SAM 3 checkpoint, or None."""
    candidates = []
    env_path = os.environ.get("BOUNDING_BOX_SAM3")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.append(Path.home() / ".cache" / "bounding_box" / "sam3.pt")
    candidates.append(Path("sam3.pt"))
    for path in candidates:
        if path.is_file():
            return path.resolve()
    return None


def _iou_xyxy(box_a: list[float], box_b: list[float]) -> float:
    """Intersection-over-union of two ``[x1, y1, x2, y2]`` boxes."""
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union else 0.0


def _rotated_poly(center, size, angle_deg) -> np.ndarray:
    """Return integer polygon points for a rotated rectangle."""
    return cv2.boxPoints((center, size, angle_deg)).astype(np.int32)


def _draw_synthetic_pen(width: int = WIDTH, height: int = HEIGHT):
    """Draw a desk scene with a ballpoint pen and return rgb, xyxy, mask."""
    rng = np.random.default_rng(0)
    base = np.array([206.0, 184.0, 152.0], dtype=np.float32)
    rgb = np.clip(base + rng.normal(0.0, 7.0, (height, width, 3)), 0, 255)
    rgb = rgb.astype(np.uint8)
    for y in range(0, height, 6):
        shade = int(rng.integers(-14, 14))
        rgb[y: y + 2] = np.clip(rgb[y: y + 2].astype(np.int16) + shade, 0, 255)

    angle = -11.0
    center = (328.0, 246.0)
    barrel = _rotated_poly(center, (300.0, 20.0), angle)
    highlight = _rotated_poly((center[0], center[1] - 4.0), (260.0, 5.0), angle)
    band = _rotated_poly((center[0] + 70.0, center[1]), (10.0, 20.0), angle)
    tip = _rotated_poly((center[0] + 168.0, center[1]), (36.0, 12.0), angle)
    nib = _rotated_poly((center[0] + 188.0, center[1]), (14.0, 6.0), angle)
    clicker = _rotated_poly((center[0] - 162.0, center[1]), (22.0, 10.0), angle)
    clip = _rotated_poly((center[0] - 110.0, center[1] - 14.0), (70.0, 5.0), angle)

    cv2.fillConvexPoly(rgb, barrel, (24, 28, 42))
    cv2.fillConvexPoly(rgb, highlight, (86, 96, 124))
    cv2.fillConvexPoly(rgb, band, (196, 164, 72))
    cv2.fillConvexPoly(rgb, tip, (188, 190, 196))
    cv2.fillConvexPoly(rgb, nib, (40, 40, 44))
    cv2.fillConvexPoly(rgb, clicker, (210, 212, 216))
    cv2.fillConvexPoly(rgb, clip, (170, 174, 180))

    shadow = _rotated_poly((center[0] + 6.0, center[1] + 16.0), (300.0, 10.0), angle)
    overlay = rgb.copy()
    cv2.fillConvexPoly(overlay, shadow, (150, 130, 105))
    rgb = cv2.addWeighted(overlay, 0.35, rgb, 0.65, 0)

    pen_mask = np.zeros((height, width), dtype=np.uint8)
    for poly in (barrel, highlight, band, tip, nib, clicker, clip):
        cv2.fillConvexPoly(pen_mask, poly, 255)
    ys, xs = np.nonzero(pen_mask)
    xyxy = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    return rgb, xyxy, pen_mask


def _depth_mm_to_image_msg(depth_mm: np.ndarray, header: Header) -> Image:
    """Pack an ``(H, W)`` millimetre depth image as ``16UC1``."""
    height, width = depth_mm.shape[:2]
    packed = np.ascontiguousarray(depth_mm.astype("<u2"))
    msg = Image(header=header, height=height, width=width, encoding="16UC1")
    msg.step = width * 2
    msg.is_bigendian = False
    msg.data = packed.tobytes()
    return msg


def _make_header(stamp, frame_id: str = "camera_color_optical_frame") -> Header:
    header = Header()
    header.stamp = stamp
    header.frame_id = frame_id
    return header


JEV_FRAME = Path(__file__).resolve().parent / "data" / "jev_frame.png"


def _load_jev_frame():
    """Load ``jev_frame.png`` as RGB and a flat aligned depth image."""
    bgr = cv2.imread(str(JEV_FRAME), cv2.IMREAD_COLOR)
    if bgr is None:
        pytest.fail(f"could not read {JEV_FRAME}")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    depth_mm = np.full(rgb.shape[:2], PEN_DEPTH_MM, dtype=np.uint16)
    return rgb, depth_mm


def _save_pair(rgb: np.ndarray, annotated: Image, stem: str) -> None:
    """Write the input and annotated frames under ``test/output``."""
    from bounding_box.image_utils import image_msg_to_rgb

    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(exist_ok=True)
    input_path = out_dir / f"{stem}_input.png"
    annotated_path = out_dir / f"{stem}_annotated.png"
    cv2.imwrite(str(input_path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    cv2.imwrite(
        str(annotated_path),
        cv2.cvtColor(image_msg_to_rgb(annotated), cv2.COLOR_RGB2BGR),
    )
    print(f"Wrote input image to {input_path}", flush=True)
    print(f"Wrote annotated image to {annotated_path}", flush=True)


def _await_detection(session, rgb: np.ndarray, depth_mm: np.ndarray) -> dict:
    """Publish one fake frame until a same-size detection arrives."""
    from bounding_box.image_utils import rgb_to_image_msg

    latest = session["latest"]
    for key in latest:
        latest[key] = None
    height, width = rgb.shape[:2]
    deadline = time.monotonic() + WAIT_TIMEOUT_SEC
    while time.monotonic() < deadline:
        header = _make_header(session["harness"].get_clock().now().to_msg())
        session["color_pub"].publish(rgb_to_image_msg(rgb, header))
        session["depth_pub"].publish(_depth_mm_to_image_msg(depth_mm, header))
        image = latest["image"]
        boxes = latest["boxes"]
        if (
            image is not None
            and boxes is not None
            and latest["mask"] is not None
            and image.width == width
            and image.height == height
        ):
            payload = json.loads(boxes.data)
            if payload.get("detections"):
                return payload
        time.sleep(0.1)
    pytest.fail(
        f"Timed out after {WAIT_TIMEOUT_SEC:.0f}s waiting for "
        "/bounding_box/boxes with detections"
    )


@pytest.fixture(scope="module")
def camera_node():
    """Start one bounding-box node fed by fake image publishers."""
    pytest.importorskip("ultralytics")
    weights = _resolve_sam3_weights()
    if weights is None:
        pytest.skip(
            "sam3.pt not found (set BOUNDING_BOX_SAM3 or place weights at "
            "~/.cache/bounding_box/sam3.pt)"
        )

    from bounding_box.bounding_box_node import BoundingBoxNode

    ros_args = [
        "--ros-args",
        "-p",
        f"model:={weights}",
        "-p",
        "rate_hz:=10.0",
        "-p",
        "use_depth:=true",
        "-p",
        "publish_mask:=true",
        "-p",
        "prompt:=pen",
        "-p",
        "conf:=0.25",
    ]
    if rclpy.ok():
        rclpy.shutdown()
    rclpy.init(args=ros_args)

    bbox_node = None
    harness = None
    executor = None
    spin_thread = None
    try:
        bbox_node = BoundingBoxNode()
        harness = rclpy.create_node("fake_camera_harness")
        color_pub = harness.create_publisher(Image, IMAGE_TOPIC, qos_profile_sensor_data)
        depth_pub = harness.create_publisher(Image, DEPTH_TOPIC, qos_profile_sensor_data)
        latest = {"boxes": None, "mask": None, "image": None, "detections": None}

        def _on_boxes(msg: String) -> None:
            latest["boxes"] = msg

        def _on_mask(msg: Image) -> None:
            latest["mask"] = msg

        def _on_image(msg: Image) -> None:
            latest["image"] = msg

        harness.create_subscription(String, BOXES_TOPIC, _on_boxes, 10)
        harness.create_subscription(Image, MASK_TOPIC, _on_mask, qos_profile_sensor_data)
        harness.create_subscription(
            Image, ANNOTATED_TOPIC, _on_image, qos_profile_sensor_data
        )
        if Detection2DArray is not None:
            def _on_detections(msg) -> None:
                latest["detections"] = msg

            harness.create_subscription(
                Detection2DArray, DETECTIONS_TOPIC, _on_detections, 10
            )

        executor = MultiThreadedExecutor()
        executor.add_node(bbox_node)
        executor.add_node(harness)
        spin_thread = threading.Thread(target=executor.spin, daemon=True)
        spin_thread.start()
        yield {
            "harness": harness,
            "color_pub": color_pub,
            "depth_pub": depth_pub,
            "latest": latest,
        }
    finally:
        if executor is not None:
            executor.shutdown()
        if harness is not None:
            harness.destroy_node()
        if bbox_node is not None:
            bbox_node.destroy_node()
        if spin_thread is not None:
            spin_thread.join(timeout=5.0)
        if rclpy.ok():
            rclpy.shutdown()


def _assert_mask_and_image(session, rgb: np.ndarray, stem: str) -> None:
    """Check the mask and annotated image, then write both frames to disk."""
    mask_msg = session["latest"]["mask"]
    assert mask_msg is not None
    assert mask_msg.encoding == "mono8"
    mask = np.frombuffer(mask_msg.data, dtype=np.uint8).reshape(
        mask_msg.height, mask_msg.step
    )[:, : mask_msg.width]
    assert int((mask > 0).sum()) > 0

    annotated = session["latest"]["image"]
    assert annotated is not None
    assert annotated.encoding == "rgb8"
    assert annotated.width == rgb.shape[1]
    assert annotated.height == rgb.shape[0]
    _save_pair(rgb, annotated, stem)

    if Detection2DArray is not None:
        assert session["latest"]["detections"] is not None
        assert len(session["latest"]["detections"].detections) >= 1


def test_bounding_box_on_fake_camera_frames(camera_node):
    """Publish a synthetic pen frame and expect SAM 3 to box it."""
    rgb, expected_xyxy, pen_mask = _draw_synthetic_pen()
    depth_mm = np.full((HEIGHT, WIDTH), BG_DEPTH_MM, dtype=np.uint16)
    depth_mm[pen_mask > 0] = PEN_DEPTH_MM

    payload = _await_detection(camera_node, rgb, depth_mm)
    assert payload["prompt"] == "pen"
    detections = payload["detections"]
    assert detections, "SAM 3 returned no pen detections"
    best = next((item for item in detections if item.get("best")), None)
    assert best is not None, "no detection marked best"
    iou = _iou_xyxy(best["xyxy"], list(expected_xyxy))
    assert iou >= MIN_IOU, (
        f"best box {best['xyxy']} IoU {iou:.3f} < {MIN_IOU} "
        f"vs drawn pen {expected_xyxy}"
    )
    _assert_mask_and_image(camera_node, rgb, "fake_camera")


def test_bounding_box_on_jev_frame(camera_node):
    """Publish jev_frame.png as a fake camera image and box the pen."""
    rgb, depth_mm = _load_jev_frame()
    payload = _await_detection(camera_node, rgb, depth_mm)
    assert payload["prompt"] == "pen"
    detections = payload["detections"]
    assert detections, "SAM 3 returned no pen detections on jev_frame.png"
    best = next((item for item in detections if item.get("best")), None)
    assert best is not None, "no detection marked best"
    height, width = rgb.shape[:2]
    cx = 0.5 * (best["xyxy"][0] + best["xyxy"][2])
    cy = 0.5 * (best["xyxy"][1] + best["xyxy"][3])
    assert width * 0.15 < cx < width * 0.75, f"pen center x={cx:.0f} is outside the fixture"
    assert cy > height * 0.45, f"pen center y={cy:.0f} is not in the lower half"
    _assert_mask_and_image(camera_node, rgb, "jev_frame")
