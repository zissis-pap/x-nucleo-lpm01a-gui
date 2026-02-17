"""
Console widget – scrollable log of all serial I/O plus a raw command input.
"""

from __future__ import annotations

from datetime import datetime

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import (
    QHBoxLayout, QLineEdit, QPushButton,
    QTextEdit, QVBoxLayout, QWidget,
)


class ConsoleWidget(QWidget):
    """Scrollable log with colour-coded messages and a command input line."""

    command_entered = pyqtSignal(str)   # raw text typed by the user

    # Maximum lines kept in the text box (old lines are trimmed automatically)
    MAX_LINES = 2000

    # Colour map keyed on message prefix
    _COLORS = {
        ">>": "#5bc8d0",    # sent command (teal)
        "<<": "#9db8c0",    # received text (muted blue)
        "[": "#e0c030",     # [meta] messages (amber)
        "[W": "#e08030",    # [WARNING] (orange)
        "[E": "#e05050",    # [Error] (red)
        "ack": "#00c896",   # ack (green)
        "err": "#e05050",   # err (red)
    }
    _DEFAULT_COLOR = "#9098b8"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setLineWrapMode(QTextEdit.NoWrap)
        self._log.setMinimumHeight(80)
        root.addWidget(self._log, 1)

        # Input row
        input_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a raw command and press Enter…")
        self._input.returnPressed.connect(self._on_send)
        input_row.addWidget(self._input)

        send_btn = QPushButton("Send")
        send_btn.setFixedWidth(60)
        send_btn.clicked.connect(self._on_send)
        input_row.addWidget(send_btn)

        clear_btn = QPushButton("Clear log")
        clear_btn.setFixedWidth(72)
        clear_btn.clicked.connect(self._log.clear)
        input_row.addWidget(clear_btn)

        root.addLayout(input_row)

    # ── Public API ────────────────────────────────────────────────────────────

    def append(self, text: str) -> None:
        """Append a line to the log with appropriate colour."""
        if not text:
            return

        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        full = f"[{ts}]  {text}"

        # Pick colour
        color = self._DEFAULT_COLOR
        for prefix, col in self._COLORS.items():
            if text.startswith(prefix):
                color = col
                break

        # Append with colour
        cursor = self._log.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.insertText(full + "\n", fmt)

        # Trim old lines
        doc = self._log.document()
        while doc.lineCount() > self.MAX_LINES:
            cursor = doc.find("\n")
            tc = QTextCursor(doc)
            tc.movePosition(QTextCursor.Start)
            tc.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor)
            tc.removeSelectedText()

        self._log.setTextCursor(cursor)
        self._log.ensureCursorVisible()

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_send(self) -> None:
        text = self._input.text().strip()
        if text:
            self.command_entered.emit(text)
            self._input.clear()
