"""SRT and WebVTT subtitle export for Meet-Scribe."""
from __future__ import annotations

import datetime
from pathlib import Path

from .base import SessionData


def _ts_srt(seconds: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm"""
    h  = int(seconds // 3600)
    m  = int((seconds % 3600) // 60)
    s  = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _ts_vtt(seconds: float) -> str:
    """Format seconds as WebVTT timestamp: HH:MM:SS.mmm"""
    return _ts_srt(seconds).replace(",", ".")


def write_srt(data: SessionData, path: Path) -> Path:
    """Write an SRT subtitle file from session transcript lines.

    Each transcript line becomes a ~4-second subtitle cue.  Start time is
    estimated from the ``HH:MM:SS`` timestamp embedded in each line; duration
    defaults to 4 s (or until the next cue starts).

    Returns the path written.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    cues = _build_cues(data)
    with open(path, "w", encoding="utf-8") as fh:
        for i, (start, end, text) in enumerate(cues, 1):
            fh.write(f"{i}\n")
            fh.write(f"{_ts_srt(start)} --> {_ts_srt(end)}\n")
            fh.write(f"{text}\n\n")
    return path


def write_vtt(data: SessionData, path: Path) -> Path:
    """Write a WebVTT subtitle file from session transcript lines."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    cues = _build_cues(data)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("WEBVTT\n\n")
        for start, end, text in cues:
            fh.write(f"{_ts_vtt(start)} --> {_ts_vtt(end)}\n")
            fh.write(f"{text}\n\n")
    return path


def _build_cues(
    data: SessionData,
    default_duration: float = 4.0,
) -> list[tuple[float, float, str]]:
    """Convert raw lines → list of (start_sec, end_sec, text) tuples."""
    cues: list[tuple[float, float, str]] = []
    session_start: datetime.datetime = data.started_at

    for ts_str, source, text in data.lines:
        try:
            h, m, s = (int(x) for x in ts_str.split(":"))
            abs_time = session_start.replace(hour=h, minute=m, second=s, microsecond=0)
            offset = (abs_time - session_start).total_seconds()
            if offset < 0:               # crossed midnight
                offset += 86400
        except (ValueError, AttributeError):
            offset = len(cues) * default_duration

        speaker = {"them": "THEM", "you": "YOU"}.get(source, "")
        label   = f"[{speaker}] {text}" if speaker else text
        cues.append((offset, offset + default_duration, label))

    # Clamp each end time to the start of the next cue
    for i in range(len(cues) - 1):
        start_next = cues[i + 1][0]
        start, end, text = cues[i]
        cues[i] = (start, min(end, start_next - 0.1), text)

    return cues
