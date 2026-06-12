"""Meet-Scribe - Main Window."""
from __future__ import annotations

import contextlib
import datetime
import logging
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .audio.devices import AudioDevice, list_speakers
from .export.base import SessionData
from .export.obsidian import ObsidianWriter
from .settings import AppSettings
from .transcribe.device import DeviceInfo, detect_device
from .transcribe.worker import TranscriptionWorker
from .utils import apply_dark_titlebar, apply_mica

log = logging.getLogger(__name__)

MODEL_SIZES = [
    "tiny.en", "base.en", "small.en", "medium.en",
    "tiny", "base", "small", "medium", "large-v2", "large-v3",
]

LANGUAGES: dict[str, str | None] = {
    "Auto-detect": None,
    "English":     "en",
    "Arabic":      "ar",
    "Tamil":       "ta",
    "Hindi":       "hi",
    "French":      "fr",
    "Spanish":     "es",
    "German":      "de",
    "Portuguese":  "pt",
    "Russian":     "ru",
    "Japanese":    "ja",
    "Korean":      "ko",
    "Chinese":     "zh",
    "Italian":     "it",
    "Dutch":       "nl",
    "Turkish":     "tr",
    "Polish":      "pl",
    "Ukrainian":   "uk",
    "Indonesian":  "id",
    "Malay":       "ms",
    "Vietnamese":  "vi",
}

SOURCE_MODES = {
    "System audio only":   "system",
    "Both (system + mic)": "both",
    "Mic only":            "mic",
}

RTL_LANGS = frozenset({"ar", "fa", "he", "ur"})


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


