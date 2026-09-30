#!/usr/bin/env python3

import numpy as np

import rclpy
from rclpy.node import Node

from PyQt5 import QtCore, QtWidgets

from xela_sparshskin_sim.msg import TaxelPertubation

from leap_taxel_map import LEAP_XELA_ID


BACKGROUND_VALUE = 6e6


class TaxelPertubationUi(Node):
    def __init__(self) -> None:
        super().__init__("taxel_pertubation_ui")

        self._taxel_pub = self.create_publisher(TaxelPertubation, "taxel_perturbation", 10)

        self._qt_app = None
        self._window = None
        self._spin_timer = None
        self._publish_timer = None
        self._status_label = None
        self._buttons = {}
        self._active_taxels = set()

        self._grid = np.array(LEAP_XELA_ID, dtype=float)
        self._rows, self._cols = self._grid.shape

    def publish_taxel_pertubation(self, taxel_id: int, force_xyz) -> None:
        msg = TaxelPertubation()
        msg.taxel_id = int(taxel_id)
        msg.force = [float(v) for v in force_xyz]
        self._taxel_pub.publish(msg)

        force_text = ", ".join(f"{float(v):.2f}" for v in force_xyz)
        if self._status_label is not None:
            self._status_label.setText(f"Published taxel {taxel_id}: [{force_text}]")

    def _current_force(self):
        return [
            self._fx_spin.value(),
            self._fy_spin.value(),
            self._fz_spin.value(),
        ]

    def _publish_active_taxels(self) -> None:
        force = self._current_force()
        for taxel_id in sorted(self._active_taxels):
            self.publish_taxel_pertubation(taxel_id, force)

    def _on_taxel_toggled(self, taxel_id: int, checked: bool) -> None:
        if checked:
            self._active_taxels.add(taxel_id)
            self.publish_taxel_pertubation(taxel_id, self._current_force())
            if self._status_label is not None:
                self._status_label.setText(
                    f"Taxel {taxel_id} enabled. Click again to clear it."
                )
        else:
            self._active_taxels.discard(taxel_id)
            self.publish_taxel_pertubation(taxel_id, [0.0, 0.0, 0.0])
            if self._status_label is not None:
                self._status_label.setText(f"Taxel {taxel_id} cleared.")

    def _release_all_taxels(self) -> None:
        for taxel_id in sorted(self._active_taxels):
            self.publish_taxel_pertubation(taxel_id, [0.0, 0.0, 0.0])
        self._active_taxels.clear()
        for button in self._buttons.values():
            button.blockSignals(True)
            button.setChecked(False)
            button.blockSignals(False)
        if self._status_label is not None:
            self._status_label.setText("All taxel perturbations cleared.")

    def start_ui(self) -> int:
        self._qt_app = QtWidgets.QApplication([])

        self._window = QtWidgets.QWidget()
        self._window.setWindowTitle("XELA Taxel Pertubation")
        root = QtWidgets.QVBoxLayout(self._window)

        controls = QtWidgets.QHBoxLayout()
        root.addLayout(controls)

        controls.addWidget(QtWidgets.QLabel("Fx (local)"))
        self._fx_spin = QtWidgets.QDoubleSpinBox()
        self._fx_spin.setRange(-100.0, 100.0)
        self._fx_spin.setDecimals(3)
        self._fx_spin.setSingleStep(0.1)
        self._fx_spin.setValue(0.0)
        controls.addWidget(self._fx_spin)

        controls.addWidget(QtWidgets.QLabel("Fy (local)"))
        self._fy_spin = QtWidgets.QDoubleSpinBox()
        self._fy_spin.setRange(-100.0, 100.0)
        self._fy_spin.setDecimals(3)
        self._fy_spin.setSingleStep(0.1)
        self._fy_spin.setValue(0.0)
        controls.addWidget(self._fy_spin)

        controls.addWidget(QtWidgets.QLabel("Fz (local)"))
        self._fz_spin = QtWidgets.QDoubleSpinBox()
        self._fz_spin.setRange(-100.0, 100.0)
        self._fz_spin.setDecimals(3)
        self._fz_spin.setSingleStep(0.1)
        self._fz_spin.setValue(-1.5)
        controls.addWidget(self._fz_spin)

        clear_button = QtWidgets.QPushButton("Clear All")
        clear_button.clicked.connect(self._release_all_taxels)
        controls.addWidget(clear_button)
        controls.addStretch(1)

        self._status_label = QtWidgets.QLabel(
            "Click a taxel to toggle its perturbation on or off. Forces are in the taxel local frame."
        )
        root.addWidget(self._status_label)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        root.addWidget(scroll)

        inner = QtWidgets.QWidget()
        grid_layout = QtWidgets.QGridLayout(inner)
        grid_layout.setSpacing(2)
        scroll.setWidget(inner)

        for row in range(self._rows):
            for col in range(self._cols):
                taxel_value = self._grid[row, col]
                if taxel_value == BACKGROUND_VALUE:
                    spacer = QtWidgets.QLabel("")
                    spacer.setMinimumSize(52, 36)
                    grid_layout.addWidget(spacer, row, col)
                    continue

                taxel_id = int(taxel_value)
                button = QtWidgets.QPushButton(str(taxel_id))
                button.setMinimumSize(52, 36)
                button.setCheckable(True)
                button.toggled.connect(
                    lambda checked, taxel_id=taxel_id: self._on_taxel_toggled(
                        taxel_id, checked
                    )
                )
                grid_layout.addWidget(button, row, col)
                self._buttons[taxel_id] = button

        self._spin_timer = QtCore.QTimer()
        self._spin_timer.setInterval(10)
        self._spin_timer.timeout.connect(lambda: rclpy.spin_once(self, timeout_sec=0.0))
        self._spin_timer.start()

        self._publish_timer = QtCore.QTimer()
        self._publish_timer.setInterval(100)
        self._publish_timer.timeout.connect(self._publish_active_taxels)
        self._publish_timer.start()

        self._window.resize(1400, 900)
        self._window.show()
        return int(self._qt_app.exec_())


def main(args=None) -> None:
    rclpy.init(args=args)
    node = TaxelPertubationUi()
    try:
        exit_code = node.start_ui()
    except KeyboardInterrupt:
        exit_code = 0
    finally:
        node.destroy_node()
        rclpy.shutdown()
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
