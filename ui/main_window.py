"""
Main application window.

Layout
──────
  ┌─────────────────────────────────────────────────────────┐
  │ Left sidebar (280 px)    │ Centre area                  │
  │  ConnectionPanel         │  PlotWidget (stretches)      │
  │  ConfigPanel             │  StatsPanel (below plot)     │
  │  ControlPanel            ├──────────────────────────────┤
  │                          │ ConsoleWidget (bottom drawer)│
  └─────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication, QHBoxLayout, QMainWindow,
    QScrollArea, QSplitter, QStatusBar,
    QVBoxLayout, QWidget,
)

from core.data_parser import ParsedData
from core.protocol import Commands
from core.serial_worker import SerialWorker
from ui.config_panel import ConfigPanel
from ui.connection_panel import ConnectionPanel
from ui.console_widget import ConsoleWidget
from ui.control_panel import ControlPanel
from ui.plot_widget import PlotWidget
from ui.stats_panel import StatsPanel


class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("X-NUCLEO-LPM01A  Power Monitor")
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)

        # ── Serial worker ─────────────────────────────────────────────────────
        self._worker = SerialWorker(self)
        self._worker.conn_changed.connect(self._on_conn_changed)
        self._worker.log_message.connect(self._on_log)
        self._worker.cmd_result.connect(self._on_cmd_result)
        self._worker.data_ready.connect(self._on_data_ready)
        self._worker.acq_changed.connect(self._on_acq_changed)

        # ── Build UI ──────────────────────────────────────────────────────────
        self._build_ui()
        self._wire_signals()

        # ── Periodic plot refresh (50 ms = 20 FPS) ─────────────────────────
        # The plot widget itself calls _update_curve on add_samples, but we
        # also need to refresh when samples arrive in bursts.
        self._plot_timer = QTimer(self)
        self._plot_timer.setInterval(50)
        # (No separate timer needed – PlotWidget updates on add_samples)

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Not connected – select a port and click Connect.")

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # ── Left sidebar ──────────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setFixedWidth(290)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(6)

        self.conn_panel   = ConnectionPanel()
        self.config_panel = ConfigPanel()
        self.ctrl_panel   = ControlPanel()

        # Wrap config panel in a scroll area so it doesn't overflow on small screens
        config_scroll = QScrollArea()
        config_scroll.setWidget(self.config_panel)
        config_scroll.setWidgetResizable(True)
        config_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        config_scroll.setFrameShape(0)   # no border

        sidebar_layout.addWidget(self.conn_panel)
        sidebar_layout.addWidget(config_scroll, 1)
        sidebar_layout.addWidget(self.ctrl_panel)

        # ── Right / centre area ───────────────────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        # Plot + stats side-by-side
        plot_stats = QSplitter(Qt.Horizontal)
        self.plot_widget = PlotWidget()
        self.stats_panel = StatsPanel()
        self.stats_panel.setFixedWidth(220)
        plot_stats.addWidget(self.plot_widget)
        plot_stats.addWidget(self.stats_panel)
        plot_stats.setStretchFactor(0, 1)
        plot_stats.setStretchFactor(1, 0)
        plot_stats.setCollapsible(1, False)

        # Vertical splitter: plot area on top, console on bottom
        vert_splitter = QSplitter(Qt.Vertical)
        vert_splitter.addWidget(plot_stats)
        self.console = ConsoleWidget()
        vert_splitter.addWidget(self.console)
        vert_splitter.setSizes([560, 180])
        vert_splitter.setStretchFactor(0, 3)
        vert_splitter.setStretchFactor(1, 1)

        right_layout.addWidget(vert_splitter)

        # Assemble main layout
        main_layout.addWidget(sidebar)
        main_layout.addWidget(right, 1)

    def _wire_signals(self) -> None:
        # Connection panel
        self.conn_panel.connect_requested.connect(self._on_connect_requested)
        self.conn_panel.disconnect_requested.connect(self._on_disconnect_requested)

        # Config panel
        self.config_panel.apply_requested.connect(self._on_apply_config)

        # Control panel
        self.ctrl_panel.start_requested.connect(self._on_start_acquisition)
        self.ctrl_panel.stop_requested.connect(self._on_stop_acquisition)
        self.ctrl_panel.htc_requested.connect(
            lambda: self._send(Commands.htc(), "htc")
        )
        self.ctrl_panel.hrc_requested.connect(
            lambda: self._send(Commands.hrc(), "hrc")
        )
        self.ctrl_panel.temp_requested.connect(
            lambda: self._send(Commands.temp("degc"), "temp")
        )
        self.ctrl_panel.calib_requested.connect(
            lambda: self._send(Commands.calib(), "calib")
        )
        self.ctrl_panel.autotest_requested.connect(
            lambda: self._send(Commands.autotest(), "autotest")
        )
        self.ctrl_panel.psrst_requested.connect(
            lambda: self._send(Commands.psrst(), "psrst")
        )
        self.ctrl_panel.targrst_requested.connect(self._on_targrst)

        # Console raw command
        self.console.command_entered.connect(self._on_raw_command)

        # Stats clear
        self.stats_panel.clear_requested.connect(self.plot_widget.clear)

    # ── Serial event handlers ─────────────────────────────────────────────────

    def _on_conn_changed(self, connected: bool, message: str) -> None:
        self.conn_panel.set_connected(connected, message)
        self.config_panel.set_connected(connected)
        self.ctrl_panel.set_connected(connected)
        self._status_bar.showMessage(message)
        self.console.append(f"[{'Connected' if connected else 'Disconnected'}] {message}")

        if connected:
            # Auto-probe the device
            self._send(Commands.powershield(), "powershield")
            self._send(Commands.version(), "version")
            self._send(Commands.htc(), "htc")
            self.ctrl_panel.enable_start(True)
        else:
            self.ctrl_panel.enable_start(False)
            self.stats_panel.stop_acquisition()

    def _on_log(self, text: str) -> None:
        self.console.append(text)

    def _on_cmd_result(self, success: bool, cmd: str, payload: str) -> None:
        if cmd == "powershield" and success:
            # "PowerShield present XXXXX-XXXXX-XXXXX"
            board_id = payload.replace("PowerShield present", "").strip()
            self.conn_panel.set_board_id(board_id or payload)
        elif cmd == "version" and success:
            self.conn_panel.set_firmware(payload.strip())
        elif cmd == "temp" and success:
            self.conn_panel.set_temperature(payload.strip())

        prefix = "ACK" if success else "ERR"
        label = f"[{prefix}] {cmd} {payload}".strip()
        self._status_bar.showMessage(label, 4000)

    def _on_data_ready(self, result: ParsedData) -> None:
        if result.samples:
            self.plot_widget.add_samples(result.samples)
            self.stats_panel.add_samples(result.samples)

        for time_ms, buf_pct in result.timestamps:
            self.plot_widget.add_timestamp(
                self.plot_widget._total_samples, time_ms
            )
            self.stats_panel.update_buffer(buf_pct)
            self.stats_panel.update_timestamp(time_ms)

        if result.overcurrent:
            self.plot_widget.mark_overcurrent()
            self.console.append("[WARNING] Overcurrent event in data stream!")

        for err in result.errors:
            self.console.append(f"[Stream error] {err}")

        if result.end_of_acquisition:
            self.stats_panel.stop_acquisition()

    def _on_acq_changed(self, acquiring: bool) -> None:
        self.ctrl_panel.set_acquiring(acquiring)
        self.config_panel.set_enabled_controls(not acquiring)
        if acquiring:
            self.stats_panel.start_acquisition()
            freq_hz = self.config_panel.get_frequency_hz()
            self.plot_widget.set_sample_rate(freq_hz)
            self._status_bar.showMessage("Acquisition running…")
        else:
            self.stats_panel.stop_acquisition()
            self._status_bar.showMessage("Acquisition stopped.")

    # ── User action handlers ──────────────────────────────────────────────────

    def _on_connect_requested(self, port: str) -> None:
        self._worker.connect_device(port)

    def _on_disconnect_requested(self) -> None:
        self._worker.disconnect_device()

    def _on_apply_config(self, cmd_list: list[tuple[bytes, str]]) -> None:
        for cmd_bytes, name in cmd_list:
            self._send(cmd_bytes, name)

    def _on_start_acquisition(self) -> None:
        # 1. Push all configuration commands
        for cmd_bytes, name in self.config_panel.build_command_list():
            self._send(cmd_bytes, name)
        # 2. Inform the worker about data format so it routes correctly
        fmt = self.config_panel.get_data_format()
        self._worker.set_data_format(fmt)
        # 3. Clear previous data
        self.plot_widget.clear()
        self.stats_panel.clear()
        # 4. Fire start
        self._send(Commands.start(), "start")

    def _on_stop_acquisition(self) -> None:
        self._send(Commands.stop(), "stop")

    def _on_targrst(self, ms: int) -> None:
        self._send(Commands.targrst(ms), "targrst")

    def _on_raw_command(self, text: str) -> None:
        """Send any raw text typed in the console input."""
        cmd_bytes = (text.strip() + "\n").encode("ascii", errors="replace")
        self._send(cmd_bytes, text.split()[0] if text.split() else text)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _send(self, cmd_bytes: bytes, name: str = "") -> None:
        self._worker.send_command(cmd_bytes, name)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._worker.disconnect_device()
        event.accept()
