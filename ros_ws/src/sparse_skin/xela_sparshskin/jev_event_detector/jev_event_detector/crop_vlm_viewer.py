#!/usr/bin/env python3
"""Show the crops ``crop_vlm`` publishes and where they sit in the camera frame.

Subscribes:
  - std_msgs/String on ``{topic_prefix}/boxes``, the boxes JSON from ``crop_vlm``
  - sensor_msgs/Image on ``{topic_prefix}/{object}/task_{i}``, one per task
  - sensor_msgs/Image on ``/camera/color/image_raw``, drawn with every box

Task tiles are created from the boxes messages, so tasks added to ``crop.json``
show up without changing the viewer. A tile with an invalid box is outlined red
and shows the full frame, as ``crop_vlm`` publishes it.
"""

from __future__ import annotations

import json
import signal
import sys
import time

import rclpy
from PyQt5 import QtCore, QtGui, QtWidgets
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String

from jev_event_detector.image_utils import image_msg_to_pil

BOX_COLORS = ["#2ecc71", "#3a7bd5", "#f1c40f", "#e67e22", "#9b59b6", "#1abc9c"]
INVALID_COLOR = "#e74c3c"
STALE_AFTER_S = 5.0


def pil_to_pixmap(image) -> QtGui.QPixmap:
    image = image.convert("RGB")
    qimage = QtGui.QImage(
        image.tobytes(), image.width, image.height, image.width * 3, QtGui.QImage.Format_RGB888
    ).copy()
    return QtGui.QPixmap.fromImage(qimage)


class ScaledImage(QtWidgets.QLabel):
    """A label that keeps its pixmap scaled to fit, preserving aspect ratio."""

    def __init__(self, placeholder: str) -> None:
        super().__init__(placeholder)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setMinimumSize(200, 150)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.setStyleSheet("background: black; color: #aaa;")
        self._pixmap: QtGui.QPixmap | None = None

    def set_pixmap(self, pixmap: QtGui.QPixmap) -> None:
        self._pixmap = pixmap
        self._rescale()

    def _rescale(self) -> None:
        if self._pixmap is not None:
            self.setPixmap(self._pixmap.scaled(
                self.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            ))

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._rescale()


class TaskTile(QtWidgets.QGroupBox):
    """One task: its question, the crop, and the raw box text."""

    def __init__(self, title: str, question: str, color: str) -> None:
        super().__init__(title)
        self.color = color
        question_label = QtWidgets.QLabel(question)
        question_label.setWordWrap(True)
        self.image = ScaledImage("Waiting for crop ...")
        self._box = QtWidgets.QLabel("")
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(question_label)
        layout.addWidget(self.image, stretch=1)
        layout.addWidget(self._box)
        self.set_box("", None)

    def set_box(self, raw: str, bbox: list[float] | None) -> None:
        color = self.color if bbox is not None else INVALID_COLOR
        self.setStyleSheet(
            f"QGroupBox {{ border: 2px solid {color}; margin-top: 1.2em; font-weight: bold; }}"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; }"
        )
        if bbox is None:
            self._box.setText(f"invalid box: {raw!r}" if raw else "")
        else:
            self._box.setText("box %: " + ", ".join(f"{v:.0f}" for v in bbox))


