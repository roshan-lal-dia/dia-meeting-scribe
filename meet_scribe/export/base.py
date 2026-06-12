"""Abstract base class for all export writers."""
from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SessionData:
    """Everything the export layer needs about a recording session.

    Decouples the export code from Qt/window state — can be constructed
    and tested independently of the UI.
    """

    started_at:   datetime.datetime
    ended_at:     datetime.datetime
    model:        str
    device_name:  str
    language:     str                          # e.g. "Arabic" or "Auto-detect (AR)"
    capture_mode: str                          # "system" | "mic" | "both"
    lines: list[tuple[str, str, str]] = field(default_factory=list)
    # Each entry: (timestamp_str, source_tag, text)
    # source_tag: "them" | "you" | "info"

    @property
    def speech_lines(self) -> list[tuple[str, str, str]]:
        """Lines that are actual speech (exclude 'info' entries)."""
        return [(ts, src, txt) for ts, src, txt in self.lines if src != "info"]

    @property
    def duration(self) -> datetime.timedelta:
        return self.ended_at - self.started_at

    @property
    def duration_str(self) -> str:
        secs = int(self.duration.total_seconds())
        m, s = divmod(secs, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}h {m}m {s}s"
        return f"{m}m {s}s" if m else f"{s}s"

    @property
    def participants(self) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for _, src, _ in self.lines:
            if src not in ("info",) and src not in seen:
                seen.add(src)
                result.append(src)
        return result


class ExportWriter(ABC):
    """Base class for all export writers.

    Subclasses implement ``write()`` and ``default_filename()``.
    All writes are expected to be non-blocking (use threading if needed).
    """

    @abstractmethod
    def write(self, data: SessionData, path: Path) -> Path:
        """Write *data* to *path*.  Returns the resolved output path."""

    @abstractmethod
    def default_filename(self, data: SessionData) -> str:
        """Suggest a filename (no directory) for the given session."""
