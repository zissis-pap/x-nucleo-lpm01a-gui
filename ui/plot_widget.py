"""
Real-time current / energy plot using pyqtgraph.

Features
────────
• Rolling circular buffer (configurable max samples)
• Adaptive Y-axis auto-range with unit scaling (nA / µA / mA / A)
• X-axis shows time in seconds (derived from sample index × sample period)
• Visual markers for timestamps, overcurrent events
• Toolbar: window size selector, clear, export CSV
"""

from __future__ import annotations

import csv
import math
from collections import deque
from typing import Optional

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel,
    QPushButton, QVBoxLayout, QWidget,
)


# Colour constants (match dark theme)
CLR_BG        = "#12121e"
CLR_CURVE     = "#00d8b0"
CLR_GRID      = "#1e2d50"
CLR_AXIS      = "#6070a0"
CLR_TIMESTAMP = "#e0c030"
CLR_OVERCURR  = "#e05050"


def _scale_current(values_a: np.ndarray) -> tuple[np.ndarray, str]:
    """Return (scaled_array, unit_string) for the best unit."""
    if len(values_a) == 0:
        return values_a, "µA"
    peak = float(np.max(np.abs(values_a)))
    if peak == 0.0 or math.isnan(peak):
        return values_a * 1e6, "µA"
    if peak < 1e-6:
        return values_a * 1e9, "nA"
    if peak < 1e-3:
        return values_a * 1e6, "µA"
    if peak < 1.0:
        return values_a * 1e3, "mA"
    return values_a, "A"


