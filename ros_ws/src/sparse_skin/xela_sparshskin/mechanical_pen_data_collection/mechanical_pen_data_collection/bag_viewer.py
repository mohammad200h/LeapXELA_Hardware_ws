#!/usr/bin/env python3
"""Replay a bag recorded by ``rosbag_recorder`` in a Qt window.

Reads the bag straight from disk; nothing is published on ROS.

Usage:
  ros2 run mechanical_pen_data_collection bag_viewer [--bag PATH] [--speed 1.0]
"""

from __future__ import annotations

import argparse
import sys
import time

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets  # imported before pyqtgraph so it binds to PyQt5
import pyqtgraph as pg

from mechanical_pen_data_collection.bag_data import (
    IMAGE_TOPIC,
    XELA_TOPIC,
    BagData,
    default_bag_dir,
    newest_bag,
)
from xela_data_collection.leapXelaMap import LEAP_XELA_ID

EMPTY_CELL = 6e6  # LEAP_XELA_ID value for grid cells without a taxel
PLOTTED_JOINT_TOPICS = ("/leap_state_sim", "/leap_state", "/cmd_xela")  # top to bottom
SPEEDS = (0.25, 0.5, 1.0, 2.0, 4.0)
SLIDER_STEPS_PER_SEC = 1000
MEAN_MODE = "Per-sensor mean |delta|"

pg.setConfigOptions(imageAxisOrder="row-major", antialias=False)


def index_at(t: np.ndarray, now: float) -> int:
    """Index of the last sample at or before ``now`` (-1 if none)."""
    return int(np.searchsorted(t, now, side="right")) - 1


def no_data(plot: pg.PlotItem, topic: str) -> None:
    text = pg.TextItem(f"no data on {topic}", anchor=(0.5, 0.5))
    plot.addItem(text)
    text.setPos(0.5, 0.5)
    plot.setRange(xRange=(0, 1), yRange=(0, 1))


class _ResizingWidget(QtWidgets.QWidget):
    resized = QtCore.pyqtSignal()

    def resizeEvent(self, ev) -> None:
        super().resizeEvent(ev)
        self.resized.emit()


