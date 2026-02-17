"""
Real-time current / energy plot using pyqtgraph.

Performance design
──────────────────
• _RingBuffer  — pre-allocated numpy array; no Python-object overhead,
                 no full-buffer copy on every update.
• Dirty flag   — add_samples() only marks new data; a 30 FPS QTimer
                 drives rendering, completely decoupling data rate from
                 paint rate.
• Min-max decimation — preserves peaks and valleys that stride decimation
                 silently drops, at no extra cost.
• antialias=False — software anti-aliasing is expensive at large point
                 counts; disable it for the waveform (axes stay sharp).
"""

from __future__ import annotations

import csv
import math

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt, QTimer
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scale_current(values_a: np.ndarray) -> tuple[np.ndarray, str]:
    """Return (scaled_array, unit_string) for the most readable unit."""
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


def _minmax_decimate(y: np.ndarray, max_points: int) -> np.ndarray:
    """Decimate by keeping the min and max of each bin.

    Unlike stride decimation, this preserves narrow spikes and valleys that
    would otherwise be lost.  Returns at most max_points points (always even).
    """
    n = len(y)
    if n <= max_points:
        return y
    bins = max_points // 2
    length = (n // bins) * bins          # trim to a whole number of bins
    grouped = y[:length].reshape(bins, -1)
    result = np.empty(bins * 2, dtype=y.dtype)
    result[0::2] = grouped.min(axis=1)
    result[1::2] = grouped.max(axis=1)
    return result


# ---------------------------------------------------------------------------
# Ring buffer
# ---------------------------------------------------------------------------

class _RingBuffer:
    """Pre-allocated numpy circular buffer.

    Avoids the per-element Python object overhead of a deque[float] and
    allows zero-copy slicing of the tail (window) without touching the
    rest of the buffer.
    """

    def __init__(self, maxsize: int) -> None:
        self._buf    = np.empty(maxsize, dtype=np.float64)
        self._maxsize = maxsize
        self._write  = 0   # index of the next write position
        self._count  = 0   # number of valid samples (≤ maxsize)

    # -- write ----------------------------------------------------------------

    def extend(self, data: np.ndarray) -> None:
        n = len(data)
        if n == 0:
            return
        if n >= self._maxsize:
            # Incoming data fills or overflows the entire buffer
            self._buf[:] = data[-self._maxsize:]
            self._write  = 0
            self._count  = self._maxsize
            return
        end = self._write + n
        if end <= self._maxsize:
            self._buf[self._write:end] = data
        else:
            split = self._maxsize - self._write
            self._buf[self._write:] = data[:split]
            self._buf[:end - self._maxsize] = data[split:]
        self._write = end % self._maxsize
        self._count = min(self._count + n, self._maxsize)

    # -- read -----------------------------------------------------------------

    def tail(self, n: int) -> np.ndarray:
        """Return the last n samples as a contiguous array (copy)."""
        n = min(n, self._count)
        if n == 0:
            return np.empty(0, dtype=np.float64)
        end   = self._write
        start = (end - n) % self._maxsize
        if start < end:
            return self._buf[start:end].copy()
        return np.concatenate((self._buf[start:], self._buf[:end]))

    def all(self) -> np.ndarray:
        """Return every valid sample in chronological order (copy)."""
        return self.tail(self._count)

    # -- misc -----------------------------------------------------------------

    def __len__(self) -> int:
        return self._count

    def clear(self) -> None:
        self._write = 0
        self._count = 0


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------

class PlotWidget(QWidget):
    """pyqtgraph real-time waveform with rate-limited rendering."""

    MAX_BUFFER  = 5_000_000   # samples kept in ring buffer (~40 MB)
    MAX_DISPLAY = 10_000      # points sent to renderer per frame
    _REFRESH_MS = 33          # render timer interval (~30 FPS)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._ring           = _RingBuffer(self.MAX_BUFFER)
        self._sample_rate_hz = 100.0
        self._total_samples  = 0
        self._dirty          = False   # True when unrendered data exists

        self._ts_markers: list[tuple[int, int]] = []

        self._build_ui()

        # Render timer — fires at ~30 FPS, redraws only when data changed
        self._render_timer = QTimer(self)
        self._render_timer.setInterval(self._REFRESH_MS)
        self._render_timer.timeout.connect(self._maybe_update_curve)
        self._render_timer.start()

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
        self.window_combo.currentIndexChanged.connect(self._force_update)
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

        # pyqtgraph canvas — antialias off for the waveform (too costly at
        # high point counts); axes and labels remain sharp regardless.
        pg.setConfigOptions(antialias=False, useOpenGL=False)
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
        self._pw.getAxis("bottom").setGrid(60)
        self._pw.getAxis("left").setGrid(60)

        self._curve = self._pw.plot(
            pen=pg.mkPen(color=CLR_CURVE, width=1.2),
        )

        self._ts_lines: list[pg.InfiniteLine] = []

        root.addWidget(self._pw, 1)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_sample_rate(self, hz: float) -> None:
        self._sample_rate_hz = max(hz, 1e-3)

    def add_samples(self, samples: list[float]) -> None:
        """Buffer incoming samples; do NOT redraw here."""
        if not samples:
            return
        self._ring.extend(np.asarray(samples, dtype=np.float64))
        self._total_samples += len(samples)
        self._dirty = True

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
        self._ring.clear()
        self._total_samples = 0
        self._ts_markers.clear()
        for line in self._ts_lines:
            self._pw.removeItem(line)
        self._ts_lines.clear()
        self._curve.setData([], [])
        self._dirty = False

    # ── Internal ──────────────────────────────────────────────────────────────

    def _force_update(self) -> None:
        """Trigger an immediate repaint (e.g. when the window selector changes)."""
        self._dirty = True

    def _maybe_update_curve(self) -> None:
        """Timer slot: skip the paint entirely if nothing changed."""
        if not self._dirty:
            return
        self._dirty = False
        self._update_curve()

    def _update_curve(self) -> None:
        window   = self.window_combo.currentData() or 0
        n_wanted = window if window > 0 else len(self._ring)

        y_raw = self._ring.tail(n_wanted)
        if len(y_raw) == 0:
            return

        y_dec    = _minmax_decimate(y_raw, self.MAX_DISPLAY)
        y_scaled, unit = _scale_current(y_dec)

        start_sample = self._total_samples - len(y_raw)
        x = np.linspace(
            start_sample / self._sample_rate_hz,
            self._total_samples / self._sample_rate_hz,
            len(y_scaled),
        )

        self._curve.setData(x, y_scaled)
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
        data = self._ring.all()
        dt   = 1.0 / self._sample_rate_hz
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["index", "time_s", "current_A"])
            for i, v in enumerate(data):
                writer.writerow([i, f"{i * dt:.9f}", f"{v:.9e}"])