class PlotWidget(QWidget):
    """pyqtgraph-based real-time waveform widget."""

    MAX_BUFFER   = 5_000_000   # 5 M samples in ring buffer (~40 MB)
    MAX_DISPLAY  = 10_000      # points drawn at once (performance limit)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._buffer: deque[float] = deque(maxlen=self.MAX_BUFFER)
        self._sample_rate_hz: float = 100.0   # used for x-axis time scaling
        self._total_samples: int = 0          # monotonically increasing

        # Timestamp markers: (sample_index, time_ms)
        self._ts_markers: list[tuple[int, int]] = []

        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        toolbar.addWidget(QLabel("Window:"))
        self.window_combo = QComboBox()
        self.window_combo.setFixedWidth(110)
        for label, n in [
            ("All",     0),
            ("1 000",   1_000),
            ("5 000",   5_000),
            ("10 000",  10_000),
            ("50 000",  50_000),
            ("100 000", 100_000),
        ]:
            self.window_combo.addItem(label, n)
        self.window_combo.setCurrentIndex(0)
        self.window_combo.setToolTip("Number of samples visible in the plot")
        toolbar.addWidget(self.window_combo)

        toolbar.addSpacing(12)

        self.autorange_btn = QPushButton("Auto Y")
        self.autorange_btn.setCheckable(True)
        self.autorange_btn.setChecked(True)
        self.autorange_btn.setFixedWidth(70)
        self.autorange_btn.setToolTip("Toggle automatic Y-axis scaling")
        toolbar.addWidget(self.autorange_btn)

        toolbar.addStretch()

        self.export_btn = QPushButton("Export CSV")
        self.export_btn.setToolTip("Save current buffer to a CSV file")
        self.export_btn.clicked.connect(self._on_export)
        toolbar.addWidget(self.export_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setToolTip("Clear all buffered data")
        self.clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(self.clear_btn)

        root.addLayout(toolbar)

        # pyqtgraph PlotWidget
        pg.setConfigOptions(antialias=True, useOpenGL=False)
        self._pw = pg.PlotWidget()
        self._pw.setBackground(CLR_BG)
        self._pw.showGrid(x=True, y=True)
        self._pw.getAxis("bottom").setTextPen(CLR_AXIS)
        self._pw.getAxis("left").setTextPen(CLR_AXIS)
        self._pw.getAxis("bottom").setPen(CLR_AXIS)
        self._pw.getAxis("left").setPen(CLR_AXIS)
        self._pw.getAxis("bottom").setLabel("Time", units="s", color=CLR_AXIS)
        self._pw.getAxis("left").setLabel("Current", units="µA", color=CLR_AXIS)
        self._pw.setMouseEnabled(x=True, y=True)

        # Grid styling
        grid_pen = pg.mkPen(color=CLR_GRID, width=1, style=Qt.DotLine)
        self._pw.getAxis("bottom").setGrid(60)
        self._pw.getAxis("left").setGrid(60)

        # Main measurement curve
        self._curve = self._pw.plot(
            pen=pg.mkPen(color=CLR_CURVE, width=1.2),
        )

        # Infinite vertical lines for timestamps
        self._ts_lines: list[pg.InfiniteLine] = []

        root.addWidget(self._pw, 1)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_sample_rate(self, hz: float) -> None:
        self._sample_rate_hz = max(hz, 1e-3)

    def add_samples(self, samples: list[float]) -> None:
        if not samples:
            return
        self._buffer.extend(samples)
        self._total_samples += len(samples)
        self._update_curve()

    def add_timestamp(self, sample_idx: int, time_ms: int) -> None:
        self._ts_markers.append((sample_idx, time_ms))
        x = sample_idx / self._sample_rate_hz
        line = pg.InfiniteLine(
            pos=x,
            angle=90,
            pen=pg.mkPen(color=CLR_TIMESTAMP, width=1, style=Qt.DashLine),
            label=f"{time_ms / 1000:.1f}s",
            labelOpts={"color": CLR_TIMESTAMP, "position": 0.9},
        )
        self._pw.addItem(line)
        self._ts_lines.append(line)

    def mark_overcurrent(self) -> None:
        x = self._total_samples / self._sample_rate_hz
        line = pg.InfiniteLine(
            pos=x,
            angle=90,
            pen=pg.mkPen(color=CLR_OVERCURR, width=2),
            label="OC!",
            labelOpts={"color": CLR_OVERCURR, "position": 0.7},
        )
        self._pw.addItem(line)

    def clear(self) -> None:
        self._buffer.clear()
        self._total_samples = 0
        self._ts_markers.clear()
        for line in self._ts_lines:
            self._pw.removeItem(line)
        self._ts_lines.clear()
        self._curve.setData([], [])

    # ── Internal ──────────────────────────────────────────────────────────────

    def _update_curve(self) -> None:
        window = self.window_combo.currentData() or 0
        buf = list(self._buffer)

        if window > 0 and len(buf) > window:
            buf = buf[-window:]

        if not buf:
            return

        # Decimate for display if too many points
        y_raw = np.array(buf, dtype=np.float64)
        if len(y_raw) > self.MAX_DISPLAY:
            step = max(1, len(y_raw) // self.MAX_DISPLAY)
            y_raw = y_raw[::step]

        y_scaled, unit = _scale_current(y_raw)

        # X axis in seconds
        n = len(y_scaled)
        # Start sample offset within the full buffer
        buf_len = len(self._buffer)
        window_len = min(window, buf_len) if window > 0 else buf_len
        start_sample = self._total_samples - window_len
        end_sample = self._total_samples
        x = np.linspace(
            start_sample / self._sample_rate_hz,
            end_sample / self._sample_rate_hz,
            n,
        )

        self._curve.setData(x, y_scaled)

        # Update Y axis label
        self._pw.getAxis("left").setLabel("Current", units=unit, color=CLR_AXIS)

        if self.autorange_btn.isChecked():
            self._pw.enableAutoRange(axis="y")

    # ── Export ────────────────────────────────────────────────────────────────

    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "", "CSV files (*.csv)"
        )
        if not path:
            return
        data = list(self._buffer)
        dt = 1.0 / self._sample_rate_hz
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["index", "time_s", "current_A"])
            for i, v in enumerate(data):
                writer.writerow([i, f"{i * dt:.9f}", f"{v:.9e}"])