class MainWindow(QMainWindow):
    recording_changed = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self.device: DeviceInfo = detect_device()
        self.worker: TranscriptionWorker | None = None
        self.lines: list[str] = []
        self._raw_lines: list[tuple[str, str, str]] = []
        self.settings = AppSettings()
        self._last_detected_lang: str = ""
        self._started_at: datetime.datetime | None = None
        self._ended_at:   datetime.datetime | None = None

        # Transparent window so Mica backdrop shows through
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._setup_ui()
        self._restore_settings()
        self._setup_shortcuts()

    # ── UI construction ──────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setWindowTitle("Meet-Scribe")
        self.setMinimumSize(820, 540)
        self.resize(1040, 700)

        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_main(), stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._set_status("Ready  -  Space = record  -  Ctrl+S = save")

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")

        v = QVBoxLayout(sidebar)
        v.setSpacing(0)
        v.setContentsMargins(16, 22, 16, 16)

        # App header
        title = QLabel("Meet-Scribe")
        title.setObjectName("appTitle")
        v.addWidget(title)

        gpu_tag = "GPU" if self.device.is_gpu else "CPU"
        sub = QLabel(f"{self.device.name}  |  {gpu_tag}")
        sub.setObjectName("deviceSubtitle")
        v.addWidget(sub)

        v.addSpacing(18)
        v.addWidget(_sep())
        v.addSpacing(16)

        # Record button
        self.rec_btn = QPushButton("  Start Recording")
        self.rec_btn.setObjectName("recBtn")
        self.rec_btn.setFixedHeight(44)
        self.rec_btn.setToolTip("Start / stop recording  [Space]")
        self.rec_btn.clicked.connect(self._toggle)
        v.addWidget(self.rec_btn)

        v.addSpacing(20)
        v.addWidget(_sep())
        v.addSpacing(16)

        # Settings combos
        def _field(label: str, widget: QWidget) -> None:
            lbl = QLabel(label)
            lbl.setObjectName("sectionLabel")
            v.addWidget(lbl)
            v.addSpacing(4)
            v.addWidget(widget)
            v.addSpacing(12)

        self.model_combo = QComboBox()
        self.model_combo.addItems(MODEL_SIZES)
        self.model_combo.setCurrentText(self.device.default_model)
        self.model_combo.setToolTip(
            "Whisper model.  .en = English-only (faster).  "
            "Multilingual names required for Arabic, Tamil, etc."
        )
        _field("MODEL", self.model_combo)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(list(LANGUAGES.keys()))
        self.lang_combo.setToolTip(
            "Auto-detect: Whisper identifies language per chunk.  "
            "Pin a language for faster, more accurate results."
        )
        self.lang_combo.currentTextChanged.connect(self._on_language_changed)
        _field("LANGUAGE", self.lang_combo)

        self.source_combo = QComboBox()
        self.source_combo.addItems(list(SOURCE_MODES.keys()))
        self.source_combo.setToolTip("Audio source(s) to capture")
        _field("CAPTURE", self.source_combo)

        self.speaker_combo = QComboBox()
        self.speaker_combo.setToolTip(
            "Playback device for WASAPI loopback.  "
            "Bluetooth speakers do not support loopback - pick a wired/built-in device."
        )
        self._populate_speaker_combo()
        _field("SPEAKER", self.speaker_combo)

        v.addWidget(_sep())
        v.addSpacing(16)

        # Obsidian
        obs_lbl = QLabel("OBSIDIAN")
        obs_lbl.setObjectName("sectionLabel")
        v.addWidget(obs_lbl)
        v.addSpacing(8)

        self.obs_toggle = QCheckBox("Save to vault")
        self.obs_toggle.stateChanged.connect(self._on_obs_toggle)
        v.addWidget(self.obs_toggle)
        v.addSpacing(6)

        vault_row = QHBoxLayout()
        vault_row.setSpacing(4)
        self.obs_path_edit = QLineEdit()
        self.obs_path_edit.setPlaceholderText("Vault folder...")
        self.obs_path_edit.setReadOnly(True)
        self.obs_path_edit.setToolTip("Notes go to <vault>/Meetings/YYYY-MM/")
        vault_row.addWidget(self.obs_path_edit)
        self.obs_browse_btn = QPushButton("...")
        self.obs_browse_btn.setFixedWidth(34)
        self.obs_browse_btn.setToolTip("Select Obsidian vault folder")
        self.obs_browse_btn.clicked.connect(self._browse_vault)
        vault_row.addWidget(self.obs_browse_btn)
        v.addLayout(vault_row)
        v.addSpacing(6)

        self.obs_wikilinks_chk = QCheckBox("Auto-wikilinks")
        self.obs_wikilinks_chk.setChecked(True)
        self.obs_wikilinks_chk.setToolTip(
            "Wrap repeated proper nouns in [[double brackets]] automatically"
        )
        v.addWidget(self.obs_wikilinks_chk)

        v.addSpacing(16)
        v.addWidget(_sep())
        v.addSpacing(12)

        # Save / Clear
        action_row = QHBoxLayout()
        action_row.setSpacing(6)
        self.save_btn = QPushButton("Save")
        self.save_btn.setEnabled(False)
        self.save_btn.setToolTip("Save transcript  [Ctrl+S]")
        self.save_btn.clicked.connect(self._save)
        action_row.addWidget(self.save_btn)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setToolTip("Clear transcript from view")
        self.clear_btn.clicked.connect(self._clear)
        action_row.addWidget(self.clear_btn)
        v.addLayout(action_row)

        # Push stats to bottom
        v.addStretch()

        self.rtf_label   = QLabel("RTF -")
        self.lat_label   = QLabel("Latency -")
        self.lang_label  = QLabel("Lang -")
        self.chunk_label = QLabel("Chunks -")
        for lbl in (self.rtf_label, self.lat_label, self.lang_label, self.chunk_label):
            lbl.setObjectName("stat")
            v.addWidget(lbl)

        return sidebar

    def _build_main(self) -> QWidget:
        content = QWidget()
        content.setObjectName("mainContent")

        v = QVBoxLayout(content)
        v.setSpacing(0)
        v.setContentsMargins(20, 18, 16, 10)

        # Header: "Transcript" + line count
        hdr = QHBoxLayout()
        t_lbl = QLabel("Transcript")
        t_lbl.setObjectName("appTitle")
        hdr.addWidget(t_lbl)
        hdr.addStretch()
        self.line_count = QLabel("0 lines")
        self.line_count.setObjectName("lineCountLabel")
        hdr.addWidget(self.line_count)
        v.addLayout(hdr)
        v.addSpacing(10)
        v.addWidget(_sep())
        v.addSpacing(10)

        # Transcript view
        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setAcceptRichText(True)
        self.transcript.setObjectName("transcript")
        self.transcript.setPlaceholderText("Transcript will appear here once you start recording...")
        v.addWidget(self.transcript, stretch=1)

        return content

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence(Qt.Key.Key_Space), self).activated.connect(self._toggle)
        QShortcut(QKeySequence.StandardKey.Save,  self).activated.connect(self._save)

    # ── Speaker device ────────────────────────────────────────────────────────

    def _populate_speaker_combo(self) -> None:
        self._speaker_devices: list[AudioDevice] = list_speakers()
        self.speaker_combo.clear()
        for d in self._speaker_devices:
            prefix = "* " if d.likely_loopback_capable else "! "
            label  = prefix + d.name
            if d.is_default:
                label += " (default)"
            self.speaker_combo.addItem(label, userData=d.id)
        for i, d in enumerate(self._speaker_devices):
            if d.likely_loopback_capable:
                self.speaker_combo.setCurrentIndex(i)
                break

    def _selected_loopback_device_id(self) -> str | None:
        idx = self.speaker_combo.currentIndex()
        if 0 <= idx < len(self._speaker_devices):
            return self._speaker_devices[idx].id
        return None

    # ── Language hint ────────────────────────────────────────────────────────

    @Slot(str)
    def _on_language_changed(self, lang: str) -> None:
        code  = LANGUAGES.get(lang)
        model = self.model_combo.currentText()
        if code and code != "en" and model.endswith(".en"):
            base = model.replace(".en", "")
            self.model_combo.setCurrentText(base)
            self._set_status(f"Switched to '{base}' - multilingual model required for {lang}")

    # ── Obsidian slots ────────────────────────────────────────────────────────

    @Slot()
    def _browse_vault(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Obsidian Vault Folder", str(Path.home()),
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if folder:
            self.obs_path_edit.setText(folder)
            self.settings.obsidian_vault = Path(folder)
            self.obs_toggle.setChecked(True)
            self.settings.obsidian_enabled = True
            self.settings.sync()
            self._set_status(f"Obsidian vault: {folder}")

    @Slot(int)
    def _on_obs_toggle(self, state: int) -> None:
        enabled = bool(state)
        self.settings.obsidian_enabled = enabled
        if enabled and not self.settings.obsidian_vault:
            self._browse_vault()

    # ── Settings ──────────────────────────────────────────────────────────────

    def _restore_settings(self) -> None:
        if (m := self.settings.model) in MODEL_SIZES:
            self.model_combo.setCurrentText(m)
        if (lm := self.settings.language) in LANGUAGES:
            self.lang_combo.setCurrentText(lm)
        if (cm := self.settings.capture_mode) in SOURCE_MODES:
            self.source_combo.setCurrentText(cm)
        if geo := self.settings.geometry:
            self.restoreGeometry(geo)
        self.obs_toggle.setChecked(self.settings.obsidian_enabled)
        self.obs_wikilinks_chk.setChecked(self.settings.obsidian_wikilinks)
        if vault := self.settings.obsidian_vault:
            self.obs_path_edit.setText(str(vault))

    def _persist_settings(self) -> None:
        self.settings.model              = self.model_combo.currentText()
        self.settings.language           = self.lang_combo.currentText()
        self.settings.capture_mode       = self.source_combo.currentText()
        self.settings.geometry           = bytes(self.saveGeometry())
        self.settings.obsidian_enabled   = self.obs_toggle.isChecked()
        self.settings.obsidian_wikilinks = self.obs_wikilinks_chk.isChecked()
        self.settings.sync()

    # ── Window events ─────────────────────────────────────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        hwnd = int(self.winId())
        with contextlib.suppress(Exception):
            apply_dark_titlebar(hwnd)
        with contextlib.suppress(Exception):
            apply_mica(hwnd)

    def closeEvent(self, event) -> None:
        self._persist_settings()
        event.ignore()
        self.hide()
        self._tray_notify_fn()

    # ── Recording control ─────────────────────────────────────────────────────

    @Slot()
    def _toggle(self) -> None:
        if self.worker and self.worker.isRunning():
            self._stop()
        else:
            self._start()

    def _start(self) -> None:
        mode     = SOURCE_MODES[self.source_combo.currentText()]
        model    = self.model_combo.currentText()
        lang_key = self.lang_combo.currentText()
        lang     = LANGUAGES[lang_key]

        self._started_at = datetime.datetime.now()
        self._raw_lines  = []

        log.info("start: model=%s lang=%s mode=%s device=%s", model, lang or "auto", mode, self.device.name)

        loopback_dev = self._selected_loopback_device_id()
        self.worker = TranscriptionWorker(model, self.device, mode, lang, loopback_dev)
        self.worker.line_ready.connect(self._on_line)
        self.worker.status_changed.connect(self._on_status)
        self.worker.error.connect(self._on_error)
        self.worker.perf_update.connect(self._on_perf)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

        self.rec_btn.setText("  Stop Recording")
        self.rec_btn.setProperty("active", "true")
        self.rec_btn.setStyle(self.rec_btn.style())
        self.model_combo.setEnabled(False)
        self.lang_combo.setEnabled(False)
        self.source_combo.setEnabled(False)
        self.speaker_combo.setEnabled(False)
        self.recording_changed.emit(True)

    def _stop(self) -> None:
        if self.worker:
            self.worker.stop()
            QTimer.singleShot(4000, self._force_stop)
        self.rec_btn.setText("  Stopping...")
        self.rec_btn.setEnabled(False)
        self.recording_changed.emit(False)

    def _force_stop(self) -> None:
        if self.worker and self.worker.isRunning():
            log.warning("force-terminating stuck worker thread")
            self.worker.terminate()
            self.worker.wait(1000)
            self._on_worker_finished()

    @Slot()
    def _on_worker_finished(self) -> None:
        self._ended_at = datetime.datetime.now()
        self.rec_btn.setText("  Start Recording")
        self.rec_btn.setProperty("active", "false")
        self.rec_btn.setStyle(self.rec_btn.style())
        self.rec_btn.setEnabled(True)
        self.model_combo.setEnabled(True)
        self.lang_combo.setEnabled(True)
        self.source_combo.setEnabled(True)
        self.speaker_combo.setEnabled(True)
        if self.lines:
            self.save_btn.setEnabled(True)
            self._auto_save()

    # ── Worker slots ──────────────────────────────────────────────────────────

    @Slot(str, str, str)
    def _on_line(self, ts: str, source: str, text: str) -> None:
        if source == "info":
            color = "#484848"
            prefix = ""
        elif source == "them":
            color  = "#4a9eca"
            prefix = "THEM"
        else:
            color  = "#5aad54"
            prefix = "YOU"

        plain = f"[{ts}] {prefix}  {text}"
        if source != "info":
            self.lines.append(plain)
            self._raw_lines.append((ts, source, text))
        self.save_btn.setEnabled(bool(self.lines))
        self.line_count.setText(f"{len(self.lines)} lines")

        lang = self._last_detected_lang.lower()
        direction = "rtl" if lang in RTL_LANGS else "ltr"

        if source == "info":
            html = (
                f'<p style="margin:1px 0; direction: {direction};">'
                f'<span style="color:#404040; font-size:8pt;">{text}</span>'
                f'</p>'
            )
        else:
            html = (
                f'<p style="margin:2px 0; direction: {direction};">'
                f'<span style="color:#404040; font-family: Consolas, monospace; font-size:8pt;">[{ts}]</span>'
                f'&nbsp;<span style="color:{color}; font-size:8pt; font-weight:600;">{prefix}</span>'
                f'&nbsp;<span style="color:#c0c0c0;">{text}</span>'
                f'</p>'
            )

        cur = self.transcript.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        self.transcript.setTextCursor(cur)
        self.transcript.insertHtml(html)
        self.transcript.ensureCursorVisible()

    @Slot(str)
    def _on_status(self, msg: str) -> None:
        self._set_status(msg)

    @Slot(str)
    def _on_error(self, msg: str) -> None:
        log.warning("worker error: %s", msg)
        self._set_status(f"Error: {msg}")

    @Slot(float, float, str)
    def _on_perf(self, rtf: float, lat_ms: float, lang: str) -> None:
        self._last_detected_lang = lang.lower()

        if rtf < 0.5:
            rtf_color = "#4a9a46"
        elif rtf < 0.85:
            rtf_color = "#b8922a"
        else:
            rtf_color = "#9e3030"

        self.rtf_label.setText(
            f'<span style="color:{rtf_color}; font-family: Consolas, monospace; font-size:8pt;">RTF {rtf:.2f}x</span>'
        )
        self.lat_label.setText(f"{lat_ms:.0f} ms / chunk")
        self.lang_label.setText(f"lang: {lang.lower()}")

    # ── Transcript I/O ────────────────────────────────────────────────────────

    def _output_dir(self) -> Path:
        d = self.settings.output_dir
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _auto_save(self) -> None:
        now  = datetime.datetime.now()
        path = self._output_dir() / f"meeting_{now.strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        self._write_async(path)
        self._set_status(f"Saved to {path}")
        if self.obs_toggle.isChecked() and self.settings.obsidian_vault:
            self._write_obsidian_async()

    def _write_obsidian_async(self) -> None:
        vault      = self.settings.obsidian_vault
        wikilinks  = self.obs_wikilinks_chk.isChecked()
        raw        = list(self._raw_lines)
        started    = self._started_at or datetime.datetime.now()
        ended      = self._ended_at   or datetime.datetime.now()
        lang_label = self.lang_combo.currentText()
        detected   = self._last_detected_lang.upper()
        if lang_label == "Auto-detect" and detected:
            lang_label = f"Auto-detect ({detected})"

        data = SessionData(
            started_at   = started,
            ended_at     = ended,
            model        = self.model_combo.currentText(),
            device_name  = self.device.name,
            language     = lang_label,
            lines        = raw,
            capture_mode = SOURCE_MODES[self.source_combo.currentText()],
        )

        def _do() -> None:
            try:
                out = ObsidianWriter(auto_wikilinks=wikilinks).write_to_vault(data, Path(vault))
                log.info("Obsidian note written to %s", out)
            except Exception as exc:
                log.error("Obsidian write failed: %s", exc)

        threading.Thread(target=_do, daemon=True).start()

    @Slot()
    def _save(self) -> None:
        if not self.lines:
            return
        default = str(
            self._output_dir() / f"meeting_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')}.txt"
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Transcript", default, "Text files (*.txt)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if path:
            self._write_async(Path(path))
            self._set_status(f"Saving to {path}...")

    def _write_async(self, path: Path) -> None:
        snapshot    = list(self.lines)
        model       = self.model_combo.currentText()
        device_name = self.device.name
        lang        = self.lang_combo.currentText()
        detected    = self._last_detected_lang.upper()
        now         = datetime.datetime.now()

        def _do() -> None:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write("Meet-Scribe Transcript\n")
                    fh.write(f"Date    : {now.strftime('%A, %B %d %Y  %H:%M')}\n")
                    fh.write(f"Model   : {model}  |  Device: {device_name}\n")
                    fh.write(
                        f"Language: {lang}"
                        + (f" ({detected})" if lang == "Auto-detect" and detected else "")
                        + "\n"
                    )
                    fh.write("=" * 60 + "\n\n")
                    fh.write("\n".join(snapshot) + "\n")
                log.info("transcript written -> %s (%d lines)", path, len(snapshot))
            except Exception as exc:
                log.error("save failed: %s", exc)

        threading.Thread(target=_do, daemon=True).start()

    @Slot()
    def _clear(self) -> None:
        self.transcript.clear()
        self.lines.clear()
        self._raw_lines.clear()
        self.line_count.setText("0 lines")
        self.save_btn.setEnabled(False)
        for _lbl in (self.rtf_label, self.lat_label, self.lang_label, self.chunk_label):
            _lbl.setText("-")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_status(self, msg: str) -> None:
        self.status_bar.showMessage(msg)

    def set_tray_notify(self, fn) -> None:
        self._tray_notify_fn = fn

    def _tray_notify_fn(self) -> None:
        pass
