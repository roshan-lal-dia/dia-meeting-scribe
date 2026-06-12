"""Obsidian vault export writer.

Produces Obsidian-flavoured Markdown with:
  - YAML frontmatter  (Dataview / Properties panel compatible)
  - Transcript table  (time · speaker · text)
  - Auto-wikilinks    (proper nouns repeated >=2x get [[wrapped]])
  - Scaffold sections (Summary, Action Items, Notes) for the user to fill

Folder layout: <vault>/Meetings/YYYY-MM/meeting-YYYY-MM-DD-HH-MM.md

References:
  dannb.org/blog/2023/obsidian-meeting-note-template/
  github.com/pattynextdoor/meetingmind
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from pathlib import Path

from .base import ExportWriter, SessionData

log = logging.getLogger(__name__)

# -- Wikilink detection -------------------------------------------------------

_PROPER_RE = re.compile(r"\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})*)\b")

_STOPWORDS: frozenset[str] = frozenset(
    {
        "The", "This", "That", "These", "Those", "Here", "There",
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
        "January", "February", "March", "April", "June", "July", "August",
        "September", "October", "November", "December",
        "Thanks", "Thank", "Hello", "Good", "Okay", "Sorry",
        "Yes", "No", "Well", "Now", "Just", "Also", "And", "But",
        "Meet", "Scribe",  # our own app name shouldn't become a wikilink
    }
)


def detect_wikilinks(
    lines: list[tuple[str, str, str]],
    min_count: int = 2,
) -> set[str]:
    """Return proper-noun phrases that appear >= min_count times across all lines."""
    all_text = " ".join(txt for _, _, txt in lines)
    counts = Counter(
        m for m in _PROPER_RE.findall(all_text) if m not in _STOPWORDS and len(m) > 3
    )
    return {phrase for phrase, cnt in counts.items() if cnt >= min_count}


def apply_wikilinks(text: str, wikilink_set: set[str]) -> str:
    """Wrap each phrase in *wikilink_set* with [[ ]] in *text*.

    Phrases are applied longest-first so 'John Smith' wins over 'John'.
    A negative lookbehind (?<!\\[) prevents re-wrapping inside existing [[ ]].
    """
    for phrase in sorted(wikilink_set, key=len, reverse=True):
        # (?<![) prevents matching a phrase already inside [[ ]]
        text = re.sub(rf"(?<!\[)\b{re.escape(phrase)}\b(?!\])", f"[[{phrase}]]", text)
    return text


# -- Markdown rendering -------------------------------------------------------


def _frontmatter(data: SessionData) -> str:
    participants_yaml = "\n".join(f"  - {p}" for p in data.participants) or "  []"
    return (
        "---\n"
        f'title: "Meeting {data.started_at.strftime("%Y-%m-%d %H:%M")}"\n'
        f"date: {data.started_at.strftime('%Y-%m-%d')}\n"
        f"time: \"{data.started_at.strftime('%H:%M')}\"\n"
        "tags:\n  - meeting\n  - transcript\n"
        "type: meeting\n"
        f'duration: "{data.duration_str}"\n'
        f"model: {data.model}\n"
        f'device: "{data.device_name}"\n'
        f"language: {data.language}\n"
        f"participants:\n{participants_yaml}\n"
        f"created: {data.started_at.isoformat(timespec='seconds')}\n"
        "---\n"
    )


def _transcript_table(
    lines: list[tuple[str, str, str]],
    wikilink_set: set[str],
) -> str:
    rows = [
        f"| {ts} | {'Them' if src == 'them' else 'You'} "
        f"| {apply_wikilinks(txt, wikilink_set).replace('|', chr(92) + '|')} |"
        for ts, src, txt in lines
        if src != "info"
    ]
    if not rows:
        return "_No speech detected._\n"
    header = "| Time | Speaker | Transcript |\n|------|---------|------------|\n"
    return header + "\n".join(rows) + "\n"


def render(data: SessionData, *, auto_wikilinks: bool = True) -> str:
    """Return the complete Obsidian markdown string for *data*."""
    wikilinks = detect_wikilinks(data.lines) if auto_wikilinks else set()
    pax_links = "  ".join(f"[[{p.title()}]]" for p in data.participants) or "_unknown_"
    wikilink_note = (
        "\n> **Auto-linked topics:** " + ", ".join(f"[[{w}]]" for w in sorted(wikilinks)) + "\n"
        if wikilinks
        else ""
    )
    heading = data.started_at.strftime("%A, %B %d %Y -- %H:%M")

    return (
        f"{_frontmatter(data)}\n"
        f"# {heading}\n\n"
        f"**Participants:** {pax_links}\n"
        f"**Duration:** {data.duration_str}  .  "
        f"**Model:** {data.model}  .  **Device:** {data.device_name}\n"
        f"{wikilink_note}\n"
        "---\n\n"
        "## Notes\n\n_Add your notes here._\n\n"
        "## Action Items\n\n- [ ] \n\n"
        f"## Transcript\n\n{_transcript_table(data.lines, wikilinks)}\n"
        "---\n"
        f"_Transcribed locally by Meet-Scribe . {data.model} on {data.device_name}_\n"
    )


# -- Writer -------------------------------------------------------------------


class ObsidianWriter(ExportWriter):
    """Writes Obsidian-flavoured Markdown to a vault folder."""

    def __init__(self, auto_wikilinks: bool = True) -> None:
        self.auto_wikilinks = auto_wikilinks

    def default_filename(self, data: SessionData) -> str:
        return f"meeting-{data.started_at.strftime('%Y-%m-%d-%H-%M')}.md"

    def vault_path(self, vault_dir: Path, data: SessionData) -> Path:
        """Return <vault>/Meetings/YYYY-MM/<filename>."""
        month_dir = vault_dir / "Meetings" / data.started_at.strftime("%Y-%m")
        return month_dir / self.default_filename(data)

    def write(self, data: SessionData, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = render(data, auto_wikilinks=self.auto_wikilinks)
        path.write_text(content, encoding="utf-8")
        log.info("Obsidian note written to %s", path)
        return path

    def write_to_vault(self, data: SessionData, vault_dir: Path) -> Path:
        """Convenience: resolve path from vault root then write."""
        return self.write(data, self.vault_path(vault_dir, data))
