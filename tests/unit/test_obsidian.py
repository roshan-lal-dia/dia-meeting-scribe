"""Tests for meet_scribe.export.obsidian."""
from __future__ import annotations

from pathlib import Path

from meet_scribe.export.base import SessionData
from meet_scribe.export.obsidian import (
    ObsidianWriter,
    apply_wikilinks,
    detect_wikilinks,
    render,
)

# ── Wikilink detection ────────────────────────────────────────────────────────

class TestDetectWikilinks:
    def test_repeated_proper_noun_detected(self, sample_session: SessionData) -> None:
        wikilinks = detect_wikilinks(sample_session.lines, min_count=2)
        assert "Kubernetes" in wikilinks

    def test_single_occurrence_not_detected(self) -> None:
        lines = [("ts", "them", "I met John Smith today.")]
        wikilinks = detect_wikilinks(lines, min_count=2)
        assert "John Smith" not in wikilinks

    def test_stopwords_excluded(self) -> None:
        lines = [
            ("ts", "them", "Thanks for the update."),
            ("ts", "you",  "Thanks indeed."),
        ]
        wikilinks = detect_wikilinks(lines, min_count=2)
        assert "Thanks" not in wikilinks

    def test_returns_set(self) -> None:
        lines = [("ts", "them", "Python Python Python")]
        result = detect_wikilinks(lines, min_count=2)
        assert isinstance(result, set)

    def test_min_count_respected(self) -> None:
        lines = [
            ("ts", "them", "Kubernetes is great"),
            ("ts", "you",  "Kubernetes is stable"),
            ("ts", "them", "Kubernetes migration done"),
        ]
        assert "Kubernetes" in detect_wikilinks(lines, min_count=3)
        assert "Kubernetes" not in detect_wikilinks(lines, min_count=4)


class TestApplyWikilinks:
    def test_wraps_matching_phrase(self) -> None:
        result = apply_wikilinks("Kubernetes is ready", {"Kubernetes"})
        assert "[[Kubernetes]]" in result

    def test_no_match_unchanged(self) -> None:
        result = apply_wikilinks("hello world", {"Kubernetes"})
        assert result == "hello world"

    def test_longer_phrase_wins(self) -> None:
        """Longer phrases should be matched before shorter sub-phrases."""
        text = "John Smith came to visit"
        result = apply_wikilinks(text, {"John Smith", "John"})
        assert "[[John Smith]]" in result
        # "John" should not appear as a separate wikilink inside [[John Smith]]
        assert "[[John]] Smith" not in result

    def test_multiple_occurrences_all_wrapped(self) -> None:
        text = "Python is great. Python is fast."
        result = apply_wikilinks(text, {"Python"})
        assert result.count("[[Python]]") == 2


# ── Render ────────────────────────────────────────────────────────────────────

class TestRender:
    def test_contains_yaml_frontmatter(self, sample_session: SessionData) -> None:
        md = render(sample_session)
        assert md.startswith("---")
        assert "type: meeting" in md

    def test_frontmatter_contains_model(self, sample_session: SessionData) -> None:
        assert "small.en" in render(sample_session)

    def test_frontmatter_contains_date(self, sample_session: SessionData) -> None:
        assert "2026-06-11" in render(sample_session)

    def test_transcript_table_present(self, sample_session: SessionData) -> None:
        md = render(sample_session)
        assert "| Time | Speaker | Transcript |" in md

    def test_action_items_section_present(self, sample_session: SessionData) -> None:
        assert "## Action Items" in render(sample_session)

    def test_notes_section_present(self, sample_session: SessionData) -> None:
        assert "## Notes" in render(sample_session)

    def test_info_lines_excluded_from_table(self, sample_session: SessionData) -> None:
        md = render(sample_session)
        # The info status line should NOT appear as a table row
        assert "✅ loaded" not in md.split("## Transcript")[1]

    def test_wikilinks_applied_when_enabled(self, sample_session: SessionData) -> None:
        md = render(sample_session, auto_wikilinks=True)
        assert "[[Kubernetes]]" in md

    def test_wikilinks_disabled(self, sample_session: SessionData) -> None:
        md = render(sample_session, auto_wikilinks=False)
        assert "[[Kubernetes]]" not in md

    def test_empty_session_renders_no_speech(self, empty_session: SessionData) -> None:
        md = render(empty_session)
        assert "_No speech detected._" in md


# ── ObsidianWriter ────────────────────────────────────────────────────────────

class TestObsidianWriter:
    def test_default_filename_contains_date(self, sample_session: SessionData) -> None:
        w = ObsidianWriter()
        assert "2026-06-11" in w.default_filename(sample_session)

    def test_default_filename_ends_with_md(self, sample_session: SessionData) -> None:
        w = ObsidianWriter()
        assert w.default_filename(sample_session).endswith(".md")

    def test_vault_path_structure(
        self, sample_session: SessionData, tmp_path: Path
    ) -> None:
        w = ObsidianWriter()
        p = w.vault_path(tmp_path, sample_session)
        assert p.parent.parent.name == "Meetings"
        assert p.parent.name == "2026-06"

    def test_write_creates_file(
        self, sample_session: SessionData, tmp_path: Path
    ) -> None:
        w = ObsidianWriter()
        out = w.write_to_vault(sample_session, tmp_path)
        assert out.exists()
        assert out.suffix == ".md"

    def test_written_file_is_utf8(
        self, sample_session: SessionData, tmp_path: Path
    ) -> None:
        w = ObsidianWriter()
        out = w.write_to_vault(sample_session, tmp_path)
        text = out.read_text(encoding="utf-8")
        assert "---" in text  # frontmatter delimiters present
