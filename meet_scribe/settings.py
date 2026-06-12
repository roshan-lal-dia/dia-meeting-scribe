"""Persistent app settings backed by QSettings (registry on Windows)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings

_ORG = "MeetingScribe"
_APP = "MeetingScribe"


class AppSettings:
    def __init__(self):
        self._q = QSettings(_ORG, _APP)

    # ── Model ──────────────────────────────────────────────────────────────────
    @property
    def model(self) -> str:
        return self._q.value("model", "base.en")

    @model.setter
    def model(self, v: str) -> None:
        self._q.setValue("model", v)

    # ── Compute device ─────────────────────────────────────────────────────────
    @property
    def compute_device(self) -> str:
        """One of: "auto", "gpu", "cpu"."""
        return self._q.value("compute_device", "auto")

    @compute_device.setter
    def compute_device(self, v: str) -> None:
        self._q.setValue("compute_device", v)

    @property
    def cuda_index(self) -> int:
        """Which CUDA device to use (0 = first GPU)."""
        return int(self._q.value("cuda_index", 0))

    @cuda_index.setter
    def cuda_index(self, v: int) -> None:
        self._q.setValue("cuda_index", v)

    # ── Capture ────────────────────────────────────────────────────────────────
    @property
    def capture_mode(self) -> str:
        return self._q.value("capture_mode", "System audio only")

    @capture_mode.setter
    def capture_mode(self, v: str) -> None:
        self._q.setValue("capture_mode", v)

    # ── Microphone ─────────────────────────────────────────────────────────────
    @property
    def mic_device(self) -> str:
        """Saved mic device name; empty string = system default."""
        return self._q.value("mic_device", "")

    @mic_device.setter
    def mic_device(self, v: str) -> None:
        self._q.setValue("mic_device", v)

    # ── Noise suppression ──────────────────────────────────────────────────────
    @property
    def noise_suppression(self) -> bool:
        return self._q.value("noise_suppression", False, type=bool)

    @noise_suppression.setter
    def noise_suppression(self, v: bool) -> None:
        self._q.setValue("noise_suppression", v)

    # ── Keywords ───────────────────────────────────────────────────────────────
    @property
    def keywords(self) -> list[str]:
        """User-defined highlight keywords (comma-separated in storage)."""
        raw = self._q.value("keywords", "")
        return [k.strip() for k in raw.split(",") if k.strip()] if raw else []

    @keywords.setter
    def keywords(self, v: list[str]) -> None:
        self._q.setValue("keywords", ", ".join(v))

    # ── Auto-punctuation ───────────────────────────────────────────────────────
    @property
    def auto_punctuation(self) -> bool:
        return self._q.value("auto_punctuation", True, type=bool)

    @auto_punctuation.setter
    def auto_punctuation(self, v: bool) -> None:
        self._q.setValue("auto_punctuation", v)

    @property
    def speaker_diarization(self) -> bool:
        return self._q.value("speaker_diarization", False, type=bool)

    @speaker_diarization.setter
    def speaker_diarization(self, v: bool) -> None:
        self._q.setValue("speaker_diarization", v)

    # ── Output directory ───────────────────────────────────────────────────────
    @property
    def output_dir(self) -> Path:
        default = str(Path.home() / "MeetingTranscripts")
        return Path(self._q.value("output_dir", default))

    @output_dir.setter
    def output_dir(self, v: Path) -> None:
        self._q.setValue("output_dir", str(v))

    # ── Window geometry ────────────────────────────────────────────────────────
    @property
    def geometry(self) -> bytes | None:
        v = self._q.value("geometry")
        return bytes(v) if v else None

    @geometry.setter
    def geometry(self, v: bytes) -> None:
        self._q.setValue("geometry", v)

    # ── Language ───────────────────────────────────────────────────────────────
    @property
    def language(self) -> str:
        return self._q.value("language", "Auto-detect")

    @language.setter
    def language(self, v: str) -> None:
        self._q.setValue("language", v)

    # ── Obsidian ───────────────────────────────────────────────────────────────
    @property
    def obsidian_vault(self) -> Path | None:
        v = self._q.value("obsidian_vault", "")
        return Path(v) if v else None

    @obsidian_vault.setter
    def obsidian_vault(self, v: Path | None) -> None:
        self._q.setValue("obsidian_vault", str(v) if v else "")

    @property
    def obsidian_enabled(self) -> bool:
        return self._q.value("obsidian_enabled", False, type=bool)

    @obsidian_enabled.setter
    def obsidian_enabled(self, v: bool) -> None:
        self._q.setValue("obsidian_enabled", v)

    @property
    def obsidian_wikilinks(self) -> bool:
        return self._q.value("obsidian_wikilinks", True, type=bool)

    @obsidian_wikilinks.setter
    def obsidian_wikilinks(self, v: bool) -> None:
        self._q.setValue("obsidian_wikilinks", v)

    # ── Auto-update ────────────────────────────────────────────────────────────
    @property
    def last_update_check(self) -> str:
        """ISO date of last GitHub release check."""
        return self._q.value("last_update_check", "")

    @last_update_check.setter
    def last_update_check(self, v: str) -> None:
        self._q.setValue("last_update_check", v)

    @property
    def skipped_version(self) -> str:
        """Version the user chose to skip."""
        return self._q.value("skipped_version", "")

    @skipped_version.setter
    def skipped_version(self, v: str) -> None:
        self._q.setValue("skipped_version", v)

    def sync(self) -> None:
        self._q.sync()

    def export_json(self) -> dict:
        """Export all settings as a plain dict for backup."""
        keys = self._q.allKeys()
        return {k: self._q.value(k) for k in keys}

    def import_json(self, data: dict) -> None:
        """Restore settings from a previously exported dict."""
        for k, v in data.items():
            self._q.setValue(k, v)
        self._q.sync()

    def reset_defaults(self) -> None:
        """Wipe all stored settings back to defaults."""
        self._q.clear()
        self._q.sync()
