"""Dark theme stylesheet for the X-NUCLEO-LPM01A GUI."""

DARK_THEME = """
/* ── Base ──────────────────────────────────────────────────────────────── */
QMainWindow, QDialog, QWidget {
    background-color: #12121e;
    color: #dde1ec;
    font-family: "Segoe UI", "Inter", "Helvetica Neue", sans-serif;
    font-size: 13px;
}

/* ── Group boxes ────────────────────────────────────────────────────────── */
QGroupBox {
    background-color: #1a1a2e;
    border: 1px solid #2a3a5c;
    border-radius: 7px;
    margin-top: 14px;
    padding: 10px 8px 8px 8px;
    font-weight: 600;
    font-size: 12px;
    color: #5bc8d0;
    letter-spacing: 0.5px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 5px;
    background-color: #12121e;
}

/* ── Buttons ────────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #1e2d50;
    color: #dde1ec;
    border: 1px solid #2a4070;
    border-radius: 5px;
    padding: 6px 14px;
    font-weight: 500;
    min-height: 26px;
}
QPushButton:hover {
    background-color: #253860;
    border-color: #00c8d0;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #162240;
}
QPushButton:disabled {
    background-color: #1a1a28;
    color: #555870;
    border-color: #252535;
}

QPushButton#start_btn {
    background-color: #1a4d3a;
    border-color: #00c896;
    color: #ccffe8;
    font-weight: 700;
    font-size: 14px;
    min-height: 34px;
    border-radius: 6px;
}
QPushButton#start_btn:hover { background-color: #22603f; }
QPushButton#start_btn:pressed { background-color: #133a2a; }
QPushButton#start_btn:disabled { background-color: #1a2520; color: #405545; border-color: #253030; }

QPushButton#stop_btn {
    background-color: #4d1a1a;
    border-color: #e05050;
    color: #ffd0d0;
    font-weight: 700;
    font-size: 14px;
    min-height: 34px;
    border-radius: 6px;
}
QPushButton#stop_btn:hover { background-color: #602222; }
QPushButton#stop_btn:pressed { background-color: #3a1010; }
QPushButton#stop_btn:disabled { background-color: #221a1a; color: #554040; border-color: #302525; }

QPushButton#connect_btn {
    background-color: #1a3550;
    border-color: #3080c8;
    color: #c8deff;
    font-weight: 600;
}
QPushButton#connect_btn:hover { background-color: #1e4060; border-color: #60a8e8; }

QPushButton#disconnect_btn {
    background-color: #3a2a10;
    border-color: #c89030;
    color: #ffe0a0;
    font-weight: 600;
}
QPushButton#disconnect_btn:hover { background-color: #4a3318; }

/* ── ComboBox ───────────────────────────────────────────────────────────── */
QComboBox {
    background-color: #16203a;
    color: #dde1ec;
    border: 1px solid #2a3a5c;
    border-radius: 5px;
    padding: 4px 8px;
    min-width: 90px;
    min-height: 24px;
    selection-background-color: #1e3a6e;
}
QComboBox:hover { border-color: #00c8d0; }
QComboBox:focus { border-color: #00a8b8; }
QComboBox::drop-down {
    border: none;
    width: 22px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #8090b0;
    margin-right: 4px;
}
QComboBox QAbstractItemView {
    background-color: #16203a;
    color: #dde1ec;
    border: 1px solid #2a3a5c;
    selection-background-color: #1e3a6e;
    outline: none;
}

/* ── SpinBox ────────────────────────────────────────────────────────────── */
QSpinBox, QDoubleSpinBox {
    background-color: #16203a;
    color: #dde1ec;
    border: 1px solid #2a3a5c;
    border-radius: 5px;
    padding: 4px 6px;
    min-height: 24px;
}
QSpinBox:hover, QDoubleSpinBox:hover { border-color: #00c8d0; }
QSpinBox:focus, QDoubleSpinBox:focus { border-color: #00a8b8; }
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #1e3060;
    border: none;
    width: 18px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #2a4080;
}

/* ── LineEdit ───────────────────────────────────────────────────────────── */
QLineEdit {
    background-color: #16203a;
    color: #dde1ec;
    border: 1px solid #2a3a5c;
    border-radius: 5px;
    padding: 4px 8px;
    min-height: 24px;
}
QLineEdit:hover { border-color: #00c8d0; }
QLineEdit:focus { border-color: #00a8b8; }

/* ── Labels ─────────────────────────────────────────────────────────────── */
QLabel {
    color: #9098b8;
    background: transparent;
}
QLabel#section_label {
    color: #dde1ec;
    font-weight: 600;
}
QLabel#value_display {
    color: #00d8b0;
    font-weight: 700;
    font-size: 28px;
    font-family: "Consolas", "JetBrains Mono", monospace;
}
QLabel#unit_label {
    color: #7090a0;
    font-size: 14px;
}
QLabel#stat_value {
    color: #00c8d0;
    font-weight: 600;
    font-family: "Consolas", monospace;
}
QLabel#status_ok  { color: #00c896; font-weight: 700; }
QLabel#status_err { color: #e05050; font-weight: 700; }
QLabel#status_warn{ color: #e0a020; font-weight: 700; }

/* ── TextEdit / console ─────────────────────────────────────────────────── */
QTextEdit {
    background-color: #0d1018;
    color: #9db8c0;
    border: 1px solid #1e2a40;
    border-radius: 5px;
    font-family: "Consolas", "JetBrains Mono", "Fira Code", monospace;
    font-size: 12px;
}

/* ── Scrollbars ─────────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #0d1018;
    width: 9px;
    border-radius: 4px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #2a3a5c;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #00a8b8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: #0d1018;
    height: 9px;
    border-radius: 4px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #2a3a5c;
    border-radius: 4px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background: #00a8b8; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Splitter ───────────────────────────────────────────────────────────── */
QSplitter::handle {
    background-color: #1e2d50;
}
QSplitter::handle:horizontal { width: 3px; }
QSplitter::handle:vertical   { height: 3px; }
QSplitter::handle:hover { background-color: #00c8d0; }

/* ── TabWidget ──────────────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #2a3a5c;
    border-radius: 5px;
    background-color: #1a1a2e;
}
QTabBar::tab {
    background-color: #12121e;
    color: #708090;
    border: 1px solid #2a3a5c;
    border-bottom: none;
    padding: 6px 16px;
    border-radius: 5px 5px 0 0;
    font-size: 12px;
}
QTabBar::tab:selected {
    background-color: #1a1a2e;
    color: #dde1ec;
    border-color: #2a3a5c;
}
QTabBar::tab:hover:!selected { background-color: #161630; color: #b0c0d0; }

/* ── CheckBox ───────────────────────────────────────────────────────────── */
QCheckBox {
    color: #9098b8;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #2a3a5c;
    border-radius: 3px;
    background-color: #16203a;
}
QCheckBox::indicator:checked {
    background-color: #00a8b8;
    border-color: #00c8d0;
}
QCheckBox::indicator:hover { border-color: #00c8d0; }

/* ── Status bar ─────────────────────────────────────────────────────────── */
QStatusBar {
    background-color: #0d1018;
    color: #6070a0;
    border-top: 1px solid #1e2a40;
    font-size: 12px;
}

/* ── Tooltip ────────────────────────────────────────────────────────────── */
QToolTip {
    background-color: #1a2a4a;
    color: #dde1ec;
    border: 1px solid #00a8b8;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}

/* ── Frame separators ───────────────────────────────────────────────────── */
QFrame[frameShape="4"],  /* HLine */
QFrame[frameShape="5"] { /* VLine */
    color: #2a3a5c;
}
"""
