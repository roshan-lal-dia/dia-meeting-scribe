"""First-run onboarding wizard (4 steps)."""
from __future__ import annotations

import logging

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

log = logging.getLogger(__name__)

ONBOARDING_DONE_KEY = "onboarding_done_v1"


def should_show(settings: object) -> bool:
    return not bool(settings._q.value(ONBOARDING_DONE_KEY, False))


def mark_done(settings: object) -> None:
    settings._q.setValue(ONBOARDING_DONE_KEY, True)


class _WelcomePage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Welcome to Meet-Scribe")
        self.setSubTitle("Local, private transcription — no cloud, no data leaves your PC.")
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        for text in (
            "Meet-Scribe listens to your meetings and transcribes them in real-time"
            " using a local AI model (Whisper).",
            "Your audio and transcripts never leave your computer.",
            "This wizard will help you set up in under a minute.",
        ):
            lbl = QLabel(text)
            lbl.setWordWrap(True)
            lay.addWidget(lbl)
        lay.addStretch()


class _AudioPage(QWizardPage):
    def __init__(self, settings: object) -> None:
        super().__init__()
        self._settings = settings
        self.setTitle("Audio Source")
        self.setSubTitle("Choose what Meet-Scribe should listen to.")
        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        desc = QLabel(
            "System Audio (loopback): captures everything playing through your speakers"
            " — ideal for online meetings (Teams, Zoom, Google Meet).\n\n"
            "Microphone: captures your voice — use for in-person meetings.\n\n"
            "Both: combines system audio and your microphone."
        )
        desc.setWordWrap(True)
        lay.addWidget(desc)

        row = QHBoxLayout()
        row.addWidget(QLabel("Capture source:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(["System Audio (loopback)", "Microphone", "Both"])
        row.addWidget(self.source_combo)
        row.addStretch()
        lay.addLayout(row)
        lay.addStretch()

    def validatePage(self) -> bool:
        mode_map = {0: "system", 1: "mic", 2: "both"}
        self._settings.capture_mode = mode_map[self.source_combo.currentIndex()]
        return True


class _ModelPage(QWizardPage):
    def __init__(self, settings: object) -> None:
        super().__init__()
        self._settings = settings
        self.setTitle("Transcription Model")
        self.setSubTitle("Larger models are more accurate but slower and use more memory.")
        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        self.model_combo = QComboBox()
        for model, spec in (
            ("tiny.en",   "Fastest — English only — ~75 MB VRAM"),
            ("base.en",   "Fast — English only — ~150 MB VRAM  (recommended)"),
            ("small.en",  "Balanced — English only — ~500 MB VRAM"),
            ("medium.en", "Accurate — English only — ~1.5 GB VRAM"),
            ("large-v3",  "Best accuracy — multilingual — ~3 GB VRAM"),
        ):
            self.model_combo.addItem(f"{model}  |  {spec}", userData=model)

        cur = settings.model
        for i in range(self.model_combo.count()):
            if self.model_combo.itemData(i) == cur:
                self.model_combo.setCurrentIndex(i)
                break

        row = QHBoxLayout()
        row.addWidget(QLabel("Model:"))
        row.addWidget(self.model_combo, stretch=1)
        lay.addLayout(row)

        hint = QLabel(
            "Tip: if your PC has an NVIDIA GPU, Meet-Scribe will use it automatically."
            " You can override to CPU-only in Settings."
        )
        hint.setWordWrap(True)
        lay.addWidget(hint)
        lay.addStretch()

    def validatePage(self) -> bool:
        self._settings.model = self.model_combo.currentData()
        return True


class _ReadyPage(QWizardPage):
    def __init__(self, settings: object) -> None:
        super().__init__()
        self._settings = settings
        self.setTitle("You're all set!")
        self.setSubTitle("Here are a few tips to get the most from Meet-Scribe.")
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        for text in (
            "Press Record (or Ctrl+R) to start capturing a meeting.",
            "The transcript appears in real-time — scroll while recording.",
            "Press Ctrl+S to save as TXT, SRT, or Markdown.",
            "Keywords typed in the sidebar are highlighted amber in the transcript.",
            "Right-click the system tray icon for quick access to all features.",
            "The app stays in the system tray when you close the window.",
        ):
            lbl = QLabel(f"•  {text}")
            lbl.setWordWrap(True)
            lay.addWidget(lbl)
        lay.addSpacing(8)
        self.start_chk = QCheckBox("Start recording immediately after finishing this wizard")
        lay.addWidget(self.start_chk)
        lay.addStretch()


class OnboardingWizard(QWizard):
    """Four-step first-run wizard."""

    def __init__(self, settings: object, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("Meet-Scribe Setup")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(560, 400)

        self.addPage(_WelcomePage())
        self.addPage(_AudioPage(settings))
        self.addPage(_ModelPage(settings))
        self._ready_page = _ReadyPage(settings)
        self.addPage(self._ready_page)

        self.button(QWizard.WizardButton.FinishButton).setText("Start Meet-Scribe")

    @property
    def start_immediately(self) -> bool:
        return self._ready_page.start_chk.isChecked()

    def accept(self) -> None:
        mark_done(self._settings)
        super().accept()
