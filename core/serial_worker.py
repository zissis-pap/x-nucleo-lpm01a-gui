"""
Serial communication worker for X-NUCLEO-LPM01A PowerShield.

Runs in a dedicated QThread to keep the GUI responsive.

State machine
─────────────
  idle        – not connected
  ready       – connected, awaiting commands
  acquiring   – streaming measurement data

Transitions
  idle  → ready         : successful serial port open
  ready → acquiring     : 'ack start' received after 'start' command
  acquiring → ready     : 'end' metadata or user sends 'stop'
  any   → idle          : disconnect / serial error
"""

from __future__ import annotations

import array
import fcntl
import struct
import sys
from typing import Optional

import serial
import serial.tools.list_ports

from PyQt5.QtCore import QMutex, QMutexLocker, QThread, pyqtSignal

from core.data_parser import AsciiParser, BinaryParser, ParsedData


# ---------------------------------------------------------------------------
# Linux: set non-standard baud rate via termios2 / ioctl
# ---------------------------------------------------------------------------
# The baud rate 3 686 400 is not in the POSIX enum, so pyserial's normal
# tcsetattr() call fails with EINVAL (22).  termios2 lets any Linux 2.6+
# kernel accept an arbitrary baud rate for the UART hardware driver.
# ---------------------------------------------------------------------------

# ioctl codes for termios2 on Linux (x86_64 and aarch64 share the same values;
# sizeof(struct termios2) = 44 = 0x2C, type byte 'T' = 0x54, nr 0x2A/0x2B)
_TCGETS2 = 0x802C542A
_TCSETS2 = 0x402C542B
_BOTHER  = 0x00001000   # use arbitrary baud rate
_CBAUD   = 0x0000100F   # baud-rate bits mask inside c_cflag

# struct termios2 layout:
#   c_iflag, c_oflag, c_cflag, c_lflag  (4 × uint32)
#   c_line                               (uint8)
#   c_cc[19]                             (19 × uint8)
#   c_ispeed, c_ospeed                   (2 × uint32)
_T2_FMT  = "IIIIB19sII"
_T2_SIZE = struct.calcsize(_T2_FMT)   # 44 bytes


def _set_custom_baudrate(fd: int, baudrate: int) -> None:
    """Apply a non-standard baud rate to an open serial fd on Linux."""
    if not sys.platform.startswith("linux"):
        return
    buf = array.array("B", b"\x00" * _T2_SIZE)
    fcntl.ioctl(fd, _TCGETS2, buf)
    parts = list(struct.unpack(_T2_FMT, bytes(buf)))
    parts[2] = (parts[2] & ~_CBAUD) | _BOTHER   # c_cflag: use BOTHER
    parts[6] = baudrate                           # c_ispeed
    parts[7] = baudrate                           # c_ospeed
    buf = array.array("B", struct.pack(_T2_FMT, *parts))
    fcntl.ioctl(fd, _TCSETS2, buf)


def _open_port(port: str, baudrate: int) -> serial.Serial:
    """
    Open a serial port, handling non-standard baud rates on Linux.

    Strategy
    --------
    1. Try to open directly – works if the OS already knows the rate.
    2. On failure, open at 9 600 baud then apply the real rate via termios2.
    """
    common_kwargs = dict(
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=0,          # non-blocking reads
        write_timeout=2.0,
    )
    try:
        ser = serial.Serial(port=port, baudrate=baudrate, **common_kwargs)
        # Even if it "opened", verify the baud is correct on Linux
        if sys.platform.startswith("linux"):
            _set_custom_baudrate(ser.fileno(), baudrate)
        return ser
    except Exception:
        pass

    # Fallback: open at a safe standard baud rate, then override
    ser = serial.Serial(port=port, baudrate=9600, **common_kwargs)
    if sys.platform.startswith("linux"):
        _set_custom_baudrate(ser.fileno(), baudrate)
    return ser