class CropVlmViewerWindow(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CropVLM_Viewer")
        self.resize(1400, 800)

        self.frame = ScaledImage("Waiting for camera ...")
        self._tiles_widget = QtWidgets.QWidget()
        self._tiles_layout = QtWidgets.QGridLayout(self._tiles_widget)
        self._status = QtWidgets.QLabel("Waiting for boxes ...")
        self.tiles: dict[tuple[str, int], TaskTile] = {}
        self.boxes: list[dict] = []

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(self.frame)
        splitter.addWidget(self._tiles_widget)
        splitter.setSizes([700, 700])
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(splitter, stretch=1)
        layout.addWidget(self._status)

    def show_boxes(self, data: dict) -> list[tuple[str, int]]:
        """Update tiles from a boxes message and return any tasks that are new."""
        new_tasks = []
        for crop in data["crops"]:
            key = (crop["object"], crop["task"])
            if key not in self.tiles:
                color = BOX_COLORS[len(self.tiles) % len(BOX_COLORS)]
                tile = TaskTile(f"{key[0]} / task_{key[1]}", crop["question"], color)
                columns = 2
                index = len(self.tiles)
                self._tiles_layout.addWidget(tile, index // columns, index % columns)
                self.tiles[key] = tile
                new_tasks.append(key)
            self.tiles[key].set_box(crop["raw"], crop["bbox_pct"])
        self.boxes = data["crops"]
        valid = sum(c["valid"] for c in data["crops"])
        self._status.setText(
            f"Latency {data['latency_ms']:.0f} ms  |  valid boxes {valid}/{len(data['crops'])}"
        )
        return new_tasks

    def show_frame(self, image) -> None:
        pixmap = pil_to_pixmap(image)
        painter = QtGui.QPainter(pixmap)
        pen_width = max(2, pixmap.width() // 300)
        font = painter.font()
        font.setPointSize(max(10, pixmap.width() // 60))
        painter.setFont(font)
        for crop in self.boxes:
            bbox = crop["bbox_pct"]
            if bbox is None:
                continue
            tile = self.tiles.get((crop["object"], crop["task"]))
            color = QtGui.QColor(tile.color if tile else BOX_COLORS[0])
            painter.setPen(QtGui.QPen(color, pen_width))
            x1, y1, x2, y2 = (v / 100 for v in bbox)
            rect = QtCore.QRectF(
                x1 * pixmap.width(), y1 * pixmap.height(),
                (x2 - x1) * pixmap.width(), (y2 - y1) * pixmap.height(),
            )
            painter.drawRect(rect)
            painter.drawText(rect.topLeft() + QtCore.QPointF(4, -4), f"task_{crop['task']}")
        painter.end()
        self.frame.set_pixmap(pixmap)

    def mark_stale(self, seconds: float) -> None:
        self._status.setText(f"No boxes for {seconds:.0f} s - is crop_vlm running?")


class CropVlmViewer(Node):
    """Feed boxes, crops and the camera frame into the Qt window."""

    def __init__(self, window: CropVlmViewerWindow) -> None:
        super().__init__("CropVLM_Viewer")
        self._prefix = self.declare_parameter("topic_prefix", "/crop_vlm").value.rstrip("/")
        image_topic = self.declare_parameter("image_topic", "/camera/color/image_raw").value
        self._window = window
        self._last_boxes_time: float | None = None
        self._started = time.monotonic()
        self._latest_frame: Image | None = None

        self.create_subscription(
            String, f"{self._prefix}/boxes", self._on_boxes, QoSProfile(depth=10)
        )
        self.create_subscription(Image, image_topic, self._on_frame, qos_profile_sensor_data)
        self.get_logger().info(f"Showing '{self._prefix}' crops over '{image_topic}'")

    def _on_boxes(self, msg: String) -> None:
        self._last_boxes_time = time.monotonic()
        for name, index in self._window.show_boxes(json.loads(msg.data)):
            tile = self._window.tiles[(name, index)]
            self.create_subscription(
                Image,
                f"{self._prefix}/{name}/task_{index}",
                lambda m, tile=tile: tile.image.set_pixmap(pil_to_pixmap(image_msg_to_pil(m))),
                qos_profile_sensor_data,
            )

    def _on_frame(self, msg: Image) -> None:
        self._latest_frame = msg

    def draw_frame(self) -> None:
        msg, self._latest_frame = self._latest_frame, None
        if msg is not None:
            self._window.show_frame(image_msg_to_pil(msg))

    def check_stale(self) -> None:
        last = self._last_boxes_time or self._started
        if time.monotonic() - last > STALE_AFTER_S:
            self._window.mark_stale(time.monotonic() - last)


def main(args=None):
    rclpy.init(args=args)
    app = QtWidgets.QApplication(sys.argv[:1])
    window = CropVlmViewerWindow()
    node = CropVlmViewer(window)
    window.show()
    signal.signal(signal.SIGINT, lambda *_: app.quit())

    def spin() -> None:
        if not rclpy.ok():
            app.quit()
            return
        try:
            rclpy.spin_once(node, timeout_sec=0)
        except ExternalShutdownException:
            app.quit()

    spin_timer = QtCore.QTimer()
    spin_timer.timeout.connect(spin)
    spin_timer.start(10)
    # The camera runs at ~30 Hz; redrawing the full frame at 10 Hz keeps the UI responsive.
    frame_timer = QtCore.QTimer()
    frame_timer.timeout.connect(node.draw_frame)
    frame_timer.start(100)
    stale_timer = QtCore.QTimer()
    stale_timer.timeout.connect(node.check_stale)
    stale_timer.start(1000)

    try:
        app.exec_()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
