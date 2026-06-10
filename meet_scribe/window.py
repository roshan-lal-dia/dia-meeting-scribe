"""
meetingScribe — Main Window
"""

import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QComboBox,
    QFilemeetlog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .device import DeviceInfo, detect_device
from .worker import TranscriptionWorker

TRANSCRIPTS_DIR = Path.home() / "meetingTranscripts"
MODEL_SIZES = ["tiny.en", "base.en", "small.en", "medium.en", "large-v3"]
SOURCE_MODES = {
    "Both (system + mic)": "both",
    "System audio only":   "system",
    "Mic only":            "mic",
}


class MainWindow(QMainWindow):
    # Emitted so the tray icon can react to recording state
    recording_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.device: DeviceInfo = detect_device()
        self.worker: TranscriptionWorker | None = None
        self.lines: list[str] = []
        self._setup_ui()

    # ── UI construction ─────────────────────────────────────────────────────

    def _setup_ui(self):
        self.setWindowTitle("meetingScribe")
        self.setMinimumSize(720, 520)
        self.resize(860, 640)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 14, 16, 10)

        # ── Row 1: device badge + model + source ──
        row1 = QHBoxLayout()

        gpu_label = "⚡ GPU" if self.device.is_gpu else "🖥  CPU"
        badge = QLabel(f"{gpu_label}  ·  {self.device.name}")
        badge.setObjectName("deviceBadge")
        row1.addWidget(badge)
        row1.addStretch()

        row1.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(MODEL_SIZES)
        self.model_combo.setCurrentText(self.device.default_model)
        row1.addWidget(self.model_combo)

        row1.addWidget(QLabel("Capture:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(list(SOURCE_MODES.keys()))
        row1.addWidget(self.source_combo)

        layout.addLayout(row1)

        # ── Separator ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separator")
        layout.addWidget(sep)

        # ── Record button ──
        self.rec_btn = QPushButton("▶   Start Recording")
        self.rec_btn.setObjectName("recBtn")
        self.rec_btn.setFixedHeight(46)
        self.rec_btn.clicked.connect(self._toggle)
        layout.addWidget(self.rec_btn)

        # ── Transcript ──
        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setAcceptRichText(True)
        self.transcript.setObjectName("transcript")
        self.transcript.setPlaceholderText(
            "Transcript will appear here once you start recording…"
        )
        layout.addWidget(self.transcript, stretch=1)

        # ── Bottom row ──
        row2 = QHBoxLayout()
        self.save_btn = QPushButton("💾  Save Transcript")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save)
        row2.addWidget(self.save_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear)
        row2.addWidget(self.clear_btn)

        row2.addStretch()

        self.line_count = QLabel("0 lines")
        self.line_count.setObjectName("lineCount")
        row2.addWidget(self.line_count)

        layout.addLayout(row2)

        # ── Status bar ──
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._set_status("Ready")

    # ── Recording control ────────────────────────────────────────────────────

    @Slot()
    def _toggle(self):
        if self.worker and self.worker.isRunning():
            self._stop()
        else:
            self._start()

    def _start(self):
        mode = SOURCE_MODES[self.source_combo.currentText()]
        model = self.model_combo.currentText()

        self.worker = TranscriptionWorker(model, self.device, mode)
        self.worker.line_ready.connect(self._on_line)
        self.worker.status_changed.connect(self._on_status)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

        self.rec_btn.setText("⏹   Stop Recording")
        self.rec_btn.setProperty("active", True)
        self.rec_btn.setStyle(self.rec_btn.style())
        self.model_combo.setEnabled(False)
        self.source_combo.setEnabled(False)
        self.recording_changed.emit(True)

    def _stop(self):
        """Signal the worker to stop — non-blocking. UI updates in _on_worker_finished."""
        if self.worker:
            self.worker.stop()
            # Force-kill after 4 s if the thread is still stuck
            QTimer.singleShot(4000, self._force_stop)
        self.rec_btn.setText("⏳   Stopping…")
        self.rec_btn.setEnabled(False)
        self.recording_changed.emit(False)

    def _force_stop(self):
        """Called 4 s after stop() — terminates the thread if it's still running."""
        if self.worker and self.worker.isRunning():
            print("[window] force-terminating stuck worker")
            self.worker.terminate()
            self.worker.wait(1000)
            self._on_worker_finished()

    @Slot()
    def _on_worker_finished(self):
        """Called by worker.finished signal — safe to update UI here."""
        self.rec_btn.setText("▶   Start Recording")
        self.rec_btn.setProperty("active", False)
        self.rec_btn.setStyle(self.rec_btn.style())
        self.rec_btn.setEnabled(True)
        self.model_combo.setEnabled(True)
        self.source_combo.setEnabled(True)

        if self.lines:
            self.save_btn.setEnabled(True)
            self._auto_save()

    # ── Slots ────────────────────────────────────────────────────────────────

    @Slot(str, str, str)
    def _on_line(self, ts: str, source: str, text: str):
        if source == "info":
            icon, color = "ℹ️", "#94a3b8"
        elif source == "them":
            icon, color = "🎧", "#7dd3fc"
        else:
            icon, color = "🎤", "#86efac"

        plain = f"[{ts}] {icon}  {text}"
        if source != "info":
            self.lines.append(plain)
        self.save_btn.setEnabled(bool(self.lines))
        self.line_count.setText(f"{len(self.lines)} lines")

        # insertHtml is more reliable than append() for HTML fragments
        html = (
            f'<p style="margin:1px 0; font-family: Consolas, monospace; font-size: 12pt;">'
            f'<span style="color:#6b7280;">[{ts}]</span>&nbsp;'
            f'{icon}&nbsp;'
            f'<span style="color:{color};">{text}</span>'
            f'</p>'
        )
        cur = self.transcript.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        self.transcript.setTextCursor(cur)
        self.transcript.insertHtml(html)
        self.transcript.ensureCursorVisible()

    @Slot(str)
    def _on_status(self, msg: str):
        self._set_status(msg)

    @Slot(str)
    def _on_error(self, msg: str):
        self._set_status(f"⚠  {msg}")

    # ── Transcript persistence ───────────────────────────────────────────────

    def _auto_save(self):
        TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        now = datetime.datetime.now()
        path = TRANSCRIPTS_DIR / f"meeting_{now.strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        self._write(path)
        self._set_status(f"Auto-saved → {path}")

    @Slot()
    def _save(self):
        default = str(
            TRANSCRIPTS_DIR / f"meeting_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')}.txt"
        )
        path, _ = QFilemeetlog.getSaveFileName(
            self, "Save Transcript", default, "Text files (*.txt)"
        )
        if path:
            self._write(Path(path))
            self._set_status(f"Saved → {path}")

    def _write(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.datetime.now()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("meeting Transcript\n")
            fh.write(f"Date  : {now.strftime('%A, %B %d %Y — %H:%M')}\n")
            fh.write(f"Model : {self.model_combo.currentText()}  |  Device: {self.device.name}\n")
            fh.write("=" * 62 + "\n\n")
            fh.write("\n".join(self.lines))
            fh.write("\n")

    @Slot()
    def _clear(self):
        self.transcript.clear()
        self.lines.clear()
        self.line_count.setText("0 lines")
        self.save_btn.setEnabled(False)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _set_status(self, msg: str):
        self.status_bar.showMessage(msg)

    def closeEvent(self, event):
        """Hide to tray instead of quitting."""
        event.ignore()
        self.hide()
        # Signal the tray to show a balloon (first time only)
        self._tray_notify_fn()

    def set_tray_notify(self, fn):
        """Register a callable the window uses to trigger a tray balloon."""
        self._tray_notify_fn = fn

    def _tray_notify_fn(self):
        pass  # replaced by set_tray_notify()
