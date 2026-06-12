"""Windows 11 Mica dark theme for Meet-Scribe.

Requires WA_TranslucentBackground on the main window so Mica shows through.
All widget backgrounds use rgba() so the Mica layer is visible beneath them.

Palette:
  sidebar     rgba(20, 20, 20, 0.88)
  main        rgba(13, 13, 13, 0.80)
  surface     rgba(255, 255, 255, 0.06)
  hover       rgba(255, 255, 255, 0.11)
  border      rgba(255, 255, 255, 0.07)
  accent      #0067c0  (Win11 blue, slightly desaturated)
  danger      #b91c1c
  text-hi     #f0f0f0
  text-mid    #b8b8b8
  text-low    #666666
  mono        Cascadia Code > Consolas > monospace
"""

STYLESHEET = """
/* ── Global ──────────────────────────────────────────────── */
* {
    font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
    font-size: 9pt;
    color: #e0e0e0;
    outline: none;
    border: none;
}
QWidget {
    background: transparent;
}
QMainWindow {
    background: transparent;
}

/* ── Sidebar ─────────────────────────────────────────────── */
#sidebar {
    background-color: rgba(20, 20, 20, 0.88);
    border-right: 1px solid rgba(255, 255, 255, 0.06);
    min-width: 264px;
    max-width: 264px;
}

/* ── Main content ────────────────────────────────────────── */
#mainContent {
    background-color: rgba(13, 13, 13, 0.80);
}

/* ── Labels ──────────────────────────────────────────────── */
QLabel {
    background: transparent;
    color: #b0b0b0;
}
QLabel#appTitle {
    font-size: 13pt;
    font-weight: 600;
    color: #f0f0f0;
}
QLabel#deviceSubtitle {
    font-size: 8pt;
    color: #585858;
}
QLabel#sectionLabel {
    font-size: 7.5pt;
    font-weight: 600;
    color: #585858;
    letter-spacing: 0.5px;
}
QLabel#stat {
    font-size: 8pt;
    color: #606060;
    font-family: "Cascadia Code", "Consolas", monospace;
}
QLabel#lineCountLabel {
    font-size: 8pt;
    color: #555555;
}

/* ── Record button ───────────────────────────────────────── */
QPushButton#recBtn {
    background-color: #0067c0;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    font-size: 10pt;
    font-weight: 600;
    padding: 0 16px;
    min-height: 40px;
}
QPushButton#recBtn:hover {
    background-color: #1177d1;
}
QPushButton#recBtn:pressed {
    background-color: #0055a5;
}
QPushButton#recBtn[active="true"] {
    background-color: #b91c1c;
}
QPushButton#recBtn[active="true"]:hover {
    background-color: #c82c2c;
}
QPushButton#recBtn:disabled {
    background-color: rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.25);
}

/* ── Regular buttons ─────────────────────────────────────── */
QPushButton {
    background-color: rgba(255, 255, 255, 0.07);
    color: #d8d8d8;
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 5px;
    padding: 5px 14px;
    font-size: 9pt;
    min-height: 28px;
}
QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.13);
    border-color: rgba(255, 255, 255, 0.15);
}
QPushButton:pressed {
    background-color: rgba(255, 255, 255, 0.04);
}
QPushButton:disabled {
    color: rgba(255, 255, 255, 0.22);
    border-color: rgba(255, 255, 255, 0.05);
}

/* ── Combo box ───────────────────────────────────────────── */
QComboBox {
    background-color: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 5px;
    padding: 4px 8px;
    color: #d8d8d8;
    min-height: 28px;
    selection-background-color: #0067c0;
}
QComboBox:hover {
    border-color: rgba(255, 255, 255, 0.18);
}
QComboBox:focus {
    border-color: #0067c0;
    border-width: 2px;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #1e1e1e;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 6px;
    selection-background-color: #0067c0;
    color: #d8d8d8;
    padding: 2px;
}

/* ── Checkboxes ──────────────────────────────────────────── */
QCheckBox {
    color: #a8a8a8;
    spacing: 6px;
    font-size: 8.5pt;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 3px;
    background: rgba(255, 255, 255, 0.05);
}
QCheckBox::indicator:checked {
    background-color: #0067c0;
    border-color: #0067c0;
}
QCheckBox::indicator:hover {
    border-color: rgba(255, 255, 255, 0.30);
}

/* ── Line edit (vault path) ──────────────────────────────── */
QLineEdit {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 5px;
    padding: 4px 8px;
    color: #909090;
    font-size: 8.5pt;
    min-height: 26px;
}
QLineEdit:focus {
    border-color: #0067c0;
}

/* ── Transcript ──────────────────────────────────────────── */
QTextEdit#transcript {
    background: transparent;
    color: #c0c0c0;
    border: none;
    font-family: "Cascadia Code", "Cascadia Mono", "Consolas", monospace;
    font-size: 9pt;
    padding: 2px 0;
    selection-background-color: #0067c0;
}

/* ── Scrollbars ──────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.14);
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 0.26);
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical { background: none; }
QScrollBar:horizontal {
    background: transparent;
    height: 6px;
}
QScrollBar::handle:horizontal {
    background: rgba(255, 255, 255, 0.14);
    border-radius: 3px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover {
    background: rgba(255, 255, 255, 0.26);
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal { width: 0; }

/* ── Separators ──────────────────────────────────────────── */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {
    background: rgba(255, 255, 255, 0.07);
    max-height: 1px;
    color: transparent;
    border: none;
}

/* ── Status bar ──────────────────────────────────────────── */
QStatusBar {
    background: rgba(0, 0, 0, 0.45);
    color: #525252;
    font-size: 7.5pt;
    border-top: 1px solid rgba(255, 255, 255, 0.04);
    padding-left: 4px;
}
QStatusBar::item { border: none; }

/* ── Tooltip ─────────────────────────────────────────────── */
QToolTip {
    background-color: #1c1c1c;
    color: #e0e0e0;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 8pt;
}

/* ── Context / tray menus ────────────────────────────────── */
QMenu {
    background-color: rgba(22, 22, 22, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 8px;
    padding: 4px;
    color: #e0e0e0;
    font-size: 9pt;
}
QMenu::item           { padding: 6px 24px; border-radius: 4px; }
QMenu::item:selected  { background-color: #0067c0; }
QMenu::item:disabled  { color: rgba(255, 255, 255, 0.25); }
QMenu::separator      {
    height: 1px;
    background: rgba(255, 255, 255, 0.08);
    margin: 4px 8px;
}
"""


def apply(app) -> None:
    """Apply the Mica-aware dark theme to the QApplication."""
    app.setStyleSheet(STYLESHEET)
