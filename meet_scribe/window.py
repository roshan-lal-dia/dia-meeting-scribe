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
    QScrollArea,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .audio.devices import AudioDevice, MicDevice, list_microphones, list_speakers
from .export.base import SessionData
from .export.obsidian import ObsidianWriter
from .export.srt import write_srt, write_vtt
from .settings import AppSettings
from .transcribe.device import DeviceInfo, detect_device, list_cuda_devices
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

COMPUTE_MODES = ["Auto", "GPU", "CPU"]

RTL_LANGS = frozenset({"ar", "fa", "he", "ur"})


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    return f


class MainWindow(QMainWindow):
    recording_changed = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self.settings = AppSettings()
        self._cuda_devices: list[str] = list_cuda_devices()
        self.device: DeviceInfo = self._build_device()
        self.worker: TranscriptionWorker | None = None
        self._paused: bool = False
        self.lines: list[str] = []
        self._raw_lines: list[tuple[str, str, str]] = []
        self._last_detected_lang: str = ""
        self._started_at: datetime.datetime | None = None
        self._ended_at:   datetime.datetime | None = None

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._setup_ui()
        self._restore_settings()
        self._setup_shortcuts()

    def _build_device(self) -> DeviceInfo:
        mode = self.settings.compute_device   # "auto" | "gpu" | "cpu"
        idx  = self.settings.cuda_index
        force_cpu = (mode == "cpu")
        return detect_device(force_cpu=force_cpu, cuda_index=idx)

    # ── UI construction ──────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setWindowTitle("Meet-Scribe")
        self.setMinimumSize(860, 560)
        self.resize(1080, 720)

        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_main(), stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._set_status("Ready  |  Space = record  |  P = pause  |  Ctrl+S = save")

    def _build_sidebar(self) -> QWidget:
        # Outer container (fixed width, opaque sidebar background)
        outer = QWidget()
        outer.setObjectName("sidebar")
        outer_v = QVBoxLayout(outer)
        outer_v.setSpacing(0)
        outer_v.setContentsMargins(0, 0, 0, 0)

        # ── Header (non-scrollable) ──────────────────────────────────────────
        header = QWidget()
        header.setObjectName("sidebarHeader")
        hv = QVBoxLayout(header)
        hv.setContentsMargins(16, 20, 16, 12)
        hv.setSpacing(2)

        title = QLabel("Meet-Scribe")
        title.setObjectName("appTitle")
        hv.addWidget(title)

        gpu_tag = "GPU" if self.device.is_gpu else "CPU"
        self._device_subtitle = QLabel(f"{self.device.name}  |  {gpu_tag}")
        self._device_subtitle.setObjectName("deviceSubtitle")
        hv.addWidget(self._device_subtitle)
        outer_v.addWidget(header)

        # ── Record + Pause buttons ────────────────────────────────────────────
        btn_area = QWidget()
        bv = QVBoxLayout(btn_area)
        bv.setContentsMargins(16, 6, 16, 6)
        bv.setSpacing(6)

        self.rec_btn = QPushButton("  Start Recording")
        self.rec_btn.setObjectName("recBtn")
        self.rec_btn.setFixedHeight(44)
        self.rec_btn.setToolTip("Start / stop recording  [Space]")
        self.rec_btn.clicked.connect(self._toggle)
        bv.addWidget(self.rec_btn)

        self.pause_btn = QPushButton("  Pause")
        self.pause_btn.setObjectName("pauseBtn")
        self.pause_btn.setFixedHeight(34)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setToolTip("Pause / resume transcription  [P]")
        self.pause_btn.clicked.connect(self._toggle_pause)
        bv.addWidget(self.pause_btn)

        outer_v.addWidget(btn_area)
        outer_v.addWidget(_sep())

        # ── Scrollable settings ────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setObjectName("sidebarScroll")

        inner = QWidget()
        inner.setObjectName("sidebarInner")
        v = QVBoxLayout(inner)
        v.setSpacing(0)
        v.setContentsMargins(16, 14, 16, 14)

        def _field(label: str, widget: QWidget) -> None:
            lbl = QLabel(label)
            lbl.setObjectName("sectionLabel")
            v.addWidget(lbl)
            v.addSpacing(4)
            v.addWidget(widget)
            v.addSpacing(12)

        # ── Compute device ─────────────────────────────────────────────────────
        self.compute_combo = QComboBox()
        self.compute_combo.addItems(COMPUTE_MODES)
        self.compute_combo.setToolTip(
            "Auto: use GPU if available.\n"
            "GPU: force CUDA even if slow.\n"
            "CPU: force CPU — useful for int8-only inference or VRAM pressure."
        )
        self.compute_combo.currentTextChanged.connect(self._on_compute_changed)
        _field("COMPUTE", self.compute_combo)

        # CUDA device picker (visible only when GPU available)
        self._cuda_row = QWidget()
        cr = QVBoxLayout(self._cuda_row)
        cr.setContentsMargins(0, 0, 0, 0)
        cr.setSpacing(4)
        cuda_lbl = QLabel("GPU DEVICE")
        cuda_lbl.setObjectName("sectionLabel")
        cr.addWidget(cuda_lbl)
        self.cuda_combo = QComboBox()
        if self._cuda_devices:
            for i, name in enumerate(self._cuda_devices):
                self.cuda_combo.addItem(f"[{i}] {name}", userData=i)
        else:
            self.cuda_combo.addItem("No CUDA devices detected")
        self.cuda_combo.currentIndexChanged.connect(self._on_cuda_device_changed)
        cr.addWidget(self.cuda_combo)
        v.addWidget(self._cuda_row)
        v.addSpacing(12)
        self._cuda_row.setVisible(bool(self._cuda_devices))

        # ── Whisper model ──────────────────────────────────────────────────────
        self.model_combo = QComboBox()
        self.model_combo.addItems(MODEL_SIZES)
        self.model_combo.setCurrentText(self.device.default_model)
        self.model_combo.setToolTip(
            "Whisper model size.\n"
            ".en variants are English-only but faster.\n"
            "large-v3 is most accurate; needs ~3 GB VRAM."
        )
        _field("MODEL", self.model_combo)

        # ── Language ───────────────────────────────────────────────────────────
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(list(LANGUAGES.keys()))
        self.lang_combo.setToolTip(
            "Auto-detect: Whisper identifies language each chunk.\n"
            "Pin a language for faster, more consistent results."
        )
        self.lang_combo.currentTextChanged.connect(self._on_language_changed)
        _field("LANGUAGE", self.lang_combo)

        # ── Capture mode ───────────────────────────────────────────────────────
        self.source_combo = QComboBox()
        self.source_combo.addItems(list(SOURCE_MODES.keys()))
        self.source_combo.setToolTip("Audio source to capture")
        self.source_combo.currentTextChanged.connect(self._on_source_changed)
        _field("CAPTURE", self.source_combo)

        # ── Speaker (loopback) ─────────────────────────────────────────────────
        self._speaker_row = QWidget()
        sr = QVBoxLayout(self._speaker_row)
        sr.setContentsMargins(0, 0, 0, 0)
        sr.setSpacing(4)
        spk_lbl = QLabel("SPEAKER  (loopback)")
        spk_lbl.setObjectName("sectionLabel")
        sr.addWidget(spk_lbl)
        self.speaker_combo = QComboBox()
        self.speaker_combo.setToolTip(
            "Playback device for WASAPI loopback.\n"
            "* = loopback-capable   ! = Bluetooth/virtual (may fail)"
        )
        self._populate_speaker_combo()
        sr.addWidget(self.speaker_combo)
        v.addWidget(self._speaker_row)
        v.addSpacing(12)

        # ── Microphone ─────────────────────────────────────────────────────────
        self._mic_row = QWidget()
        mr = QVBoxLayout(self._mic_row)
        mr.setContentsMargins(0, 0, 0, 0)
        mr.setSpacing(4)
        mic_lbl = QLabel("MICROPHONE")
        mic_lbl.setObjectName("sectionLabel")
        mr.addWidget(mic_lbl)
        self.mic_combo = QComboBox()
        self.mic_combo.setToolTip("Microphone input device")
        self._populate_mic_combo()
        mr.addWidget(self.mic_combo)
        v.addWidget(self._mic_row)
        v.addSpacing(12)

        # ── Audio options ──────────────────────────────────────────────────────
        audio_lbl = QLabel("AUDIO OPTIONS")
        audio_lbl.setObjectName("sectionLabel")
        v.addWidget(audio_lbl)
        v.addSpacing(4)
        self.noise_chk = QCheckBox("Noise suppression")
        self.noise_chk.setToolTip("Apply RNNoise / webrtcvad pre-processing to reduce background noise")
        v.addWidget(self.noise_chk)
        self.punct_chk = QCheckBox("Auto-punctuation")
        self.punct_chk.setChecked(True)
        self.punct_chk.setToolTip("Whisper adds punctuation automatically — uncheck to get raw words only")
        v.addWidget(self.punct_chk)
        v.addSpacing(14)

        v.addWidget(_sep())
        v.addSpacing(14)

        # ── Keywords ───────────────────────────────────────────────────────────
        kw_lbl = QLabel("KEYWORDS")
        kw_lbl.setObjectName("sectionLabel")
        v.addWidget(kw_lbl)
        v.addSpacing(4)
        self.keywords_edit = QLineEdit()
        self.keywords_edit.setPlaceholderText("action item, follow up, deadline...")
        self.keywords_edit.setToolTip("Comma-separated keywords to highlight amber in the transcript")
        v.addWidget(self.keywords_edit)
        v.addSpacing(14)

        v.addWidget(_sep())
        v.addSpacing(14)

        # ── Obsidian ───────────────────────────────────────────────────────────
        obs_lbl = QLabel("OBSIDIAN")
        obs_lbl.setObjectName("sectionLabel")
        v.addWidget(obs_lbl)
        v.addSpacing(6)
        self.obs_toggle = QCheckBox("Save to vault")
        self.obs_toggle.stateChanged.connect(self._on_obs_toggle)
        v.addWidget(self.obs_toggle)
        v.addSpacing(6)

        vault_row = QHBoxLayout()
        vault_row.setSpacing(4)
        self.obs_path_edit = QLineEdit()
        self.obs_path_edit.setPlaceholderText("Vault folder...")
        self.obs_path_edit.setReadOnly(True)
        self.obs_path_edit.setToolTip("Notes saved to <vault>/Meetings/YYYY-MM/")
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
        self.obs_wikilinks_chk.setToolTip("Wrap repeated proper nouns in [[double brackets]]")
        v.addWidget(self.obs_wikilinks_chk)
        v.addSpacing(14)

        v.addWidget(_sep())
        v.addSpacing(12)

        # ── Save / Clear ───────────────────────────────────────────────────────
        action_row = QHBoxLayout()
        action_row.setSpacing(6)
        self.save_btn = QPushButton("Save")
        self.save_btn.setEnabled(False)
        self.save_btn.setToolTip("Save transcript  [Ctrl+S]")
        self.save_btn.clicked.connect(self._save)
        action_row.addWidget(self.save_btn)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setToolTip("Clear transcript")
        self.clear_btn.clicked.connect(self._clear)
        action_row.addWidget(self.clear_btn)
        v.addLayout(action_row)
        v.addSpacing(16)

        # ── Perf stats ─────────────────────────────────────────────────────────
        self.rtf_label   = QLabel("RTF -")
        self.lat_label   = QLabel("Latency -")
        self.lang_label  = QLabel("Lang -")
        self.chunk_label = QLabel("Chunks -")
        for lbl in (self.rtf_label, self.lat_label, self.lang_label, self.chunk_label):
            lbl.setObjectName("stat")
            v.addWidget(lbl)

        v.addStretch()

        scroll.setWidget(inner)
        outer_v.addWidget(scroll, stretch=1)
        return outer

    def _build_main(self) -> QWidget:
        content = QWidget()
        content.setObjectName("mainContent")

        v = QVBoxLayout(content)
        v.setSpacing(0)
        v.setContentsMargins(20, 18, 16, 10)

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

        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setAcceptRichText(True)
        self.transcript.setObjectName("transcript")
        self.transcript.setPlaceholderText(
            "Transcript will appear here once you start recording...\n\n"
            "Space = Start/Stop  |  P = Pause/Resume  |  Ctrl+S = Save"
        )
        v.addWidget(self.transcript, stretch=1)

        return content

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence(Qt.Key.Key_Space), self).activated.connect(self._toggle)
        QShortcut(QKeySequence(Qt.Key.Key_P),     self).activated.connect(self._toggle_pause)
        QShortcut(QKeySequence.StandardKey.Save,  self).activated.connect(self._save)

    # ── Device population ─────────────────────────────────────────────────────

    def _populate_speaker_combo(self) -> None:
        self._speaker_devices: list[AudioDevice] = list_speakers()
        self.speaker_combo.clear()
        for d in self._speaker_devices:
            prefix = "* " if d.likely_loopback_capable else "! "
            label  = prefix + d.name + (" (default)" if d.is_default else "")
            self.speaker_combo.addItem(label, userData=d.id)
        for i, d in enumerate(self._speaker_devices):
            if d.likely_loopback_capable:
                self.speaker_combo.setCurrentIndex(i)
                break

    def _populate_mic_combo(self) -> None:
        self._mic_devices: list[MicDevice] = list_microphones()
        self.mic_combo.clear()
        if not self._mic_devices:
            self.mic_combo.addItem("No microphones detected")
            return
        for d in self._mic_devices:
            label = d.name + (" (default)" if d.is_default else "")
            self.mic_combo.addItem(label, userData=d.id)
        # Restore saved mic
        saved = self.settings.mic_device
        for i, d in enumerate(self._mic_devices):
            if d.name == saved:
                self.mic_combo.setCurrentIndex(i)
                break

    def _selected_loopback_device_id(self) -> str | None:
        idx = self.speaker_combo.currentIndex()
        if 0 <= idx < len(self._speaker_devices):
            return self._speaker_devices[idx].id
        return None

    def _selected_mic_name(self) -> str | None:
        idx = self.mic_combo.currentIndex()
        if 0 <= idx < len(self._mic_devices):
            return self._mic_devices[idx].name
        return None

    # ── Compute / device slots ────────────────────────────────────────────────

    @Slot(str)
    def _on_compute_changed(self, mode: str) -> None:
        self.settings.compute_device = mode.lower()
        self.settings.sync()
        self._cuda_row.setVisible(
            bool(self._cuda_devices) and mode != "CPU"
        )
        self.device = self._build_device()
        gpu_tag = "GPU" if self.device.is_gpu else "CPU"
        self._device_subtitle.setText(f"{self.device.name}  |  {gpu_tag}")

    @Slot(int)
    def _on_cuda_device_changed(self, idx: int) -> None:
        self.settings.cuda_index = idx
        self.settings.sync()
        self.device = self._build_device()

    # ── Source / mic visibility ────────────────────────────────────────────────

    @Slot(str)
    def _on_source_changed(self, mode_label: str) -> None:
        mode = SOURCE_MODES.get(mode_label, "system")
        uses_loopback = mode in ("system", "both")
        uses_mic      = mode in ("mic", "both")
        self._speaker_row.setVisible(uses_loopback)
        self._mic_row.setVisible(uses_mic)

    # ── Language hint ──────────────────────────────────────────────────────────

    @Slot(str)
    def _on_language_changed(self, lang: str) -> None:
        code  = LANGUAGES.get(lang)
        model = self.model_combo.currentText()
        if code and code != "en" and model.endswith(".en"):
            base = model.replace(".en", "")
            self.model_combo.setCurrentText(base)
            self._set_status(f"Switched to '{base}' — multilingual model required for {lang}")

    # ── Obsidian ───────────────────────────────────────────────────────────────

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

    # ── Settings ───────────────────────────────────────────────────────────────

    def _restore_settings(self) -> None:
        s = self.settings
        if (m := s.model) in MODEL_SIZES:
            self.model_combo.setCurrentText(m)
        if (lm := s.language) in LANGUAGES:
            self.lang_combo.setCurrentText(lm)
        if (cm := s.capture_mode) in SOURCE_MODES:
            self.source_combo.setCurrentText(cm)
        if geo := s.geometry:
            self.restoreGeometry(geo)
        self.obs_toggle.setChecked(s.obsidian_enabled)
        self.obs_wikilinks_chk.setChecked(s.obsidian_wikilinks)
        if vault := s.obsidian_vault:
            self.obs_path_edit.setText(str(vault))
        # Compute
        mode_map = {"auto": "Auto", "gpu": "GPU", "cpu": "CPU"}
        self.compute_combo.setCurrentText(mode_map.get(s.compute_device, "Auto"))
        if s.cuda_index < self.cuda_combo.count():
            self.cuda_combo.setCurrentIndex(s.cuda_index)
        # Mic
        saved_mic = s.mic_device
        for i, d in enumerate(self._mic_devices):
            if d.name == saved_mic:
                self.mic_combo.setCurrentIndex(i)
                break
        self.noise_chk.setChecked(s.noise_suppression)
        self.punct_chk.setChecked(s.auto_punctuation)
        self.keywords_edit.setText(", ".join(s.keywords))
        # Trigger visibility update
        self._on_source_changed(self.source_combo.currentText())

    def _persist_settings(self) -> None:
        s = self.settings
        s.model              = self.model_combo.currentText()
        s.language           = self.lang_combo.currentText()
        s.capture_mode       = self.source_combo.currentText()
        s.geometry           = bytes(self.saveGeometry())
        s.obsidian_enabled   = self.obs_toggle.isChecked()
        s.obsidian_wikilinks = self.obs_wikilinks_chk.isChecked()
        s.noise_suppression  = self.noise_chk.isChecked()
        s.auto_punctuation   = self.punct_chk.isChecked()
        kw_raw = self.keywords_edit.text()
        s.keywords = [k.strip() for k in kw_raw.split(",") if k.strip()]
        if (mic := self._selected_mic_name()):
            s.mic_device = mic
        s.sync()

    # ── Window events ──────────────────────────────────────────────────────────

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

    # ── Recording control ──────────────────────────────────────────────────────

    @Slot()
    def _toggle(self) -> None:
        if self.worker and self.worker.isRunning():
            self._stop()
        else:
            self._start()

    @Slot()
    def _toggle_pause(self) -> None:
        if not self.worker or not self.worker.isRunning():
            return
        if self._paused:
            self.worker.resume()
            self._paused = False
            self.pause_btn.setText("  Pause")
            self.pause_btn.setProperty("active", "false")
            self.pause_btn.setStyle(self.pause_btn.style())
            self._set_status("Resumed")
        else:
            self.worker.pause()
            self._paused = True
            self.pause_btn.setText("  Resume")
            self.pause_btn.setProperty("active", "true")
            self.pause_btn.setStyle(self.pause_btn.style())
            self._set_status("Paused — press P or click Resume to continue")

    def _start(self) -> None:
        mode     = SOURCE_MODES[self.source_combo.currentText()]
        model    = self.model_combo.currentText()
        lang_key = self.lang_combo.currentText()
        lang     = LANGUAGES[lang_key]

        self._started_at = datetime.datetime.now()
        self._raw_lines  = []
        self._paused     = False

        log.info("start: model=%s lang=%s mode=%s device=%s", model, lang or "auto", mode, self.device.name)

        loopback_dev = self._selected_loopback_device_id()
        mic_name     = self._selected_mic_name()
        self.worker  = TranscriptionWorker(model, self.device, mode, lang, loopback_dev, mic_name)
        self.worker.line_ready.connect(self._on_line)
        self.worker.status_changed.connect(self._on_status)
        self.worker.error.connect(self._on_error)
        self.worker.perf_update.connect(self._on_perf)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

        self.rec_btn.setText("  Stop Recording")
        self.rec_btn.setProperty("active", "true")
        self.rec_btn.setStyle(self.rec_btn.style())
        self.pause_btn.setEnabled(True)
        self.model_combo.setEnabled(False)
        self.lang_combo.setEnabled(False)
        self.source_combo.setEnabled(False)
        self.speaker_combo.setEnabled(False)
        self.mic_combo.setEnabled(False)
        self.compute_combo.setEnabled(False)
        self.recording_changed.emit(True)

    def _stop(self) -> None:
        if self._paused and self.worker:
            self.worker.resume()
            self._paused = False
        if self.worker:
            self.worker.stop()
            QTimer.singleShot(4000, self._force_stop)
        self.rec_btn.setText("  Stopping...")
        self.rec_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("  Pause")
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
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("  Pause")
        self.model_combo.setEnabled(True)
        self.lang_combo.setEnabled(True)
        self.source_combo.setEnabled(True)
        self.speaker_combo.setEnabled(True)
        self.mic_combo.setEnabled(True)
        self.compute_combo.setEnabled(True)
        if self.lines:
            self.save_btn.setEnabled(True)
            self._auto_save()

    # ── Worker slots ───────────────────────────────────────────────────────────

    @Slot(str, str, str)
    def _on_line(self, ts: str, source: str, text: str) -> None:
        if source == "info":
            color  = "#404040"
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

        lang      = self._last_detected_lang.lower()
        direction = "rtl" if lang in RTL_LANGS else "ltr"
        hl_text   = self._highlight_keywords(text)

        if source == "info":
            html = (
                f'<p style="margin:1px 0; direction:{direction};">'
                f'<span style="color:#404040; font-size:8pt;">{hl_text}</span>'
                f'</p>'
            )
        else:
            html = (
                f'<p style="margin:2px 0; direction:{direction};">'
                f'<span style="color:#404040; font-family:Consolas,monospace; font-size:8pt;">[{ts}]</span>'
                f'&nbsp;<span style="color:{color}; font-size:8pt; font-weight:600;">{prefix}</span>'
                f'&nbsp;<span style="color:#c0c0c0;">{hl_text}</span>'
                f'</p>'
            )

        cur = self.transcript.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        self.transcript.setTextCursor(cur)
        self.transcript.insertHtml(html)
        self.transcript.ensureCursorVisible()

    def _highlight_keywords(self, text: str) -> str:
        """Wrap any matching keywords in amber highlight span."""
        import html as _html
        import re
        kws = self.settings.keywords
        if not kws:
            return _html.escape(text)
        result = _html.escape(text)
        for kw in kws:
            pattern = re.compile(re.escape(kw), re.IGNORECASE)
            result = pattern.sub(
                lambda m: f'<span style="background:#7a5c00; color:#ffd080;">{m.group()}</span>',
                result,
            )
        return result

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
            f'<span style="color:{rtf_color}; font-family:Consolas,monospace; font-size:8pt;">RTF {rtf:.2f}x</span>'
        )
        self.lat_label.setText(f"{lat_ms:.0f} ms / chunk")
        self.lang_label.setText(f"lang: {lang.lower()}")

    # ── Transcript I/O ─────────────────────────────────────────────────────────

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
        vault     = self.settings.obsidian_vault
        wikilinks = self.obs_wikilinks_chk.isChecked()
        raw       = list(self._raw_lines)
        started   = self._started_at or datetime.datetime.now()
        ended     = self._ended_at   or datetime.datetime.now()
        lang_lbl  = self.lang_combo.currentText()
        detected  = self._last_detected_lang.upper()
        if lang_lbl == "Auto-detect" and detected:
            lang_lbl = f"Auto-detect ({detected})"

        data = SessionData(
            started_at   = started,
            ended_at     = ended,
            model        = self.model_combo.currentText(),
            device_name  = self.device.name,
            language     = lang_lbl,
            lines        = raw,
            capture_mode = SOURCE_MODES[self.source_combo.currentText()],
        )

        def _do() -> None:
            try:
                out = ObsidianWriter(auto_wikilinks=wikilinks).write_to_vault(data, Path(vault))
                log.info("Obsidian note -> %s", out)
            except Exception as exc:
                log.error("Obsidian write failed: %s", exc)

        threading.Thread(target=_do, daemon=True).start()

    @Slot()
    def _save(self) -> None:
        if not self.lines:
            return
        stem    = f"meeting_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')}"
        default = str(self._output_dir() / f"{stem}.txt")
        path, _fmt = QFileDialog.getSaveFileName(
            self,
            "Save Transcript",
            default,
            "Plain text (*.txt);;SRT subtitles (*.srt);;WebVTT subtitles (*.vtt)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if not path:
            return
        if path.endswith(".srt"):
            self._export_srt(Path(path))
        elif path.endswith(".vtt"):
            self._export_vtt(Path(path))
        else:
            self._write_async(Path(path))
        self._set_status(f"Saving to {path}...")

    def _session_data(self) -> SessionData:
        lang_lbl = self.lang_combo.currentText()
        detected = self._last_detected_lang.upper()
        if lang_lbl == "Auto-detect" and detected:
            lang_lbl = f"Auto-detect ({detected})"
        return SessionData(
            started_at   = self._started_at or datetime.datetime.now(),
            ended_at     = self._ended_at   or datetime.datetime.now(),
            model        = self.model_combo.currentText(),
            device_name  = self.device.name,
            language     = lang_lbl,
            lines        = list(self._raw_lines),
            capture_mode = SOURCE_MODES[self.source_combo.currentText()],
        )

    def _export_srt(self, path: Path) -> None:
        data = self._session_data()
        threading.Thread(
            target=write_srt, args=(data, path), daemon=True
        ).start()

    def _export_vtt(self, path: Path) -> None:
        data = self._session_data()
        threading.Thread(
            target=write_vtt, args=(data, path), daemon=True
        ).start()

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
                log.info("transcript -> %s (%d lines)", path, len(snapshot))
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

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _set_status(self, msg: str) -> None:
        self.status_bar.showMessage(msg)

    def set_tray_notify(self, fn) -> None:
        self._tray_notify_fn = fn

    def _tray_notify_fn(self) -> None:
        pass
