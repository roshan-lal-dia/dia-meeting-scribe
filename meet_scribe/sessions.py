"""Session persistence - save/load past recording sessions as JSON.

Sessions are stored in:
  Windows: %LOCALAPPDATA%\\MeetScribe\\sessions\\
  Other:   ~/.local/share/MeetScribe/sessions/

Each session is a single JSON file named by its start timestamp.
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import pathlib

log = logging.getLogger(__name__)


def _sessions_dir() -> pathlib.Path:
    if os.name == "nt":
        base = pathlib.Path(os.environ.get("LOCALAPPDATA", pathlib.Path.home()))
    else:
        base = pathlib.Path.home() / ".local" / "share"
    d = base / "MeetScribe" / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def session_filename(started_at: datetime.datetime) -> str:
    return started_at.strftime("session_%Y%m%d_%H%M%S.json")


def save_session(data: SessionData) -> pathlib.Path:  # noqa: F821
    """Serialise *data* and write to the sessions directory. Returns the path."""
    from .export.base import SessionData  # noqa: F401 (import for type check only)
    payload = {
        "version":     1,
        "started_at":  data.started_at.isoformat(),
        "ended_at":    data.ended_at.isoformat(),
        "model":       data.model,
        "device_name": data.device_name,
        "language":    data.language,
        "capture_mode": data.capture_mode,
        "lines":       data.lines,
    }
    p = _sessions_dir() / session_filename(data.started_at)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("session saved -> %s", p)
    return p


def list_sessions() -> list[dict]:
    """Return a list of session dicts (newest first), or [] on error."""
    sessions = []
    for f in sorted(_sessions_dir().glob("session_*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_path"] = str(f)
            sessions.append(data)
        except Exception as exc:
            log.warning("skipping corrupt session %s: %s", f.name, exc)
    return sessions


def load_session(path: str | pathlib.Path) -> SessionData:  # noqa: F821
    """Load a session from *path* and return a ``SessionData`` instance."""
    from .export.base import SessionData
    raw = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return SessionData(
        started_at   = datetime.datetime.fromisoformat(raw["started_at"]),
        ended_at     = datetime.datetime.fromisoformat(raw["ended_at"]),
        model        = raw.get("model", ""),
        device_name  = raw.get("device_name", ""),
        language     = raw.get("language", ""),
        capture_mode = raw.get("capture_mode", "system"),
        lines        = [tuple(ln) for ln in raw.get("lines", [])],
    )


def delete_session(path: str | pathlib.Path) -> None:
    pathlib.Path(path).unlink(missing_ok=True)
    log.info("session deleted: %s", path)