class Open3DTaxelView(QtWidgets.QWidget):
    """FK taxels drawn by an off-screen Open3D Visualizer, shown inside Qt.

    Same rendering as ``fk_taxels_viewer``: taxel positions from ``/leap_state_sim``
    FK, deformed and coloured by the Xela readings, with optional force arrows and
    id labels. Mouse: left-drag rotate, right/middle-drag pan, wheel zoom.
    Keys (like fk_taxels_viewer): T taxel ids, I FK indices, F deform, V vectors.
    """

    RENDER_SIZE = (960, 720)
    JOINT_TOPIC = "/leap_state_sim"

    def __init__(self, data: BagData, counts_per_unit: float) -> None:
        super().__init__()
        self.data = data
        self.counts_per_unit = counts_per_unit
        self._now: float | None = None
        self._key = None
        self._geoms: list = []
        self._camera_set = False
        self._drag_pos: QtCore.QPoint | None = None
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        controls = QtWidgets.QHBoxLayout()
        self.deform_box = QtWidgets.QCheckBox("Deform (F)")
        self.vectors_box = QtWidgets.QCheckBox("Force vectors (V)")
        self.labels_combo = QtWidgets.QComboBox()
        self.labels_combo.addItem("No labels", None)
        self.labels_combo.addItem("Taxel ids (T)", "taxel")
        self.labels_combo.addItem("FK indices (I)", "index")
        reset = QtWidgets.QPushButton("Reset view")
        for w in (self.deform_box, self.vectors_box, self.labels_combo, reset):
            controls.addWidget(w)
        controls.addStretch(1)
        vbox.addLayout(controls)
        self.image_label = QtWidgets.QLabel()
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setMinimumSize(200, 150)
        self.image_label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        vbox.addWidget(self.image_label, stretch=1)

        self._vis = None
        joints = data.joints.get(self.JOINT_TOPIC)
        if joints is None:
            self._disable(f"no data on {self.JOINT_TOPIC}")
            return
        try:
            import open3d as o3d

            from mechanical_pen_data_collection import taxel_fk_util as fk
        except Exception as e:
            self._disable(f"3D view unavailable: {e}")
            return
        self._o3d, self._fk = o3d, fk
        self._joint_t = joints.t
        self._angles = fk.joint_angles_in_fk_order(joints.names, joints.positions)
        self._has_forces = data.xela is not None and data.xela.taxels.shape[1] >= fk.NUM_TAXELS
        if self._has_forces:
            self._baseline = data.xela.taxels[0, : fk.NUM_TAXELS].astype(np.float64)
        self.deform_box.setChecked(self._has_forces)
        self.vectors_box.setChecked(self._has_forces)
        self.deform_box.setEnabled(self._has_forces)
        self.vectors_box.setEnabled(self._has_forces)

        self._vis = o3d.visualization.Visualizer()
        if not self._vis.create_window(
            window_name="taxel fk", width=self.RENDER_SIZE[0], height=self.RENDER_SIZE[1], visible=False
        ):
            self._vis = None
            self._disable("Open3D could not create an OpenGL context")
            return
        opt = self._vis.get_render_option()
        opt.mesh_show_back_face = True
        opt.background_color = np.array([0.08, 0.08, 0.1])
        self._vis.add_geometry(o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.04))

        for box in (self.deform_box, self.vectors_box):
            box.toggled.connect(lambda _: self.refresh())
        self.labels_combo.currentIndexChanged.connect(lambda _: self.refresh())
        reset.clicked.connect(self._reset_camera)
        shortcuts = {
            "F": self.deform_box.toggle,
            "V": self.vectors_box.toggle,
            "T": lambda: self._toggle_labels(1),
            "I": lambda: self._toggle_labels(2),
        }
        for key, slot in shortcuts.items():
            sc = QtWidgets.QShortcut(key, self)
            sc.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
            sc.activated.connect(slot)

    def _disable(self, reason: str) -> None:
        self.image_label.setText(reason)
        for w in (self.deform_box, self.vectors_box, self.labels_combo):
            w.setEnabled(False)

    def _toggle_labels(self, index: int) -> None:
        self.labels_combo.setCurrentIndex(0 if self.labels_combo.currentIndex() == index else index)

    # ------------------------------------------------------------- frames
    def show_time(self, now: float) -> None:
        self._now = now
        if self._vis is not None and self.isVisible():
            self.refresh()

    def showEvent(self, ev) -> None:
        super().showEvent(ev)
        if self._vis is not None and self._now is not None:
            self.refresh()

    def refresh(self) -> None:
        if self._vis is None or self._now is None:
            return
        j = max(index_at(self._joint_t, self._now), 0)
        x = max(index_at(self.data.xela.t, self._now), 0) if self._has_forces else -1
        deform, vectors = self.deform_box.isChecked(), self.vectors_box.isChecked()
        label_mode = self.labels_combo.currentData()
        key = (j, x, deform, vectors, label_mode)
        if key == self._key:
            return
        self._key = key

        fk = self._fk
        pos, rot = fk.get_fk_taxel_frames(self._angles[j])
        pos, rot = pos[0], rot[0]
        forces_local = None
        if self._has_forces:
            forces_local = fk.taxel_readings_to_local_forces(
                self.data.xela.taxels[x, : fk.NUM_TAXELS], self._baseline, self.counts_per_unit
            )
        geoms = fk.build_taxel_meshes(
            pos, rot, forces_local, deform=deform, vectors=vectors, label_mode=label_mode
        )
        for g in self._geoms:
            self._vis.remove_geometry(g, reset_bounding_box=False)
        self._geoms = [g for g in geoms if len(g.vertices) > 0]
        for g in self._geoms:
            self._vis.add_geometry(g, reset_bounding_box=not self._camera_set)
        if not self._camera_set:
            self._center = pos.mean(axis=0)
            self._reset_camera()
        else:
            self._draw()

    def _reset_camera(self) -> None:
        if self._vis is None or not self._geoms:
            return
        ctr = self._vis.get_view_control()
        ctr.set_lookat(self._center.tolist())
        # Match MuJoCo scene side view: hand extends in +Y, Z up.
        ctr.set_front([-0.55, -0.75, 0.35])
        ctr.set_up([0.0, 0.0, 1.0])
        ctr.set_zoom(0.55)
        self._camera_set = True
        self._draw()

    def _draw(self) -> None:
        self._vis.poll_events()
        self._vis.update_renderer()
        buf = np.asarray(self._vis.capture_screen_float_buffer(do_render=True))
        rgb = np.ascontiguousarray((np.clip(buf, 0.0, 1.0) * 255).astype(np.uint8))
        h, w = rgb.shape[:2]
        image = QtGui.QImage(rgb.data, w, h, 3 * w, QtGui.QImage.Format_RGB888).copy()
        self._pixmap = QtGui.QPixmap.fromImage(image)
        self._show_pixmap()

    def _show_pixmap(self) -> None:
        if getattr(self, "_pixmap", None) is not None:
            self.image_label.setPixmap(
                self._pixmap.scaled(
                    self.image_label.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
                )
            )

    def resizeEvent(self, ev) -> None:
        super().resizeEvent(ev)
        self._show_pixmap()

    # -------------------------------------------------------------- mouse
    def _render_scale(self) -> float:
        size = self.image_label.size()
        return max(min(size.width() / self.RENDER_SIZE[0], size.height() / self.RENDER_SIZE[1]), 1e-3)

    def mousePressEvent(self, ev) -> None:
        self.setFocus()
        self._drag_pos = ev.pos()

    def mouseReleaseEvent(self, ev) -> None:
        self._drag_pos = None

    def mouseMoveEvent(self, ev) -> None:
        if self._vis is None or self._drag_pos is None or not self._camera_set:
            return
        delta = (ev.pos() - self._drag_pos) / self._render_scale()
        self._drag_pos = ev.pos()
        ctr = self._vis.get_view_control()
        if ev.buttons() & QtCore.Qt.LeftButton:
            ctr.rotate(delta.x(), delta.y())
        else:
            ctr.translate(delta.x(), delta.y())
        self._draw()

    def wheelEvent(self, ev) -> None:
        if self._vis is None or not self._camera_set:
            return
        # ViewControl.scale(+n) zooms out, so wheel-up (positive delta) zooms in.
        self._vis.get_view_control().scale(-ev.angleDelta().y() / 120.0)
        self._draw()

    def close(self) -> None:
        if self._vis is not None:
            self._vis.destroy_window()
            self._vis = None


