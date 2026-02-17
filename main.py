#!/usr/bin/env python3
"""
X-NUCLEO-LPM01A Power Monitor GUI
===================================
Entry point for the application.

Requirements
------------
    pip install pyserial PyQt5 pyqtgraph numpy

Usage
-----
    python main.py
"""

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.styles import DARK_THEME


def main() -> int:
    # High-DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("X-NUCLEO-LPM01A Power Monitor")
    app.setOrganizationName("PowerShield")
    app.setApplicationVersion("1.0.0")

    # Apply dark theme
    app.setStyleSheet(DARK_THEME)

    # Base font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
