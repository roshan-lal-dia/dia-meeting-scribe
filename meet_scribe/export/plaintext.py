"""Plain-text (.txt) export writer."""
from __future__ import annotations

import logging
from pathlib import Path

from .base import ExportWriter, SessionData

log = logging.getLogger(__name__)

_DIVIDER = "=" * 62


class PlaintextWriter(ExportWriter):
    """Writes a human-readable .txt transcript."""

    def default_filename(self, data: SessionData) -> str:
        return f"meeting_{data.started_at.strftime('%Y-%m-%d_%H-%M-%S')}.txt"

    def write(self, data: SessionData, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = self._render(data)
        path.write_text(content, encoding="utf-8")
        log.info("plaintext transcript → %s (%d lines)", path, len(data.speech_lines))
        return path

    def _render(self, data: SessionData) -> str:
        header = "\n".join(
            [
                "Meet-Scribe Transcript",
                f"Date     : {data.started_at.strftime('%A, %B %d %Y — %H:%M')}",
                f"Duration : {data.duration_str}",
                f"Model    : {data.model}  |  Device: {data.device_name}",
                f"Language : {data.language}",
                _DIVIDER,
                "",
            ]
        )
        body = "\n".join(
            f"[{ts}] {'🎧' if src == 'them' else '🎤'}  {txt}"
            for ts, src, txt in data.speech_lines
        )
        return header + body + "\n"
