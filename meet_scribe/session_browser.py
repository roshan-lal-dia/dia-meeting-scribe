"""Session browser dialog - shows past recording sessions and lets the user
view, export, or delete them.
"""
from __future__ import annotations

import datetime
import logging
import pathlib

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .sessions import delete_session, list_sessions, load_session

log = logging.getLogger(__name__)


class SessionBrowserDialog(QDialog):
    """Modal dialog that lists past sessions and allows view / export / delete."""

    open_session = Signal(object)   # SessionData

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Recording History")
        self.setMinimumSize(700, 480)
        self._sessions: list[dict] = []
        self._build_ui()
        self._load()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QLabel("Recording History")
        f = title.font()
        f.setPointSize(13)
        f.setBold(True)
        title.setFont(f)
        root.addWidget(title)

        body = QHBoxLayout()
        root.addLayout(body, stretch=1)

        # Left: session list
        left = QVBoxLayout()
        body.addLayout(left, stretch=1)
        left.addWidget(QLabel("Sessions (newest first):"))
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._on_select)
        left.addWidget(self.list_widget, stretch=1)

        # Right: preview
        right = QVBoxLayout()
        body.addLayout(right, stretch=2)
        right.addWidget(QLabel("Transcript preview:"))
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        right.addWidget(self.preview, stretch=1)

        # Buttons
        btn_row = QHBoxLayout()
        root.addLayout(btn_row)
        self.open_btn   = QPushButton("Open in App")
        self.export_btn = QPushButton("Export…")
        self.delete_btn = QPushButton("Delete")
        self.close_btn  = QPushButton("Close")
        for btn in (self.open_btn, self.export_btn, self.delete_btn):
            btn.setEnabled(False)
        btn_row.addWidget(self.open_btn)
        btn_row.addWidget(self.export_btn)
        btn_row.addWidget(self.delete_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.close_btn)

        self.open_btn.clicked.connect(self._on_open)
        self.export_btn.clicked.connect(self._on_export)
        self.delete_btn.clicked.connect(self._on_delete)
        self.close_btn.clicked.connect(self.accept)

    # ── Data ─────────────────────────────────────────────────────────────────

    def _load(self) -> None:
        self._sessions = list_sessions()
        self.list_widget.clear()
        if not self._sessions:
            self.list_widget.addItem("(no saved sessions)")
            return
        for s in self._sessions:
            try:
                dt  = datetime.datetime.fromisoformat(s["started_at"])
                dur = _duration_str(s.get("started_at", ""), s.get("ended_at", ""))
                n   = len(s.get("lines", []))
                label = f"{dt.strftime('%Y-%m-%d  %H:%M')}   {dur}   {n} lines   {s.get('model','?')}"
            except Exception:
                label = str(s.get("_path", "unknown"))
            self.list_widget.addItem(QListWidgetItem(label))

    @Slot(int)
    def _on_select(self, row: int) -> None:
        has = 0 <= row < len(self._sessions)
        self.open_btn.setEnabled(has)
        self.export_btn.setEnabled(has)
        self.delete_btn.setEnabled(has)
        if not has:
            self.preview.clear()
            return
        s = self._sessions[row]
        lines = s.get("lines", [])
        text  = "\n".join(f"[{ts}] {src}: {txt}" for ts, src, txt in lines[:60])
        if len(lines) > 60:
            text += f"\n… ({len(lines) - 60} more lines)"
        self.preview.setPlainText(text or "(empty transcript)")

    @Slot()
    def _on_open(self) -> None:
        row = self.list_widget.currentRow()
        if not (0 <= row < len(self._sessions)):
            return
        try:
            data = load_session(self._sessions[row]["_path"])
            self.open_session.emit(data)
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, "Load Error", str(exc))

    @Slot()
    def _on_export(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        row = self.list_widget.currentRow()
        if not (0 <= row < len(self._sessions)):
            return
        try:
            data = load_session(self._sessions[row]["_path"])
        except Exception as exc:
            QMessageBox.warning(self, "Load Error", str(exc))
            return
        path, _fmt = QFileDialog.getSaveFileName(
            self, "Export Session", data.started_at.strftime("session_%Y%m%d_%H%M%S"),
            "Text (*.txt);;Markdown (*.md);;SRT (*.srt);;WebVTT (*.vtt)",
        )
        if not path:
            return
        p = pathlib.Path(path)
        try:
            suffix = p.suffix.lower()
            if suffix == ".srt":
                from .export.srt import write_srt
                write_srt(data, p)
            elif suffix == ".vtt":
                from .export.srt import write_vtt
                write_vtt(data, p)
            else:
                from .export.plaintext import PlaintextWriter
                PlaintextWriter().write(data, p)
            QMessageBox.information(self, "Exported", f"Saved to:\n{p}")
        except Exception as exc:
            QMessageBox.warning(self, "Export Error", str(exc))

    @Slot()
    def _on_delete(self) -> None:
        row = self.list_widget.currentRow()
        if not (0 <= row < len(self._sessions)):
            return
        reply = QMessageBox.question(
            self, "Delete Session",
            "Permanently delete this recording session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            delete_session(self._sessions[row]["_path"])
        except Exception as exc:
            QMessageBox.warning(self, "Delete Error", str(exc))
            return
        self._load()
        self.preview.clear()


# ── helpers ───────────────────────────────────────────────────────────────────

def _duration_str(start: str, end: str) -> str:
    try:
        s = datetime.datetime.fromisoformat(start)
        e = datetime.datetime.fromisoformat(end)
        secs = int((e - s).total_seconds())
        m, s2 = divmod(secs, 60)
        h, m  = divmod(m, 60)
        if h:
            return f"{h}h {m}m"
        return f"{m}m {s2}s" if m else f"{s2}s"
    except Exception:
        return "?"