class SerialWorker(QThread):
    """Handles all serial I/O asynchronously."""

    BAUD_RATE = 3_686_400

    # ── Signals ───────────────────────────────────────────────────────────────
    conn_changed = pyqtSignal(bool, str)   # (connected, message)
    log_message = pyqtSignal(str)          # raw text for the console
    cmd_result = pyqtSignal(bool, str, str)  # (success, cmd_name, payload)
    data_ready = pyqtSignal(object)        # ParsedData  (during acquisition)
    acq_changed = pyqtSignal(bool)         # True = acquisition started

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._serial: Optional[serial.Serial] = None
        self._lock = QMutex()

        self._keep_running = False
        self._state = "idle"           # idle | ready | acquiring
        self._data_format = "ascii_dec"

        self._ascii_parser = AsciiParser()
        self._binary_parser = BinaryParser()

        # Command queue: list of (bytes_to_send, human_name)
        self._cmd_queue: list[tuple[bytes, str]] = []

        # During 'ready': buffer incoming text until we see ack/err
        self._resp_buf = ""

        # Pending response – set when a command is in-flight
        self._pending_cmd_name = ""

    # ── Public API (called from GUI thread) ───────────────────────────────────

    @staticmethod
    def list_ports() -> list[str]:
        ports = serial.tools.list_ports.comports()
        return [p.device for p in sorted(ports, key=lambda p: p.device)]

    def connect_device(self, port: str) -> None:
        try:
            ser = _open_port(port, self.BAUD_RATE)
        except Exception as exc:
            self.conn_changed.emit(False, str(exc))
            return

        with QMutexLocker(self._lock):
            self._serial = ser
            self._keep_running = True
            self._state = "ready"
            self._resp_buf = ""
            self._cmd_queue.clear()

        self.conn_changed.emit(True, f"Connected to {port} @ {self.BAUD_RATE} baud")
        if not self.isRunning():
            self.start()

    def disconnect_device(self) -> None:
        with QMutexLocker(self._lock):
            self._keep_running = False
        self.wait(3000)

    def send_command(self, cmd_bytes: bytes, cmd_name: str = "") -> None:
        with QMutexLocker(self._lock):
            self._cmd_queue.append((cmd_bytes, cmd_name))

    def set_data_format(self, fmt: str) -> None:
        with QMutexLocker(self._lock):
            self._data_format = fmt

    # ── Thread main loop ──────────────────────────────────────────────────────

    def run(self) -> None:
        while True:
            with QMutexLocker(self._lock):
                if not self._keep_running:
                    break
                ser = self._serial
                state = self._state
                fmt = self._data_format

            if ser is None:
                self.msleep(10)
                continue

            # ── Send queued commands ──────────────────────────────────────
            if state in ("ready", "acquiring"):
                with QMutexLocker(self._lock):
                    if self._cmd_queue:
                        cmd_bytes, cmd_name = self._cmd_queue.pop(0)
                    else:
                        cmd_bytes, cmd_name = b"", ""

                if cmd_bytes:
                    try:
                        ser.write(cmd_bytes)
                        ser.flush()
                        display = cmd_bytes.decode("ascii", errors="replace").strip()
                        self.log_message.emit(f">> {display}")
                        with QMutexLocker(self._lock):
                            self._pending_cmd_name = cmd_name
                    except serial.SerialException as exc:
                        self.log_message.emit(f"[Send error] {exc}")

            # ── Read available data ───────────────────────────────────────
            try:
                waiting = ser.in_waiting
                if waiting == 0:
                    self.msleep(1)
                    continue
                raw = ser.read(min(waiting, 65536))
            except serial.SerialException as exc:
                self.log_message.emit(f"[Read error] {exc}")
                break

            if not raw:
                self.msleep(1)
                continue

            with QMutexLocker(self._lock):
                state = self._state
                fmt = self._data_format

            if state == "ready":
                self._handle_command_response(raw)
            elif state == "acquiring":
                self._handle_acquisition_data(raw, fmt)

        # Cleanup
        with QMutexLocker(self._lock):
            ser = self._serial
            self._serial = None
            self._state = "idle"
        if ser and ser.is_open:
            try:
                ser.close()
            except Exception:
                pass
        self.conn_changed.emit(False, "Disconnected")

    # ── Internal helpers ──────────────────────────────────────────────────────

    # Device prepends "PowerShield > " to every response line.
    _PROMPT = "PowerShield > "

    def _handle_command_response(self, raw: bytes) -> None:
        """Parse incoming bytes as ASCII command responses."""
        text = raw.decode("ascii", errors="replace")
        self._resp_buf += text

        while "\n" in self._resp_buf:
            line, self._resp_buf = self._resp_buf.split("\n", 1)
            line = line.rstrip("\r")
            if not line:
                continue
            self.log_message.emit(f"<< {line}")

            # Strip the interactive shell prompt before parsing
            cmd_line = line[len(self._PROMPT):] if line.startswith(self._PROMPT) else line

            if cmd_line.startswith("ack "):
                parts = cmd_line[4:].strip().split(None, 1)
                cmd = parts[0] if parts else ""
                payload = parts[1] if len(parts) > 1 else ""
                self.cmd_result.emit(True, cmd, payload)

                # 'ack start' triggers transition to acquisition mode
                if cmd == "start":
                    with QMutexLocker(self._lock):
                        fmt = self._data_format
                        self._state = "acquiring"
                        self._ascii_parser.reset()
                        self._binary_parser.reset()
                    self.acq_changed.emit(True)
                    self.log_message.emit("[Acquisition started]")
                    # If there's leftover in resp_buf treat it as data
                    if self._resp_buf:
                        leftover = self._resp_buf.encode("ascii", errors="replace")
                        self._resp_buf = ""
                        self._handle_acquisition_data(leftover, fmt)
                    return

            elif cmd_line.startswith("err "):
                # Manual documents 'err' prefix; handle for completeness
                payload = cmd_line[4:].strip()
                self.cmd_result.emit(False, "", payload)

            elif cmd_line.startswith("error "):
                # Firmware actually uses 'error <cmd> [<args>]' for failures
                parts = cmd_line[6:].strip().split(None, 1)
                cmd = parts[0] if parts else ""
                payload = parts[1] if len(parts) > 1 else ""
                self.cmd_result.emit(False, cmd, payload)

    def _handle_acquisition_data(self, raw: bytes, fmt: str) -> None:
        """Route raw bytes through the appropriate measurement parser."""
        if fmt == "ascii_dec":
            text = raw.decode("ascii", errors="replace")
            result: ParsedData = self._ascii_parser.feed(text)
        else:
            result = self._binary_parser.feed(raw)

        # Log any embedded ack/err or error messages
        for line in result.raw_lines:
            if line.startswith("ack ") or line.startswith("err "):
                self.log_message.emit(f"<< {line}")
        for err in result.errors:
            self.log_message.emit(f"[Stream error] {err}")

        # Emit parsed data to UI
        if (result.samples or result.timestamps or
                result.errors or result.end_of_acquisition or result.overcurrent):
            self.data_ready.emit(result)

        # Handle embedded command acks (e.g. 'ack stop' in ASCII stream)
        for success, cmd, payload in result.ack_lines:
            self.cmd_result.emit(success, cmd, payload)

        # Check for acquisition end
        if result.end_of_acquisition:
            with QMutexLocker(self._lock):
                self._state = "ready"
                self._resp_buf = ""
            self.acq_changed.emit(False)
            self.log_message.emit("[Acquisition ended]")

        if result.overcurrent:
            self.log_message.emit("[WARNING] Overcurrent detected!")
