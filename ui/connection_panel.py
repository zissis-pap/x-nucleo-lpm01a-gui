"""
Connection panel – serial port selection, connect/disconnect, device info.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QVBoxLayout, QWidget, QFrame,
)

from core.serial_worker import SerialWorker


class ConnectionPanel(QGroupBox):
    """Widgets for selecting and opening the serial port."""

    connect_requested = pyqtSignal(str)       # port name
    disconnect_requested = pyqtSignal()
    scan_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Connection", parent)
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(10, 14, 10, 10)

        # Port row
        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(110)
        self.port_combo.setToolTip("Select the COM / ttyUSB port")
        port_row.addWidget(self.port_combo, 1)
        self.scan_btn = QPushButton("Scan")
        self.scan_btn.setFixedWidth(52)
        self.scan_btn.setToolTip("Refresh port list")
        self.scan_btn.clicked.connect(self._on_scan)
        port_row.addWidget(self.scan_btn)
        root.addLayout(port_row)

        # Connect / Disconnect row
        btn_row = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setObjectName("connect_btn")
        self.connect_btn.setToolTip(
            f"Open port at {SerialWorker.BAUD_RATE:,} baud"
        )
        self.connect_btn.clicked.connect(self._on_connect)
        btn_row.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setObjectName("disconnect_btn")
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.clicked.connect(self.disconnect_requested)
        btn_row.addWidget(self.disconnect_btn)
        root.addLayout(btn_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        root.addWidget(sep)

        # Status / info labels
        grid = QVBoxLayout()
        grid.setSpacing(4)

        self.status_lbl = self._info_row(grid, "Status:", "Not connected")
        self.status_lbl.setObjectName("status_err")

        self.board_id_lbl = self._info_row(grid, "Board ID:", "–")
        self.fw_ver_lbl = self._info_row(grid, "Firmware:", "–")
        self.board_temp_lbl = self._info_row(grid, "Temperature:", "–")

        root.addLayout(grid)
        root.addStretch()

        # Populate port list at start-up
        self.refresh_ports()

    def _info_row(self, layout: QVBoxLayout, label: str, value: str) -> QLabel:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(90)
        val = QLabel(value)
        val.setObjectName("stat_value")
        row.addWidget(lbl)
        row.addWidget(val, 1)
        layout.addLayout(row)
        return val

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_scan(self) -> None:
        self.refresh_ports()
        self.scan_requested.emit()

    def _on_connect(self) -> None:
        port = self.port_combo.currentText()
        if port:
            self.connect_requested.emit(port)

    # ── Public helpers ────────────────────────────────────────────────────────

    def refresh_ports(self) -> None:
        current = self.port_combo.currentText()
        ports = SerialWorker.list_ports()
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        if current in ports:
            self.port_combo.setCurrentText(current)

    def set_connected(self, connected: bool, message: str = "") -> None:
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)
        self.port_combo.setEnabled(not connected)
        self.scan_btn.setEnabled(not connected)

        if connected:
            self.status_lbl.setText("Connected")
            self.status_lbl.setObjectName("status_ok")
        else:
            self.status_lbl.setText("Disconnected")
            self.status_lbl.setObjectName("status_err")
            self.board_id_lbl.setText("–")
            self.fw_ver_lbl.setText("–")
            self.board_temp_lbl.setText("–")

        # Force stylesheet re-evaluation (objectName change)
        self.status_lbl.style().unpolish(self.status_lbl)
        self.status_lbl.style().polish(self.status_lbl)

    def set_board_id(self, board_id: str) -> None:
        self.board_id_lbl.setText(board_id)

    def set_firmware(self, version: str) -> None:
        self.fw_ver_lbl.setText(version)

    def set_temperature(self, temp: str) -> None:
        self.board_temp_lbl.setText(temp)
