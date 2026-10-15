#!/usr/bin/env python3
"""
Record pen clicks from the USB mic, isolate one click and save it as a template.

Workflow in the window:
  1. Record, click the pen a few times, Stop.
  2. Left-drag on the waveform to select the click. Drag the green region or its
     edges to adjust; mouse wheel zooms, middle-drag pans.
  3. Play selection to check it by ear (Play all plays the whole recording,
     with a red playhead on the waveform).
  4. Save writes the cleaned selection to ``<template_dir>/click_<timestamp>.wav``.
     The click_detector node matches against every WAV in that directory.

ROS parameters:
  - device (str, default "08bb:2902"): USB id, name substring or index of the input device
  - template_dir (str, default ~/.ros/pen_click_templates)
  - sample_rate (int, default 48000)
  - output_device (str, default "" = system default): name substring or index of the
    device "Play selection" starts on; it can be changed in the window
"""

from __future__ import annotations

import os
import signal
import sys
import threading
import time

import numpy as np
# PyQt5 must be imported before pyqtgraph, otherwise pyqtgraph picks PySide6
# (also installed) and its widgets don't belong to our PyQt5 QApplication.
from PyQt5 import QtCore, QtWidgets
import pyqtgraph as pg  # noqa: I100
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from push_button_pen_click_detection import audio_utils

try:
    import sounddevice as sd
except OSError as _exc:  # PortAudio missing; reported from main()
    sd = None
    SD_IMPORT_ERROR = _exc

LIVE_PLOT_S = 5.0
PLAYBACK_PAD_S = 0.2


class SelectViewBox(pg.ViewBox):
    """ViewBox where left-drag selects a time range; middle-drag pans, wheel zooms."""

    sigDragSelect = QtCore.pyqtSignal(float, float)

    def mouseDragEvent(self, ev, axis=None) -> None:
        if ev.button() != QtCore.Qt.LeftButton:
            super().mouseDragEvent(ev, axis)
            return
        ev.accept()
        t0 = self.mapSceneToView(ev.buttonDownScenePos()).x()
        t1 = self.mapSceneToView(ev.scenePos()).x()
        self.sigDragSelect.emit(min(t0, t1), max(t0, t1))


