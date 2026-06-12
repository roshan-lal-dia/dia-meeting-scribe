"""Persistent app settings backed by QSettings (registry on Windows)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings

_ORG = "MeetingScribe"
_APP = "MeetingScribe"


class AppSettings:
    def __init__(self):
        self._q = QSettings(_ORG, _APP)

    # ── Model ──────────────────────────────────────────────────────────────
    @property
    def model(self) -> str:
        return self._q.value("model", "base.en")

    @model.setter
    def model(self, v: str):
        self._q.setValue("model", v)

    # ── Capture mode ────────────────────────────────────────────────────────
    @property
    def capture_mode(self) -> str:
        return self._q.value("capture_mode", "System audio only")

    @capture_mode.setter
    def capture_mode(self, v: str):
        self._q.setValue("capture_mode", v)

    # ── Output directory ────────────────────────────────────────────────────
    @property
    def output_dir(self) -> Path:
        default = str(Path.home() / "MeetingTranscripts")
        return Path(self._q.value("output_dir", default))

    @output_dir.setter
    def output_dir(self, v: Path):
        self._q.setValue("output_dir", str(v))

    # ── Window geometry ─────────────────────────────────────────────────────
    @property
    def geometry(self) -> bytes | None:
        v = self._q.value("geometry")
        return bytes(v) if v else None

    @geometry.setter
    def geometry(self, v: bytes):
        self._q.setValue("geometry", v)

    # ── Language ─────────────────────────────────────────────────────────────
    @property
    def language(self) -> str:
        return self._q.value("language", "Auto-detect")

    @language.setter
    def language(self, v: str):
        self._q.setValue("language", v)

    # ── Obsidian vault ────────────────────────────────────────────────────────
    @property
    def obsidian_vault(self) -> Path | None:
        v = self._q.value("obsidian_vault", "")
        return Path(v) if v else None

    @obsidian_vault.setter
    def obsidian_vault(self, v: Path | None):
        self._q.setValue("obsidian_vault", str(v) if v else "")

    @property
    def obsidian_enabled(self) -> bool:
        return self._q.value("obsidian_enabled", False, type=bool)

    @obsidian_enabled.setter
    def obsidian_enabled(self, v: bool):
        self._q.setValue("obsidian_enabled", v)

    @property
    def obsidian_wikilinks(self) -> bool:
        """Auto-detect proper nouns and turn them into [[wikilinks]]."""
        return self._q.value("obsidian_wikilinks", True, type=bool)

    @obsidian_wikilinks.setter
    def obsidian_wikilinks(self, v: bool):
        self._q.setValue("obsidian_wikilinks", v)

    def sync(self):
        self._q.sync()
