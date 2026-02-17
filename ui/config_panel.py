"""
Acquisition configuration panel.

Exposes all measurement parameters available on the PowerShield:
voltage, frequency, acquisition time / mode / function, output type,
data format, trigger, current threshold, and power settings.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QPushButton, QSlider,
    QSpinBox, QVBoxLayout, QWidget,
)

from core.protocol import Commands


class ConfigPanel(QGroupBox):
    """All acquisition configuration widgets."""

    apply_requested = pyqtSignal(list)   # list of (bytes, name) tuples to send

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Configuration", parent)
        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(10, 14, 10, 8)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setSpacing(6)
        form.setContentsMargins(0, 0, 0, 0)

        # ── Voltage ──────────────────────────────────────────────────────────
        volt_row = QHBoxLayout()
        self.volt_spin = QSpinBox()
        self.volt_spin.setRange(1800, 3300)
        self.volt_spin.setSingleStep(100)
        self.volt_spin.setValue(3300)
        self.volt_spin.setSuffix(" mV")
        self.volt_spin.setToolTip("Target power supply voltage (1800–3300 mV)")
        volt_row.addWidget(self.volt_spin)
        form.addRow("Voltage:", volt_row)

        # ── Sampling frequency ────────────────────────────────────────────────
        self.freq_combo = QComboBox()
        for hz, label in Commands.FREQ_OPTIONS:
            self.freq_combo.addItem(label, hz)
        # Default 100 Hz
        idx = next(
            (i for i, (hz, _) in enumerate(Commands.FREQ_OPTIONS) if hz == 100),
            9,
        )
        self.freq_combo.setCurrentIndex(idx)
        self.freq_combo.setToolTip("Sampling frequency")
        self.freq_combo.currentIndexChanged.connect(self._on_freq_changed)
        form.addRow("Frequency:", self.freq_combo)

        # ── Acquisition time ──────────────────────────────────────────────────
        acqtime_row = QHBoxLayout()
        self.acqtime_spin = QDoubleSpinBox()
        self.acqtime_spin.setRange(0.0001, 10.0)
        self.acqtime_spin.setDecimals(4)
        self.acqtime_spin.setValue(10.0)
        self.acqtime_spin.setSuffix(" s")
        self.acqtime_spin.setToolTip("Acquisition duration (set infinite below)")
        acqtime_row.addWidget(self.acqtime_spin)
        self.inf_check = QCheckBox("∞ Infinite")
        self.inf_check.setToolTip("Acquire indefinitely until Stop is pressed")
        self.inf_check.stateChanged.connect(self._on_inf_changed)
        acqtime_row.addWidget(self.inf_check)
        form.addRow("Acq. time:", acqtime_row)

        # ── Acquisition mode ──────────────────────────────────────────────────
        self.acqmode_combo = QComboBox()
        self.acqmode_combo.addItem("Dynamic (100 nA–10 mA)", "dyn")
        self.acqmode_combo.addItem("Static  (2 nA–200 mA)",  "stat")
        self.acqmode_combo.setToolTip(
            "Dynamic: current can vary freely\nStatic: current must be constant"
        )
        form.addRow("Acq. mode:", self.acqmode_combo)

        # ── Function mode ─────────────────────────────────────────────────────
        self.funcmode_combo = QComboBox()
        self.funcmode_combo.addItem("Optimised (100 nA–10 mA, ≤100 kHz)", "optim")
        self.funcmode_combo.addItem("High current (30 µA–10 mA, 50–100 kHz)", "high")
        self.funcmode_combo.setToolTip(
            "Optimised: best amplitude range\n"
            "High: better for large, fast currents"
        )
        form.addRow("Func. mode:", self.funcmode_combo)

        # ── Output type ───────────────────────────────────────────────────────
        self.output_combo = QComboBox()
        self.output_combo.addItem("Current (instantaneous)", "current")
        self.output_combo.addItem("Energy  (integrated)", "energy")
        self.output_combo.setToolTip(
            "Current: instantaneous A\n"
            "Energy: integrated J, reset each sample period"
        )
        form.addRow("Output:", self.output_combo)

        # ── Data format ───────────────────────────────────────────────────────
        self.format_combo = QComboBox()
        self.format_combo.addItem("ASCII decimal  (≤10 kHz)", "ascii_dec")
        self.format_combo.addItem("Binary hex     (≤100 kHz)", "bin_hexa")
        self.format_combo.setToolTip(
            "ASCII: human-readable, up to 10 kHz\n"
            "Binary: compact, up to 100 kHz"
        )
        form.addRow("Format:", self.format_combo)

        # ── Trigger source ────────────────────────────────────────────────────
        self.trigsrc_combo = QComboBox()
        self.trigsrc_combo.addItem("Software (immediate)", "sw")
        self.trigsrc_combo.addItem("External D7 pin", "d7")
        form.addRow("Trigger:", self.trigsrc_combo)

        # ── Trigger delay ─────────────────────────────────────────────────────
        self.trigdelay_spin = QSpinBox()
        self.trigdelay_spin.setRange(0, 30000)
        self.trigdelay_spin.setSingleStep(1)
        self.trigdelay_spin.setValue(1)
        self.trigdelay_spin.setSuffix(" ms")
        self.trigdelay_spin.setToolTip("Delay from trigger to start of measurement")
        form.addRow("Trig. delay:", self.trigdelay_spin)

        # ── Current threshold ─────────────────────────────────────────────────
        currthre_row = QHBoxLayout()
        self.currthre_enable = QCheckBox()
        self.currthre_enable.setChecked(False)
        self.currthre_enable.setToolTip(
            "Enable sending currthre — not supported by all firmware versions"
        )
        self.currthre_spin = QDoubleSpinBox()
        self.currthre_spin.setRange(0.0, 10.0)
        self.currthre_spin.setDecimals(3)
        self.currthre_spin.setValue(1.0)
        self.currthre_spin.setSuffix(" mA")
        self.currthre_spin.setEnabled(False)
        self.currthre_spin.setToolTip(
            "Current threshold for D2/D3 signal and LED4 event (0–10 mA)"
        )
        self.currthre_enable.stateChanged.connect(
            lambda s: self.currthre_spin.setEnabled(s == Qt.Checked)
        )
        currthre_row.addWidget(self.currthre_enable)
        currthre_row.addWidget(self.currthre_spin)
        form.addRow("Curr. thre.:", currthre_row)

        # ── Power supply ──────────────────────────────────────────────────────
        self.pwr_combo = QComboBox()
        self.pwr_combo.addItem("Auto (on at start, follows pwrend)", "auto")
        self.pwr_combo.addItem("Force ON", "on")
        self.pwr_combo.addItem("Force OFF", "off")
        form.addRow("Power:", self.pwr_combo)

        # ── Power after acquisition ───────────────────────────────────────────
        self.pwrend_combo = QComboBox()
        self.pwrend_combo.addItem("Keep ON", "on")
        self.pwrend_combo.addItem("Turn OFF", "off")
        form.addRow("Power end:", self.pwrend_combo)

        root.addLayout(form)

        # Apply button
        self.apply_btn = QPushButton("Apply configuration")
        self.apply_btn.setToolTip("Send all configuration values to the device")
        self.apply_btn.clicked.connect(self._on_apply)
        self.apply_btn.setEnabled(False)
        root.addWidget(self.apply_btn)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_inf_changed(self, state: int) -> None:
        self.acqtime_spin.setEnabled(state == Qt.Unchecked)

    def _on_freq_changed(self, _: int) -> None:
        """Warn when binary format is required for high frequencies."""
        hz = self.freq_combo.currentData()
        if hz is not None and hz > 10000:
            if self.format_combo.currentData() == "ascii_dec":
                # Auto-switch to binary
                idx = self.format_combo.findData("bin_hexa")
                self.format_combo.setCurrentIndex(idx)

    def _on_apply(self) -> None:
        self.apply_requested.emit(self.build_command_list())

    # ── Public helpers ────────────────────────────────────────────────────────

    def set_enabled_controls(self, enabled: bool) -> None:
        """Disable all controls while acquiring."""
        for w in (
            self.volt_spin, self.freq_combo, self.acqtime_spin,
            self.inf_check, self.acqmode_combo, self.funcmode_combo,
            self.output_combo, self.format_combo, self.trigsrc_combo,
            self.trigdelay_spin, self.currthre_enable,
            self.pwr_combo, self.pwrend_combo, self.apply_btn,
        ):
            w.setEnabled(enabled)
        # Keep the spin enabled only when the checkbox is also enabled
        self.currthre_spin.setEnabled(
            enabled and self.currthre_enable.isChecked()
        )

    def set_connected(self, connected: bool) -> None:
        self.apply_btn.setEnabled(connected)
        if not connected:
            self.set_enabled_controls(False)
        else:
            self.set_enabled_controls(True)

    def get_data_format(self) -> str:
        return self.format_combo.currentData() or "ascii_dec"

    def get_frequency_hz(self) -> int:
        return self.freq_combo.currentData() or 100

    def build_command_list(self) -> list[tuple[bytes, str]]:
        """Return ordered list of (cmd_bytes, name) for current settings."""
        cmds: list[tuple[bytes, str]] = []

        cmds.append((Commands.volt(self.volt_spin.value()), "volt"))
        cmds.append((Commands.freq(self.freq_combo.currentData()), "freq"))

        if self.inf_check.isChecked():
            cmds.append((Commands.acqtime_inf(), "acqtime"))
        else:
            cmds.append((Commands.acqtime(self.acqtime_spin.value()), "acqtime"))

        cmds.append((Commands.acqmode(self.acqmode_combo.currentData()), "acqmode"))
        cmds.append((Commands.funcmode(self.funcmode_combo.currentData()), "funcmode"))
        cmds.append((Commands.output(self.output_combo.currentData()), "output"))
        cmds.append((Commands.format_cmd(self.format_combo.currentData()), "format"))
        cmds.append((Commands.trigsrc(self.trigsrc_combo.currentData()), "trigsrc"))
        cmds.append((Commands.trigdelay(self.trigdelay_spin.value()), "trigdelay"))
        if self.currthre_enable.isChecked():
            cmds.append((Commands.currthre(self.currthre_spin.value()), "currthre"))
        cmds.append((Commands.pwr(self.pwr_combo.currentData()), "pwr"))
        cmds.append((Commands.pwrend(self.pwrend_combo.currentData()), "pwrend"))

        return cmds