class ClickRecorderWindow(QtWidgets.QWidget):
    def __init__(
        self, device: int, device_name: str, sr: int, template_dir: str, output_query: str
    ) -> None:
        super().__init__()
        self.setWindowTitle("Pen click recorder")
        self.resize(1100, 700)
        self._device = device
        self._sr = sr
        self._template_dir = template_dir

        self._lock = threading.Lock()
        self._blocks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._audio = np.zeros(0, dtype=np.float32)
        self._recording = False

        # Controls
        self._record_btn = QtWidgets.QPushButton("Record")
        self._stop_btn = QtWidgets.QPushButton("Stop")
        self._play_all_btn = QtWidgets.QPushButton("Play all")
        self._play_btn = QtWidgets.QPushButton("Play selection")
        self._save_btn = QtWidgets.QPushButton("Save")
        self._record_btn.clicked.connect(self.start_recording)
        self._stop_btn.clicked.connect(self.stop_recording)
        self._play_all_btn.clicked.connect(self.play_all)
        self._play_btn.clicked.connect(self.play_selection)
        self._save_btn.clicked.connect(self.save_selection)

        self._level = QtWidgets.QProgressBar()
        self._level.setRange(0, 1000)
        self._level.setTextVisible(False)
        self._level.setMaximumHeight(12)

        buttons = QtWidgets.QHBoxLayout()
        for w in (self._record_btn, self._stop_btn, self._play_all_btn, self._play_btn,
                  self._save_btn):
            buttons.addWidget(w)
        buttons.addStretch(1)

        # Playback goes to the chosen output; the system default is often an HDMI port
        self._output_combo = QtWidgets.QComboBox()
        for index, d in enumerate(sd.query_devices()):
            if d["max_output_channels"] > 0:
                self._output_combo.addItem(f"[{index}] {d['name']}", index)
        initial = audio_utils.find_output_device(output_query) if output_query else None
        if initial is None:
            initial = sd.default.device[1]
        self._output_combo.setCurrentIndex(max(0, self._output_combo.findData(initial)))
        outputs_row = QtWidgets.QHBoxLayout()
        outputs_row.addWidget(QtWidgets.QLabel("Play on:"))
        outputs_row.addWidget(self._output_combo, stretch=1)

        # Plots
        view_box = SelectViewBox()
        view_box.sigDragSelect.connect(self._on_drag_select)
        self._wave_plot = pg.PlotWidget(
            viewBox=view_box,
            title="Recording - left-drag to select the click, wheel to zoom, middle-drag to pan",
        )
        self._wave_plot.setMouseEnabled(x=True, y=False)
        self._wave_plot.setLabel("bottom", "time", units="s")
        self._wave_plot.setYRange(-1, 1)
        self._wave_curve = self._wave_plot.plot(pen=pg.mkPen("#3a7bd5"))
        self._region = pg.LinearRegionItem(brush=pg.mkBrush(46, 204, 113, 60))
        self._region.hide()
        self._region.sigRegionChanged.connect(self._update_preview)
        self._wave_plot.addItem(self._region)
        self._playhead = pg.InfiniteLine(angle=90, pen=pg.mkPen("#e74c3c", width=2))
        self._playhead.hide()
        self._wave_plot.addItem(self._playhead)
        self._playhead_timer = QtCore.QTimer()
        self._playhead_timer.timeout.connect(self._move_playhead)
        self._play_t0 = 0.0
        self._play_started = 0.0
        self._play_duration = 0.0

        self._preview_plot = pg.PlotWidget(title="Selection after cleaning (what gets saved)")
        self._preview_plot.setLabel("bottom", "time", units="s")
        self._preview_plot.setYRange(-1, 1)
        self._preview_curve = self._preview_plot.plot(pen=pg.mkPen("#2ecc71"))

        self._status = QtWidgets.QLabel()

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(f"Input: [{device}] {device_name} @ {sr} Hz"))
        layout.addLayout(buttons)
        layout.addLayout(outputs_row)
        layout.addWidget(self._level)
        layout.addWidget(self._wave_plot, stretch=2)
        layout.addWidget(self._preview_plot, stretch=1)
        layout.addWidget(self._status)

        self._refresh_timer = QtCore.QTimer()
        self._refresh_timer.timeout.connect(self._refresh_live)
        self._set_recording_ui(False)
        self._status.setText(f"Templates are saved to {template_dir}")

    # Recording

    def start_recording(self) -> None:
        self.stop_playback()
        with self._lock:
            self._blocks = []
        self._region.hide()
        self._preview_curve.setData([], [])
        try:
            self._stream = sd.InputStream(
                device=self._device, channels=1, samplerate=self._sr,
                dtype="float32", callback=self._on_audio,
            )
            self._stream.start()
        except Exception as exc:  # noqa: BLE001 - PortAudio raises several types
            self._stream = None
            self._status.setText(f"Could not open the mic: {exc}")
            return
        self._set_recording_ui(True)
        self._refresh_timer.start(50)
        self._status.setText("Recording... click the pen a few times, then Stop.")

    def _on_audio(self, indata, frames, time_info, status) -> None:
        with self._lock:
            self._blocks.append(indata[:, 0].copy())

    def stop_recording(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._refresh_timer.stop()
        self._level.setValue(0)
        with self._lock:
            self._audio = (
                np.concatenate(self._blocks) if self._blocks else np.zeros(0, np.float32)
            )
        self._set_recording_ui(False)
        self._plot_audio(self._audio, 0.0)
        self._wave_plot.enableAutoRange(axis="x")
        if len(self._audio) == 0:
            self._status.setText("Nothing was recorded.")
            return
        self._status.setText(
            f"Recorded {len(self._audio) / self._sr:.1f} s. "
            "Left-drag on the waveform to select the click, then Play selection / Save."
        )

    def _refresh_live(self) -> None:
        with self._lock:
            blocks = list(self._blocks)
        if not blocks:
            return
        n_keep = int(LIVE_PLOT_S * self._sr)
        tail = np.concatenate(blocks[-(n_keep // len(blocks[0]) + 1):])[-n_keep:]
        total = sum(len(b) for b in blocks)
        self._plot_audio(tail, (total - len(tail)) / self._sr)
        self._level.setValue(round(min(1.0, np.abs(blocks[-1]).max()) * 1000))

    def _plot_audio(self, x: np.ndarray, t0: float) -> None:
        # Decimate with min/max envelope so long recordings stay fast to draw
        step = max(1, len(x) // 20000)
        if step > 1:
            n = len(x) // step
            frames = x[: n * step].reshape(n, step)
            y = np.empty(2 * n, dtype=np.float32)
            y[0::2] = frames.min(axis=1)
            y[1::2] = frames.max(axis=1)
            t = t0 + np.repeat(np.arange(n) * step, 2) / self._sr
        else:
            y = x
            t = t0 + np.arange(len(x)) / self._sr
        self._wave_curve.setData(t, y)

    # Selection

    def _on_drag_select(self, t_start: float, t_end: float) -> None:
        if self._recording or len(self._audio) == 0:
            return
        dur = len(self._audio) / self._sr
        self._set_region(min(max(t_start, 0.0), dur), min(max(t_end, 0.0), dur))

    def _set_region(self, t_start: float, t_end: float) -> None:
        self._region.setBounds((0, len(self._audio) / self._sr))
        self._region.setRegion((t_start, t_end))
        self._region.show()
        self._update_preview()

    def _selection(self) -> np.ndarray:
        if not self._region.isVisible() or len(self._audio) == 0:
            return np.zeros(0, np.float32)
        t_start, t_end = self._region.getRegion()
        start = max(0, int(t_start * self._sr))
        end = min(len(self._audio), int(t_end * self._sr))
        return self._audio[start:end]

    def _update_preview(self) -> None:
        sel = self._selection()
        if len(sel) == 0:
            self._preview_curve.setData([], [])
            return
        cleaned = audio_utils.clean(sel, self._sr)
        self._preview_curve.setData(np.arange(len(cleaned)) / self._sr, cleaned)

    def play_all(self) -> None:
        """Play the whole recording as captured (not cleaned)."""
        if len(self._audio) == 0:
            self._status.setText("Nothing recorded yet.")
            return
        self._play(self._audio, 0.0, "the whole recording")

    def play_selection(self) -> None:
        sel = self._selection()
        if len(sel) == 0:
            return
        self._play(
            audio_utils.clean(sel, self._sr), self._region.getRegion()[0],
            f"{len(sel) / self._sr * 1000:.0f} ms selection",
        )

    def _play(self, x: np.ndarray, t0: float, what: str) -> None:
        """Play ``x`` on the chosen output; the playhead starts at ``t0`` s in the recording."""
        device = self._output_combo.currentData()
        # Pad with silence: USB/HDMI outputs often swallow the first few ms of a stream,
        # which can be the whole click. Stereo so both ears / speakers get it.
        pad = np.zeros(int(PLAYBACK_PAD_S * self._sr), np.float32)
        clip = np.concatenate([pad, x.astype(np.float32), pad])
        channels = min(2, sd.query_devices(device)["max_output_channels"])
        self.stop_playback()
        try:
            sd.play(np.repeat(clip[:, None], channels, axis=1), self._sr, device=device)
        except Exception as exc:  # noqa: BLE001
            self._status.setText(f"Playback on [{device}] failed: {exc}")
            return
        self._play_t0 = t0
        self._play_started = time.monotonic() + PLAYBACK_PAD_S
        self._play_duration = len(x) / self._sr
        self._playhead.setValue(t0)
        self._playhead.show()
        self._playhead_timer.start(30)
        self._status.setText(f"Playing {what} on {self._output_combo.currentText()}")

    def stop_playback(self) -> None:
        sd.stop()
        self._playhead_timer.stop()
        self._playhead.hide()

    def _move_playhead(self) -> None:
        elapsed = time.monotonic() - self._play_started
        if elapsed > self._play_duration:
            self._playhead_timer.stop()
            self._playhead.hide()
            return
        self._playhead.setValue(self._play_t0 + max(0.0, elapsed))

    def save_selection(self) -> None:
        sel = self._selection()
        if len(sel) < int(0.005 * self._sr):
            self._status.setText("Select a region of at least 5 ms first.")
            return
        path = os.path.join(
            self._template_dir, time.strftime("click_%Y%m%d_%H%M%S.wav")
        )
        audio_utils.save_wav(path, audio_utils.clean(sel, self._sr), self._sr)
        self._status.setText(f"Saved {len(sel) / self._sr * 1000:.0f} ms template to {path}")

    def _set_recording_ui(self, recording: bool) -> None:
        self._record_btn.setEnabled(not recording)
        self._stop_btn.setEnabled(recording)
        self._recording = recording
        for w in (self._play_all_btn, self._play_btn, self._save_btn):
            w.setEnabled(not recording)
        self._region.setMovable(not recording)

    def closeEvent(self, event) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
        super().closeEvent(event)


class ClickRecorder(Node):
    def __init__(self) -> None:
        super().__init__("click_recorder")
        self.device_query = self.declare_parameter("device", audio_utils.DEFAULT_DEVICE).value
        self.template_dir = os.path.expanduser(
            self.declare_parameter("template_dir", audio_utils.DEFAULT_TEMPLATE_DIR).value
        )
        self.output_query = str(self.declare_parameter("output_device", "").value)
        self.sample_rate = int(
            self.declare_parameter("sample_rate", audio_utils.SAMPLE_RATE).value
        )
        os.makedirs(self.template_dir, exist_ok=True)


def main(args=None):
    rclpy.init(args=args)
    node = ClickRecorder()
    try:
        if sd is None:
            raise RuntimeError(f"{SD_IMPORT_ERROR} - install it with: apt install libportaudio2")
        device = audio_utils.find_input_device(node.device_query)
    except Exception as exc:  # noqa: BLE001 - also covers PortAudio missing
        node.get_logger().error(str(exc))
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(1)

    app = QtWidgets.QApplication(sys.argv[:1])
    window = ClickRecorderWindow(
        device, sd.query_devices(device)["name"], node.sample_rate, node.template_dir,
        node.output_query,
    )
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

    try:
        app.exec_()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
