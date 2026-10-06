#!/usr/bin/env python3
"""Show what the JEV event detector sees and its event probabilities.

Subscribes:
  - sensor_msgs/Image on ``/jev_crop``, the zoomed region the detector runs on
  - std_msgs/String on ``/jev_events``, the detector's JSON output

Each event gets a bar from 0 to 1 that turns green while the event is fired.
Bars are created from the event names in the messages, so events added to
``events.json`` show up without changing the viewer.
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

BAR_STYLE = """
QProgressBar {{ border: 1px solid #555; border-radius: 3px; text-align: center;
                background: #2b2b2b; color: white; font-weight: bold; }}
QProgressBar::chunk {{ background: {color}; }}
"""
IDLE_COLOR = "#3a7bd5"
FIRED_COLOR = "#2ecc71"
STALE_AFTER_S = 2.0


class EventBar(QtWidgets.QWidget):
    """One row: event name, probability bar, fired marker."""

    def __init__(self, name: str, label_width: int) -> None:
        super().__init__()
        self._label = QtWidgets.QLabel(name)
        self._label.setMinimumWidth(label_width)
        self._bar = QtWidgets.QProgressBar()
        self._bar.setRange(0, 1000)
        self._bar.setMinimumHeight(26)
        self._fired = QtWidgets.QLabel("")
        self._fired.setMinimumWidth(60)
        self._fired.setStyleSheet(f"color: {FIRED_COLOR}; font-weight: bold;")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)
        layout.addWidget(self._bar, stretch=1)
        layout.addWidget(self._fired)
        self.set_value(0.0, False)

    def set_value(self, p: float, fired: bool) -> None:
        self._bar.setValue(round(p * 1000))
        self._bar.setFormat(f"{p:.2f}")
        self._bar.setStyleSheet(BAR_STYLE.format(color=FIRED_COLOR if fired else IDLE_COLOR))
        self._fired.setText("FIRED" if fired else "")


class JevViewerWindow(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Jev_Viewer")
        self.resize(1000, 800)

        self._image = QtWidgets.QLabel("Waiting for /jev_crop ...")
        self._image.setAlignment(QtCore.Qt.AlignCenter)
        self._image.setMinimumSize(320, 180)
        self._image.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored
        )
        self._image.setStyleSheet("background: black; color: #aaa;")
        self._pixmap: QtGui.QPixmap | None = None

        self._status = QtWidgets.QLabel("Waiting for /jev_events ...")

        self._bars_box = QtWidgets.QGroupBox("Event probabilities")
        self._bars_layout = QtWidgets.QVBoxLayout(self._bars_box)
        self._bars: dict[str, EventBar] = {}

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._image, stretch=1)
        layout.addWidget(self._bars_box)
        layout.addWidget(self._status)

    def show_image(self, msg: Image) -> None:
        if msg.encoding != "rgb8":
            self._image.setText(f"Unsupported encoding '{msg.encoding}'")
            return
        qimage = QtGui.QImage(
            bytes(msg.data), msg.width, msg.height, msg.step, QtGui.QImage.Format_RGB888
        ).copy()
        self._pixmap = QtGui.QPixmap.fromImage(qimage)
        self._rescale()

    def show_events(self, data: dict) -> None:
        events = data["events"]
        if set(events) != set(self._bars):
            self._rebuild_bars(list(events))
        for name, event in events.items():
            self._bars[name].set_value(event["p"], event["fired"])
        self._status.setText(
            f"Latency {data['latency_ms']:.0f} ms  |  fired: {', '.join(data['fired']) or 'none'}"
        )

    def mark_stale(self, seconds: float) -> None:
        self._status.setText(
            f"No events for {seconds:.0f} s - is the detector running?"
        )

    def _rebuild_bars(self, names: list[str]) -> None:
        for bar in self._bars.values():
            self._bars_layout.removeWidget(bar)
            bar.deleteLater()
        metrics = QtGui.QFontMetrics(self.font())
        label_width = max(metrics.horizontalAdvance(name) for name in names) + 12
        self._bars = {name: EventBar(name, label_width) for name in names}
        for bar in self._bars.values():
            self._bars_layout.addWidget(bar)

    def _rescale(self) -> None:
        if self._pixmap is not None:
            self._image.setPixmap(self._pixmap.scaled(
                self._image.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            ))

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._rescale()


class JevViewer(Node):
    """Feed the latest crop and event message into the Qt window."""

    def __init__(self, window: JevViewerWindow) -> None:
        super().__init__("Jev_Viewer")
        crop_topic = self.declare_parameter("crop_topic", "/jev_crop").value
        events_topic = self.declare_parameter("events_topic", "/jev_events").value
        self._window = window
        self._last_event_time: float | None = None
        self._started = time.monotonic()

        self.create_subscription(Image, crop_topic, window.show_image, qos_profile_sensor_data)
        self.create_subscription(String, events_topic, self._on_events, QoSProfile(depth=10))
        self.get_logger().info(f"Showing '{crop_topic}' and '{events_topic}'")

    def _on_events(self, msg: String) -> None:
        self._last_event_time = time.monotonic()
        self._window.show_events(json.loads(msg.data))

    def check_stale(self) -> None:
        last = self._last_event_time or self._started
        if time.monotonic() - last > STALE_AFTER_S:
            self._window.mark_stale(time.monotonic() - last)


def main(args=None):
    rclpy.init(args=args)
    app = QtWidgets.QApplication(sys.argv[:1])
    window = JevViewerWindow()
    node = JevViewer(window)
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
