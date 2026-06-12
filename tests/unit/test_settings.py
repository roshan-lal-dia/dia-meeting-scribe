"""Tests for meet_scribe.settings.AppSettings.

Uses an isolated IniFormat QSettings in a tmp_path so tests never
touch the real Windows registry or ~/.config directory.
"""
from __future__ import annotations

from pathlib import Path

import pytest

try:
    from PySide6.QtCore import QSettings

    from meet_scribe.settings import AppSettings
except ImportError:
    pytest.skip("PySide6 not installed", allow_module_level=True)


@pytest.fixture()
def settings(tmp_path: Path) -> AppSettings:
    """AppSettings backed by a fresh temp INI file (no registry writes)."""
    ini = str(tmp_path / "test_settings.ini")
    s = AppSettings.__new__(AppSettings)
    s._q = QSettings(ini, QSettings.Format.IniFormat)
    return s


class TestDefaults:
    def test_model_default(self, settings: AppSettings) -> None:
        assert settings.model == "base.en"

    def test_capture_mode_default(self, settings: AppSettings) -> None:
        assert settings.capture_mode == "System audio only"

    def test_output_dir_default_is_path(self, settings: AppSettings) -> None:
        assert isinstance(settings.output_dir, Path)

    def test_language_default(self, settings: AppSettings) -> None:
        assert settings.language == "Auto-detect"

    def test_obsidian_vault_default_none(self, settings: AppSettings) -> None:
        assert settings.obsidian_vault is None

    def test_obsidian_enabled_default_false(self, settings: AppSettings) -> None:
        assert settings.obsidian_enabled is False

    def test_obsidian_wikilinks_default_true(self, settings: AppSettings) -> None:
        assert settings.obsidian_wikilinks is True

    def test_geometry_default_none(self, settings: AppSettings) -> None:
        assert settings.geometry is None


class TestPersistence:
    def test_model_roundtrip(self, settings: AppSettings) -> None:
        settings.model = "large-v3"
        assert settings.model == "large-v3"

    def test_capture_mode_roundtrip(self, settings: AppSettings) -> None:
        settings.capture_mode = "Microphone only"
        assert settings.capture_mode == "Microphone only"

    def test_output_dir_roundtrip(self, settings: AppSettings, tmp_path: Path) -> None:
        settings.output_dir = tmp_path
        assert settings.output_dir == tmp_path

    def test_language_roundtrip(self, settings: AppSettings) -> None:
        settings.language = "Arabic"
        assert settings.language == "Arabic"

    def test_obsidian_vault_roundtrip(self, settings: AppSettings, tmp_path: Path) -> None:
        settings.obsidian_vault = tmp_path
        assert settings.obsidian_vault == tmp_path

    def test_obsidian_vault_clear(self, settings: AppSettings, tmp_path: Path) -> None:
        settings.obsidian_vault = tmp_path
        settings.obsidian_vault = None
        assert settings.obsidian_vault is None

    def test_obsidian_enabled_roundtrip(self, settings: AppSettings) -> None:
        settings.obsidian_enabled = True
        assert settings.obsidian_enabled is True

    def test_obsidian_wikilinks_roundtrip(self, settings: AppSettings) -> None:
        settings.obsidian_wikilinks = False
        assert settings.obsidian_wikilinks is False
