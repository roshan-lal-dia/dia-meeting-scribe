"""Dark theme stylesheet for meetingScribe."""

STYLESHEET = """
/* ── Base ── */
QMainWindow, QWidget {
    background-color: #0f172a;
    color: #f1f5f9;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 10pt;
}

/* ── Device badge ── */
#deviceBadge {
    background-color: #1e293b;
    color: #a78bfa;
    padding: 4px 14px;
    border-radius: 999px;
    font-size: 9pt;
    font-weight: 600;
}

/* ── Separator ── */
#separator {
    color: #1e293b;
    background-color: #1e293b;
    max-height: 1px;
}

/* ── Combos ── */
QComboBox {
    background-color: #1e293b;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 4px 10px;
    min-width: 145px;
    font-size: 10pt;
}
QComboBox:hover  { border-color: #4f46e5; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #1e293b;
    color: #e2e8f0;
    selection-background-color: #334155;
    border: 1px solid #334155;
    font-size: 10pt;
}

/* ── Record button (idle) ── */
QPushButton#recBtn {
    background-color: #4f46e5;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    font-size: 12pt;
    font-weight: 700;
}
QPushButton#recBtn:hover   { background-color: #6366f1; }
QPushButton#recBtn:pressed { background-color: #4338ca; }

/* Record button active (recording) */
QPushButton#recBtn[active="true"] {
    background-color: #dc2626;
}
QPushButton#recBtn[active="true"]:hover   { background-color: #ef4444; }
QPushButton#recBtn[active="true"]:pressed { background-color: #b91c1c; }

/* ── Generic buttons ── */
QPushButton {
    background-color: #1e293b;
    color: #cbd5e1;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 5px 16px;
    font-size: 10pt;
}
QPushButton:hover    { background-color: #334155; }
QPushButton:disabled { color: #475569; border-color: #1e293b; }

/* ── Transcript area ── */
QTextEdit#transcript {
    background-color: #020617;
    color: #e2e8f0;
    border: 1px solid #1e293b;
    border-radius: 8px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 10pt;
    padding: 10px;
    selection-background-color: #1e3a5f;
}

/* ── Line count ── */
#lineCount {
    color: #475569;
    font-size: 9pt;
}

/* ── Status bar ── */
QStatusBar {
    background-color: #020617;
    color: #64748b;
    font-size: 9pt;
    padding-left: 4px;
}

/* ── Scroll bars ── */
QScrollBar:vertical {
    background: #0f172a;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #4f46e5; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* ── Tray context menu ── */
QMenu {
    background-color: #1e293b;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 4px;
    font-size: 10pt;
}
QMenu::item          { padding: 6px 18px; border-radius: 4px; }
QMenu::item:selected { background-color: #334155; }
QMenu::separator     { height: 1px; background: #334155; margin: 4px 8px; }
"""
