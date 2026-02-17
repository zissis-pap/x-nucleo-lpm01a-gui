"""
Control panel – Start/Stop acquisition and device utility commands.
"""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QPushButton, QVBoxLayout, QWidget,
)


class ControlPanel(QGroupBox):
    """Start / Stop plus board utility buttons."""

    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    targrst_requested = pyqtSignal(int)   # duration in ms
    temp_requested = pyqtSignal()
    calib_requested = pyqtSignal()
    autotest_requested = pyqtSignal()
    htc_requested = pyqtSignal()
    hrc_requested = pyqtSignal()
    psrst_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Controls", parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(10, 14, 10, 10)

        # ── Start / Stop ──────────────────────────────────────────────────────
        acq_row = QHBoxLayout()
        self.start_btn = QPushButton("▶  START")
        self.start_btn.setObjectName("start_btn")
        self.start_btn.setToolTip("Configure and start measurement acquisition")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_requested)
        acq_row.addWidget(self.start_btn)

        self.stop_btn = QPushButton("■  STOP")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setToolTip("Stop the current acquisition")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_requested)
        acq_row.addWidget(self.stop_btn)
        root.addLayout(acq_row)

        # ── Host control ──────────────────────────────────────────────────────
        htc_row = QHBoxLayout()
        self.htc_btn = QPushButton("Take Host Control")
        self.htc_btn.setToolTip("htc – switch from standalone to host mode")
        self.htc_btn.setEnabled(False)
        self.htc_btn.clicked.connect(self.htc_requested)
        htc_row.addWidget(self.htc_btn)

        self.hrc_btn = QPushButton("Release Control")
        self.hrc_btn.setToolTip("hrc – return to standalone mode")
        self.hrc_btn.setEnabled(False)
        self.hrc_btn.clicked.connect(self.hrc_requested)
        htc_row.addWidget(self.hrc_btn)
        root.addLayout(htc_row)

        # ── Utility buttons ───────────────────────────────────────────────────
        util_row = QHBoxLayout()
        self.temp_btn = QPushButton("Temperature")
        self.temp_btn.setToolTip("Read board temperature (°C)")
        self.temp_btn.setEnabled(False)
        self.temp_btn.clicked.connect(self.temp_requested)
        util_row.addWidget(self.temp_btn)

        self.calib_btn = QPushButton("Calibrate")
        self.calib_btn.setToolTip("Run self-calibration (do when temp shifts >5 °C)")
        self.calib_btn.setEnabled(False)
        self.calib_btn.clicked.connect(self.calib_requested)
        util_row.addWidget(self.calib_btn)
        root.addLayout(util_row)

        util2_row = QHBoxLayout()
        self.autotest_btn = QPushButton("Auto-test")
        self.autotest_btn.setToolTip("Run board self-test")
        self.autotest_btn.setEnabled(False)
        self.autotest_btn.clicked.connect(self.autotest_requested)
        util2_row.addWidget(self.autotest_btn)

        self.psrst_btn = QPushButton("Board Reset")
        self.psrst_btn.setToolTip("psrst – hardware reset of PowerShield")
        self.psrst_btn.setEnabled(False)
        self.psrst_btn.clicked.connect(self.psrst_requested)
        util2_row.addWidget(self.psrst_btn)
        root.addLayout(util2_row)

        # ── Target reset ──────────────────────────────────────────────────────
        trst_row = QHBoxLayout()
        self.targrst_btn = QPushButton("Target Reset")
        self.targrst_btn.setToolTip(
            "Power-cycle the target device for the given duration"
        )
        self.targrst_btn.setEnabled(False)
        self.targrst_btn.clicked.connect(self._on_targrst)
        trst_row.addWidget(self.targrst_btn)

        self.targrst_spin = QDoubleSpinBox()
        self.targrst_spin.setRange(0.001, 1.0)
        self.targrst_spin.setDecimals(3)
        self.targrst_spin.setValue(0.1)
        self.targrst_spin.setSuffix(" s")
        self.targrst_spin.setFixedWidth(90)
        self.targrst_spin.setToolTip("Power-off duration for target reset")
        trst_row.addWidget(self.targrst_spin)
        root.addLayout(trst_row)

        root.addStretch()

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_targrst(self) -> None:
        ms = int(self.targrst_spin.value() * 1000)
        self.targrst_requested.emit(ms)

    # ── Public helpers ─────────────────────────────────────────────────────────

    def set_connected(self, connected: bool) -> None:
        for btn in (
            self.htc_btn, self.hrc_btn, self.temp_btn,
            self.calib_btn, self.autotest_btn, self.psrst_btn,
            self.targrst_btn,
        ):
            btn.setEnabled(connected)
        if not connected:
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)

    def set_acquiring(self, acquiring: bool) -> None:
        self.start_btn.setEnabled(not acquiring)
        self.stop_btn.setEnabled(acquiring)
        # During acquisition, disable other buttons that could disrupt it
        for btn in (
            self.htc_btn, self.hrc_btn, self.calib_btn,
            self.autotest_btn, self.psrst_btn,
        ):
            btn.setEnabled(not acquiring)
        # Target reset is allowed during acquisition (monitor power-up transient)
        # Temp is also safe during acquisition
        self.targrst_btn.setEnabled(True)
        self.temp_btn.setEnabled(True)

    def enable_start(self, enabled: bool) -> None:
        self.start_btn.setEnabled(enabled)
