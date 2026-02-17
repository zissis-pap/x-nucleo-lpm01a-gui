"""
Statistics panel – live min / max / mean, sample count, elapsed time, buffer load.
"""

from __future__ import annotations

import math
import time

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QPushButton, QVBoxLayout, QWidget,
)


def _format_current(value_a: float) -> tuple[float, str]:
    """Scale a current value in Amperes to the most readable unit."""
    if value_a == 0.0:
        return 0.0, "µA"
    abs_v = abs(value_a)
    if abs_v < 1e-6:
        return value_a * 1e9, "nA"
    if abs_v < 1e-3:
        return value_a * 1e6, "µA"
    if abs_v < 1.0:
        return value_a * 1e3, "mA"
    return value_a, "A"


class StatsPanel(QGroupBox):
    """Running statistics updated in real time during acquisition."""

    clear_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Statistics", parent)
        self._reset_state()
        self._build_ui()

        self._timer = QTimer(self)
        self._timer.setInterval(200)          # refresh at 5 Hz
        self._timer.timeout.connect(self._refresh_labels)

    # ── Reset ──────────────────────────────────────────────────────────────────

    def _reset_state(self) -> None:
        self._count = 0
        self._total = 0.0
        self._min = math.inf
        self._max = -math.inf
        self._buf_pct = 0
        self._last_time_ms = 0
        self._start_wall = 0.0

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(10, 14, 10, 10)

        grid = QGridLayout()
        grid.setSpacing(4)
        grid.setColumnStretch(1, 1)

        def _row(r: int, label: str) -> QLabel:
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            val = QLabel("–")
            val.setObjectName("stat_value")
            grid.addWidget(lbl, r, 0)
            grid.addWidget(val, r, 1)
            return val

        self.current_lbl = _row(0, "Current:")
        self.min_lbl     = _row(1, "Min:")
        self.max_lbl     = _row(2, "Max:")
        self.mean_lbl    = _row(3, "Mean:")
        self.count_lbl   = _row(4, "Samples:")
        self.elapsed_lbl = _row(5, "Elapsed:")
        self.buf_lbl     = _row(6, "Buffer:")

        # Make the "Current" label bigger for live readout
        self.current_lbl.setObjectName("value_display")
        self.current_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        root.addLayout(grid)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        root.addWidget(sep)

        self.clear_btn = QPushButton("Clear data")
        self.clear_btn.setToolTip("Reset plot and statistics")
        self.clear_btn.clicked.connect(self._on_clear)
        root.addWidget(self.clear_btn)
        root.addStretch()

    # ── Public API ─────────────────────────────────────────────────────────────

    def start_acquisition(self) -> None:
        self._reset_state()
        self._start_wall = time.monotonic()
        self._timer.start()

    def stop_acquisition(self) -> None:
        self._timer.stop()
        self._refresh_labels()

    def add_samples(self, samples: list[float]) -> None:
        if not samples:
            return
        for v in samples:
            self._count += 1
            self._total += v
            if v < self._min:
                self._min = v
            if v > self._max:
                self._max = v
        # Update live current from the last sample
        self._last_value = samples[-1]

    def update_buffer(self, buf_pct: int) -> None:
        self._buf_pct = buf_pct

    def update_timestamp(self, time_ms: int) -> None:
        self._last_time_ms = time_ms

    def clear(self) -> None:
        self._reset_state()
        self._refresh_labels()

    # ── Slots ──────────────────────────────────────────────────────────────────

    def _on_clear(self) -> None:
        self.clear()
        self.clear_requested.emit()

    # ── Label refresh ──────────────────────────────────────────────────────────

    def _refresh_labels(self) -> None:
        if self._count == 0:
            for lbl in (
                self.current_lbl, self.min_lbl, self.max_lbl,
                self.mean_lbl, self.count_lbl, self.elapsed_lbl, self.buf_lbl,
            ):
                lbl.setText("–")
            return

        val, unit = _format_current(getattr(self, "_last_value", 0.0))
        self.current_lbl.setText(f"{val:+.3f} {unit}")

        mn, mn_u = _format_current(self._min)
        mx, mx_u = _format_current(self._max)
        mean, mean_u = _format_current(self._total / self._count)

        self.min_lbl.setText(f"{mn:.4f} {mn_u}")
        self.max_lbl.setText(f"{mx:.4f} {mx_u}")
        self.mean_lbl.setText(f"{mean:.4f} {mean_u}")
        self.count_lbl.setText(f"{self._count:,}")

        elapsed = time.monotonic() - self._start_wall
        self.elapsed_lbl.setText(f"{elapsed:.1f} s")
        self.buf_lbl.setText(f"{self._buf_pct} %")