class BagViewer(QtWidgets.QMainWindow):
    def __init__(self, data: BagData, speed: float = 1.0, counts_per_unit: float = 1000.0) -> None:
        super().__init__()
        self.data = data
        self.counts_per_unit = counts_per_unit
        self.now = 0.0
        self.playing = False
        self._last_tick = time.monotonic()
        self._cursors: list[pg.InfiniteLine] = []

        self.setWindowTitle(f"Bag viewer - {data.uri}")
        self.resize(1600, 950)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_time_plots())
        splitter.setSizes([800, 800])
        layout.addWidget(splitter, stretch=1)
        layout.addLayout(self._build_transport(speed))
        self.setCentralWidget(central)

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)
        self.render()

    # ---------------------------------------------------------------- layout
    def _build_left(self) -> QtWidgets.QWidget:
        left = _ResizingWidget()
        left.resized.connect(self._balance_left)
        self._left = left
        vbox = QtWidgets.QVBoxLayout(left)
        vbox.setContentsMargins(0, 0, 0, 0)
        if self.data.image_t.size:
            h, w = self.data.image_at(0).shape[:2]
            self._camera_aspect = h / w
        else:
            self._camera_aspect = 0.75

        self._camera_widget = pg.GraphicsLayoutWidget()
        self.camera_view = self._camera_widget.addViewBox(lockAspect=True, invertY=True)
        self.camera_image = pg.ImageItem()
        self.camera_view.addItem(self.camera_image)
        if self.data.image_t.size == 0:
            self.camera_view.addItem(pg.TextItem(f"no data on {IMAGE_TOPIC}", anchor=(0.5, 0.5)))
        vbox.addWidget(self._camera_widget)

        self.taxel_tabs = QtWidgets.QTabWidget()
        vbox.addWidget(self.taxel_tabs, stretch=1)
        grid = pg.GraphicsLayoutWidget()
        self.taxel_tabs.addTab(grid, "Taxel grid")
        self.fk_view = Open3DTaxelView(self.data, self.counts_per_unit)
        self.taxel_tabs.addTab(self.fk_view, "3D FK (Open3D)")

        # Same layout as xela_data_collection's /leap_image: taxel i of the first
        # sensor sits at the LEAP_XELA_ID cell holding i, one image per x/y/z channel.
        self._taxel_images: list[pg.ImageItem] = []
        for c, label in enumerate("XYZ"):
            grid.addLabel(label, row=0, col=c)
            view = grid.addViewBox(row=1, col=c, lockAspect=True, invertY=True)
            image = pg.ImageItem()
            image.setColorMap(pg.colormap.get("viridis"))
            view.addItem(image)
            self._taxel_images.append(image)
            if self.data.xela is None:
                view.addItem(pg.TextItem(f"no data on {XELA_TOPIC}", anchor=(0.5, 0.5)))
        if self.data.xela is not None:
            ids = np.asarray(LEAP_XELA_ID, dtype=np.float64)
            n_first = int(np.count_nonzero(self.data.xela.sensor_of_taxel == 0))
            self._taxel_ids = np.arange(min(n_first, int((ids < EMPTY_CELL).sum())))
            cells = {int(ids[r, c]): (r, c) for r, c in zip(*np.nonzero(ids < EMPTY_CELL))}
            self._taxel_rows = np.array([cells[i][0] for i in self._taxel_ids])
            self._taxel_cols = np.array([cells[i][1] for i in self._taxel_ids])
            self._grid_shape = ids.shape
        return left

    def _balance_left(self) -> None:
        """Size the camera so the frame covers the same area as the three taxel grids."""
        rows, cols = np.asarray(LEAP_XELA_ID).shape
        width = max(self._left.width() - 30, 1)
        taxel_h = width / 3 * rows / cols
        camera_h = min(np.sqrt(width * taxel_h * self._camera_aspect), width * self._camera_aspect)
        self._camera_widget.setFixedHeight(int(camera_h) + 20)

    def closeEvent(self, ev) -> None:
        self.fk_view.close()
        super().closeEvent(ev)

    def _build_time_plots(self) -> QtWidgets.QWidget:
        container = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)

        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(QtWidgets.QLabel("Xela plot:"))
        self.taxel_combo = QtWidgets.QComboBox()
        controls.addWidget(self.taxel_combo, stretch=1)
        vbox.addLayout(controls)

        plots = pg.GraphicsLayoutWidget()
        vbox.addWidget(plots, stretch=1)

        first = None
        for row, topic in enumerate(PLOTTED_JOINT_TOPICS):
            plot = plots.addPlot(row=row, col=0, title=topic)
            self._setup_time_plot(plot, first)
            first = first or plot
            series = self.data.joints[topic]
            if series is None:
                no_data(plot, topic)
                continue
            plot.addLegend(offset=(5, 5), colCount=4, labelTextSize="7pt")
            n = series.positions.shape[1]
            for j in range(n):
                plot.plot(
                    series.t,
                    series.positions[:, j],
                    pen=pg.intColor(j, hues=max(n, 1)),
                    name=series.names[j] if j < len(series.names) else f"joint_{j}",
                )
            plot.setLabel("left", "rad")

        self.xela_plot = plots.addPlot(row=len(PLOTTED_JOINT_TOPICS), col=0, title=XELA_TOPIC)
        self._setup_time_plot(self.xela_plot, first)
        self.xela_plot.setLabel("bottom", "time", units="s")
        self.xela_plot.addLegend(offset=(5, 5), colCount=4, labelTextSize="7pt")
        self._xela_curves: list[pg.PlotDataItem] = []

        xela = self.data.xela
        if xela is None:
            no_data(self.xela_plot, XELA_TOPIC)
            self.taxel_combo.setEnabled(False)
        else:
            self.taxel_combo.addItem(MEAN_MODE)
            for i, s in enumerate(xela.sensor_of_taxel):
                self.taxel_combo.addItem(f"taxel {i} (sensor_pos {xela.sensor_pos[s]})")
            self.taxel_combo.currentIndexChanged.connect(self._plot_xela)
            self._plot_xela()
        return container

    def _setup_time_plot(self, plot: pg.PlotItem, link_to: pg.PlotItem | None) -> None:
        plot.showGrid(x=True, y=True, alpha=0.3)
        plot.setDownsampling(auto=True, mode="peak")
        plot.setClipToView(True)
        if link_to is not None:
            plot.setXLink(link_to)
        plot.setXRange(0.0, max(self.data.duration, 1e-3), padding=0.0)
        cursor = pg.InfiniteLine(pos=0.0, angle=90, movable=True, pen=pg.mkPen("r", width=2))
        cursor.sigDragged.connect(lambda line: self.seek(line.value()))
        plot.addItem(cursor, ignoreBounds=True)
        self._cursors.append(cursor)

    def _build_transport(self, speed: float) -> QtWidgets.QHBoxLayout:
        bar = QtWidgets.QHBoxLayout()
        self.play_button = QtWidgets.QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_play)
        bar.addWidget(self.play_button)

        self.speed_combo = QtWidgets.QComboBox()
        for s in SPEEDS:
            self.speed_combo.addItem(f"{s:g}x", s)
        nearest = min(range(len(SPEEDS)), key=lambda i: abs(SPEEDS[i] - speed))
        self.speed_combo.setCurrentIndex(nearest)
        bar.addWidget(self.speed_combo)

        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(0, int(self.data.duration * SLIDER_STEPS_PER_SEC))
        self.slider.sliderMoved.connect(lambda v: self.seek(v / SLIDER_STEPS_PER_SEC))
        bar.addWidget(self.slider, stretch=1)

        self.time_label = QtWidgets.QLabel()
        self.time_label.setMinimumWidth(140)
        bar.addWidget(self.time_label)
        return bar

    # -------------------------------------------------------------- playback
    def toggle_play(self) -> None:
        if not self.playing and self.now >= self.data.duration:
            self.now = 0.0
        self.playing = not self.playing
        self._last_tick = time.monotonic()
        self.play_button.setText("Pause" if self.playing else "Play")

    def seek(self, t: float) -> None:
        self.now = float(np.clip(t, 0.0, self.data.duration))
        self.render()

    def _tick(self) -> None:
        now = time.monotonic()
        elapsed, self._last_tick = now - self._last_tick, now
        if not self.playing:
            return
        self.now += elapsed * self.speed_combo.currentData()
        if self.now >= self.data.duration:
            self.now = self.data.duration
            self.toggle_play()
        self.render()

    # ---------------------------------------------------------------- render
    def _plot_xela(self) -> None:
        xela = self.data.xela
        for curve in self._xela_curves:
            self.xela_plot.removeItem(curve)
        self.xela_plot.legend.clear()
        self._xela_curves = []

        mode = self.taxel_combo.currentIndex()
        if mode == 0:
            n = len(xela.sensor_pos)
            for i, pos in enumerate(xela.sensor_pos):
                self._xela_curves.append(
                    self.xela_plot.plot(
                        xela.t, xela.sensor_mean_delta[:, i],
                        pen=pg.intColor(i, hues=max(n, 1)), name=f"sensor_pos {pos}",
                    )
                )
            self.xela_plot.setLabel("left", "mean |delta|")
        else:
            taxel = mode - 1
            for axis, color in zip(range(3), ("r", "g", "b")):
                self._xela_curves.append(
                    self.xela_plot.plot(
                        xela.t, xela.taxels[:, taxel, axis], pen=color, name="xyz"[axis]
                    )
                )
            self.xela_plot.setLabel("left", f"taxel {taxel} raw")
        self.xela_plot.enableAutoRange(axis="y")

    def render(self) -> None:
        now = self.now
        for cursor in self._cursors:
            cursor.setValue(now)
        self.slider.blockSignals(True)
        self.slider.setValue(int(now * SLIDER_STEPS_PER_SEC))
        self.slider.blockSignals(False)
        self.time_label.setText(f"{now:7.2f} / {self.data.duration:.2f} s")

        if self.data.image_t.size:
            idx = index_at(self.data.image_t, now)
            if idx >= 0:
                frame = self.data.image_at(idx)
                levels = (0, 255) if frame.dtype == np.uint8 else None
                self.camera_image.setImage(frame, autoLevels=levels is None, levels=levels)

        xela = self.data.xela
        if xela is not None:
            idx = max(index_at(xela.t, now), 0)
            frame = xela.taxels[idx, self._taxel_ids]
            for c, image in enumerate(self._taxel_images):
                channel = frame[:, c]
                grid = np.full(self._grid_shape, np.nan, dtype=np.float32)
                grid[self._taxel_rows, self._taxel_cols] = channel
                lo, hi = float(channel.min()), float(channel.max())
                image.setImage(grid, levels=(lo, hi if hi > lo else lo + 1.0))

        self.fk_view.show_time(now)


def main(args=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bag", help="Bag folder (default: newest under ros_ws/rosbag)")
    parser.add_argument("--speed", type=float, default=1.0, help="Initial playback speed")
    parser.add_argument(
        "--counts-per-unit",
        type=float,
        default=1000.0,
        help="Raw Xela counts per force unit for the 3D FK deformation/arrows",
    )
    opts, qt_args = parser.parse_known_args(args)

    bag = opts.bag or newest_bag()
    if bag is None:
        parser.error(f"No bag given and none found under {default_bag_dir()}")

    app = QtWidgets.QApplication([sys.argv[0], *qt_args])
    print(f"Loading {bag} ...", flush=True)
    viewer = BagViewer(BagData(bag), speed=opts.speed, counts_per_unit=opts.counts_per_unit)
    viewer.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
