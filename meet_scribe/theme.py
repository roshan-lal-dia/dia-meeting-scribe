"""Windows 11 Mica dark theme for Meet-Scribe — v2 refined."""

STYLESHEET = """
/* ── Global reset ────────────────────────────────────────────────────────── */
* {
    font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
    font-size: 9.5pt;
    color: #e2e2e2;
    outline: none;
    border: none;
    margin: 0; padding: 0;
}
QWidget {
    background: transparent;
}
QMainWindow {
    background: transparent;
}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
#sidebar {
    background-color: rgba(18, 18, 18, 0.92);
    border-right: 1px solid rgba(255, 255, 255, 0.05);
    min-width: 296px;
    max-width: 296px;
}

/* ── Main content ────────────────────────────────────────────────────────── */
#mainContent {
    background-color: rgba(12, 12, 12, 0.80);
}

/* ── App title ────────────────────────────────────────────────────────────── */
QLabel#appTitle {
    font-size: 15pt;
    font-weight: 700;
    color: #f5f5f5;
    letter-spacing: -0.3px;
}

/* ── Device subtitle ────────────────────────────────────────────────────── */
QLabel#deviceSubtitle {
    font-size: 8pt;
    color: #4a4a4a;
    letter-spacing: 0.1px;
}

/* ── Section labels ──────────────────────────────────────────────────────── */
QLabel#sectionLabel {
    font-size: 7.5pt;
    font-weight: 700;
    color: #6a6a6a;
    letter-spacing: 0.8px;
}

/* ── Generic labels ──────────────────────────────────────────────────────── */
QLabel {
    background: transparent;
    color: #a8a8a8;
}

/* ── Stat labels (perf) ─────────────────────────────────────────────────── */
QLabel#stat {
    font-size: 7.5pt;
    color: #4a4a4a;
    font-family: "Cascadia Code", "Consolas", monospace;
    letter-spacing: 0.2px;
}
QLabel#lineCountLabel {
    font-size: 8.5pt;
    color: #505050;
}

/* ── Transcript header ────────────────────────────────────────────────────── */
QLabel#transcriptTitle {
    font-size: 13pt;
    font-weight: 600;
    color: #d0d0d0;
}

/* ── Record button ───────────────────────────────────────────────────────── */
QPushButton#recBtn {
    background-color: #0067c0;
    color: #ffffff;
    border: none;
    border-radius: 7px;
    font-size: 10pt;
    font-weight: 600;
    letter-spacing: 0.2px;
    min-height: 42px;
    padding: 0 16px;
}
QPushButton#recBtn:hover {
    background-color: #1275cc;
}
QPushButton#recBtn:pressed {
    background-color: #0058aa;
}
QPushButton#recBtn[active="true"] {
    background-color: #c0392b;
}
QPushButton#recBtn[active="true"]:hover {
    background-color: #d04030;
}
QPushButton#recBtn:disabled {
    background-color: rgba(255, 255, 255, 0.07);
    color: rgba(255, 255, 255, 0.22);
}

/* ── Pause button ────────────────────────────────────────────────────────── */
QPushButton#pauseBtn {
    background-color: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    color: #b0b0b0;
    font-size: 9pt;
    font-weight: 500;
    min-height: 32px;
}
QPushButton#pauseBtn:hover {
    background-color: rgba(255, 255, 255, 0.10);
    border-color: rgba(255, 255, 255, 0.14);
}
QPushButton#pauseBtn:disabled {
    color: #2e2e2e;
    border-color: rgba(255, 255, 255, 0.03);
}
QPushButton#pauseBtn[active="true"] {
    background-color: rgba(180, 130, 0, 0.20);
    border-color: rgba(255, 185, 0, 0.22);
    color: #f0c040;
}

/* ── Regular buttons ─────────────────────────────────────────────────────── */
QPushButton {
    background-color: rgba(255, 255, 255, 0.06);
    color: #c8c8c8;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 9pt;
    font-weight: 500;
    min-height: 30px;
}
QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.11);
    border-color: rgba(255, 255, 255, 0.14);
}
QPushButton:pressed {
    background-color: rgba(255, 255, 255, 0.03);
}
QPushButton:disabled {
    color: rgba(255, 255, 255, 0.18);
    border-color: rgba(255, 255, 255, 0.04);
}

/* ── Action buttons (Save / Summarize) ───────────────────────────────────── */
QPushButton#actionBtn {
    background-color: rgba(0, 103, 192, 0.18);
    border: 1px solid rgba(0, 103, 192, 0.30);
    color: #80b8e8;
    font-weight: 600;
    min-height: 32px;
}
QPushButton#actionBtn:hover {
    background-color: rgba(0, 103, 192, 0.28);
    border-color: rgba(0, 103, 192, 0.45);
    color: #a0ccf0;
}
QPushButton#actionBtn:disabled {
    background-color: rgba(255, 255, 255, 0.04);
    border-color: rgba(255, 255, 255, 0.05);
    color: rgba(255, 255, 255, 0.18);
}

/* ── Combo box ───────────────────────────────────────────────────────────── */
QComboBox {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 5px 10px;
    color: #d0d0d0;
    font-size: 9pt;
    min-height: 30px;
    selection-background-color: #0067c0;
}
QComboBox:hover {
    border-color: rgba(255, 255, 255, 0.16);
    background-color: rgba(255, 255, 255, 0.08);
}
QComboBox:focus {
    border-color: rgba(0, 103, 192, 0.60);
    border-width: 1px;
}
QComboBox::drop-down {
    border: none;
    width: 22px;
}
QComboBox QAbstractItemView {
    background-color: #1c1c1e;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 7px;
    selection-background-color: #0067c0;
    color: #d0d0d0;
    padding: 3px;
    font-size: 9pt;
}
QComboBox QAbstractItemView::item {
    min-height: 26px;
    padding: 2px 6px;
    border-radius: 4px;
}

/* ── Checkboxes ──────────────────────────────────────────────────────────── */
QCheckBox {
    color: #b8b8b8;
    spacing: 8px;
    font-size: 9pt;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.04);
}
QCheckBox::indicator:checked {
    background-color: #0067c0;
    border-color: #0067c0;
    image: none;
}
QCheckBox::indicator:hover {
    border-color: rgba(255, 255, 255, 0.28);
}

/* ── Line edit ───────────────────────────────────────────────────────────── */
QLineEdit {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 6px;
    padding: 5px 9px;
    color: #a0a0a0;
    font-size: 9pt;
    min-height: 28px;
}
QLineEdit:focus {
    border-color: rgba(0, 103, 192, 0.55);
    background: rgba(255, 255, 255, 0.06);
    color: #c8c8c8;
}

/* ── Transcript ──────────────────────────────────────────────────────────── */
QTextEdit#transcript {
    background: transparent;
    color: #c8c8c8;
    border: none;
    font-family: "Cascadia Code", "Cascadia Mono", "Consolas", monospace;
    font-size: 9.5pt;
    line-height: 1.5;
    padding: 0;
    selection-background-color: rgba(0, 103, 192, 0.50);
}

/* ── Scrollbars ──────────────────────────────────────────────────────────── */
QScrollArea#sidebarScroll {
    background: transparent;
    border: none;
}
QWidget#sidebarInner {
    background: transparent;
}
/* Sidebar thin scrollbar */
QScrollArea#sidebarScroll QScrollBar:vertical {
    background: transparent;
    width: 3px;
    margin: 0;
}
QScrollArea#sidebarScroll QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.12);
    border-radius: 1px;
    min-height: 24px;
}
QScrollArea#sidebarScroll QScrollBar::add-line:vertical,
QScrollArea#sidebarScroll QScrollBar::sub-line:vertical { height: 0; }
/* Main scrollbar */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.12);
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 0.22);
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
    background: rgba(255, 255, 255, 0.12);
    border-radius: 3px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background: rgba(255, 255, 255, 0.22);
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal { width: 0; }

/* ── Separators ──────────────────────────────────────────────────────────── */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {
    background: rgba(255, 255, 255, 0.06);
    max-height: 1px;
    color: transparent;
    border: none;
}

/* ── Status bar ──────────────────────────────────────────────────────────── */
QStatusBar {
    background: rgba(0, 0, 0, 0.40);
    color: #484848;
    font-size: 8pt;
    font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
    border-top: 1px solid rgba(255, 255, 255, 0.04);
    padding-left: 6px;
}
QStatusBar::item { border: none; }

/* ── Tooltip ─────────────────────────────────────────────────────────────── */
QToolTip {
    background-color: #1e1e20;
    color: #dcdcdc;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 5px;
    padding: 5px 9px;
    font-size: 8.5pt;
}

/* ── Menus ───────────────────────────────────────────────────────────────── */
QMenu {
    background-color: rgba(20, 20, 22, 0.96);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 9px;
    padding: 4px;
    color: #e0e0e0;
    font-size: 9.5pt;
}
QMenu::item { padding: 7px 22px; border-radius: 5px; }
QMenu::item:selected { background-color: #0067c0; }
QMenu::item:disabled { color: rgba(255, 255, 255, 0.22); }
QMenu::separator {
    height: 1px;
    background: rgba(255, 255, 255, 0.07);
    margin: 4px 8px;
}

/* ── Wizard (onboarding) ─────────────────────────────────────────────────── */
QWizard {
    background-color: #141416;
    color: #e2e2e2;
}
QWizardPage {
    background-color: #141416;
}
QWizard QLabel {
    font-size: 9.5pt;
    color: #c0c0c0;
    line-height: 1.5;
}
QWizard QLabel#qt_wizard_title {
    font-size: 14pt;
    font-weight: 700;
    color: #f0f0f0;
}
QWizard QLabel#qt_wizard_subTitle {
    font-size: 9pt;
    color: #7a7a7a;
}
QWizard QComboBox {
    background-color: #252528;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    padding: 5px 10px;
    color: #d0d0d0;
    font-size: 9.5pt;
    min-height: 32px;
}
QWizard QPushButton {
    background-color: #252528;
    color: #d0d0d0;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    padding: 6px 18px;
    font-size: 9.5pt;
    font-weight: 500;
    min-height: 32px;
    min-width: 80px;
}
QWizard QPushButton:hover {
    background-color: #30303a;
    border-color: rgba(255, 255, 255, 0.20);
}
QWizard QPushButton[text="Start Meet-Scribe"] {
    background-color: #0067c0;
    border: none;
    color: #ffffff;
    font-weight: 600;
}
QWizard QPushButton[text="Start Meet-Scribe"]:hover {
    background-color: #1275cc;
}
QCheckBox {
    font-size: 9pt;
    color: #b8b8b8;
}
"""


def apply(app) -> None:
    """Apply the Mica-aware dark theme to the QApplication."""
    app.setStyleSheet(STYLESHEET)
