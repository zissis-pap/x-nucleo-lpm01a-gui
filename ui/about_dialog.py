"""About dialog – version, packages, author, licence."""

from __future__ import annotations

import importlib.metadata

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel,
    QTabWidget, QTextBrowser, QVBoxLayout, QWidget,
)

from version import __version__


def _pkg_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


class AboutDialog(QDialog):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About X-NUCLEO-LPM01A Power Monitor")
        self.setMinimumWidth(520)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._build_about_tab(), "About")
        tabs.addTab(self._build_licence_tab(), "Licence")
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)

    def _build_about_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        packages = [
            ("PyQt5",      _pkg_version("PyQt5")),
            ("pyqtgraph",  _pkg_version("pyqtgraph")),
            ("numpy",      _pkg_version("numpy")),
            ("pyserial",   _pkg_version("pyserial")),
        ]
        pkg_rows = "\n".join(f"  • {name}  {ver}" for name, ver in packages)

        text = QLabel(
            f"<h2>X-NUCLEO-LPM01A Power Monitor</h2>"
            f"<p><b>Version:</b> {__version__}</p>"
            f"<p><b>Author:</b> Zissis Papadopoulos</p>"
            f"<p><b>Licence:</b> GNU General Public License v3</p>"
            f"<hr>"
            f"<p><b>Dependencies:</b></p>"
            f"<pre>{pkg_rows}</pre>"
        )
        text.setTextFormat(Qt.RichText)
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignTop)
        layout.addWidget(text)
        layout.addStretch()
        return widget

    def _build_licence_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)

        try:
            with open("LICENSE", "r", encoding="utf-8") as fh:
                browser.setPlainText(fh.read())
        except OSError:
            browser.setPlainText(
                "GNU General Public License v3\n\n"
                "See https://www.gnu.org/licenses/gpl-3.0.html"
            )

        layout.addWidget(browser)
        return widget
