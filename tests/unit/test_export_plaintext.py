"""Tests for meet_scribe.export.plaintext.PlaintextWriter."""
from __future__ import annotations

from pathlib import Path

import pytest

from meet_scribe.export.base import SessionData
from meet_scribe.export.plaintext import PlaintextWriter


@pytest.fixture
def writer() -> PlaintextWriter:
    return PlaintextWriter()


class TestDefaultFilename:
    def test_contains_date(self, writer: PlaintextWriter, sample_session: SessionData) -> None:
        fname = writer.default_filename(sample_session)
        assert "2026-06-11" in fname

    def test_ends_with_txt(self, writer: PlaintextWriter, sample_session: SessionData) -> None:
        assert writer.default_filename(sample_session).endswith(".txt")

    def test_no_directory_separator(
        self, writer: PlaintextWriter, sample_session: SessionData
    ) -> None:
        fname = writer.default_filename(sample_session)
        assert "/" not in fname and "\\" not in fname


class TestRender:
    def test_header_contains_model(
        self, writer: PlaintextWriter, sample_session: SessionData
    ) -> None:
        content = writer._render(sample_session)
        assert "small.en" in content

    def test_header_contains_device(
        self, writer: PlaintextWriter, sample_session: SessionData
    ) -> None:
        content = writer._render(sample_session)
        assert "RTX 3050" in content

    def test_speech_lines_present(
        self, writer: PlaintextWriter, sample_session: SessionData
    ) -> None:
        content = writer._render(sample_session)
        assert "Kubernetes migration" in content

    def test_info_lines_excluded(
        self, writer: PlaintextWriter, sample_session: SessionData
    ) -> None:
        content = writer._render(sample_session)
        # The "info" status line should not appear in the rendered body
        assert "✅ loaded" not in content

    def test_empty_session_renders(
        self, writer: PlaintextWriter, empty_session: SessionData
    ) -> None:
        content = writer._render(empty_session)
        assert "Meet-Scribe" in content


class TestWrite:
    def test_creates_file(
        self, writer: PlaintextWriter, sample_session: SessionData, tmp_path: Path
    ) -> None:
        out = writer.write(sample_session, tmp_path / "out.txt")
        assert out.exists()

    def test_creates_parent_dirs(
        self, writer: PlaintextWriter, sample_session: SessionData, tmp_path: Path
    ) -> None:
        deep = tmp_path / "a" / "b" / "c" / "out.txt"
        writer.write(sample_session, deep)
        assert deep.exists()

    def test_utf8_encoding(
        self, writer: PlaintextWriter, sample_session: SessionData, tmp_path: Path
    ) -> None:
        out = writer.write(sample_session, tmp_path / "out.txt")
        text = out.read_text(encoding="utf-8")
        assert "Meet-Scribe" in text
