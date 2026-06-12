"""Tests for summarizer, sessions, diarize, onboarding modules."""
from __future__ import annotations

import pytest

import datetime

from meet_scribe.export.base import SessionData


def _sample_session() -> SessionData:
    return SessionData(
        started_at=datetime.datetime(2026, 1, 15, 9, 0, 0),
        ended_at=datetime.datetime(2026, 1, 15, 9, 30, 0),
        model="base.en",
        device_name="CPU",
        language="en",
        capture_mode="system",
        lines=[
            ("09:00:01", "them", "Good morning everyone."),
            ("09:00:10", "you", "Hi, thanks for joining."),
            ("09:01:00", "them", "Shall we start with the agenda?"),
        ],
    )


# ── sessions.py ──────────────────────────────────────────────────────────────

class TestSessions:
    def test_save_and_load(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        import meet_scribe.sessions as mod
        # Patch _sessions_dir to use tmp
        monkeypatch.setattr(mod, "_sessions_dir", lambda: tmp_path)

        data = _sample_session()
        saved = mod.save_session(data)
        assert saved.exists()

        loaded = mod.load_session(saved)
        assert loaded.started_at == data.started_at
        assert loaded.ended_at == data.ended_at
        assert len(loaded.lines) == 3
        assert loaded.lines[0] == ("09:00:01", "them", "Good morning everyone.")

    def test_list_sessions(self, tmp_path, monkeypatch):
        import meet_scribe.sessions as mod
        monkeypatch.setattr(mod, "_sessions_dir", lambda: tmp_path)

        data = _sample_session()
        mod.save_session(data)
        sessions = mod.list_sessions()
        assert len(sessions) == 1
        assert "_path" in sessions[0]
        assert sessions[0]["model"] == "base.en"

    def test_delete_session(self, tmp_path, monkeypatch):
        import meet_scribe.sessions as mod
        monkeypatch.setattr(mod, "_sessions_dir", lambda: tmp_path)

        data = _sample_session()
        path = mod.save_session(data)
        assert path.exists()
        mod.delete_session(path)
        assert not path.exists()

    def test_list_sessions_empty(self, tmp_path, monkeypatch):
        import meet_scribe.sessions as mod
        monkeypatch.setattr(mod, "_sessions_dir", lambda: tmp_path)
        assert mod.list_sessions() == []

    def test_session_filename_format(self):
        from meet_scribe.sessions import session_filename
        dt = datetime.datetime(2026, 3, 7, 14, 5, 9)
        assert session_filename(dt) == "session_20260307_140509.json"

    def test_corrupt_session_skipped(self, tmp_path, monkeypatch):
        import meet_scribe.sessions as mod
        monkeypatch.setattr(mod, "_sessions_dir", lambda: tmp_path)
        (tmp_path / "session_20260101_000000.json").write_text("not json")
        result = mod.list_sessions()
        assert result == []


# ── summarizer.py ────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="requires PySide6 (Qt not available in sandbox)")
class TestSummarizer:
    def test_build_prompt_contains_transcript(self):
        from meet_scribe.summarizer import _build_prompt
        data = _sample_session()
        prompt = _build_prompt(data)
        assert "Good morning everyone" in prompt
        assert "30m" in prompt

    def test_build_prompt_empty_speech(self):
        from meet_scribe.summarizer import _build_prompt
        data = SessionData(
            started_at=datetime.datetime(2026, 1, 1, 9, 0),
            ended_at=datetime.datetime(2026, 1, 1, 9, 5),
            model="base.en", device_name="CPU",
            language="en", capture_mode="system",
            lines=[("09:00:00", "info", "Started")],
        )
        prompt = _build_prompt(data)
        assert "Transcript" in prompt

    def test_worker_emits_error_when_no_lines(self):
        pass  # requires Qt event loop


# ── diarize.py ───────────────────────────────────────────────────────────────

class TestDiarize:
    def test_label_all_fallback(self):
        from meet_scribe.diarize import _label_all
        segs = [{"start": 0.0, "end": 1.0, "text": "Hello"}]
        result = _label_all(segs, "SPEAKER_00")
        assert result[0]["speaker"] == "SPEAKER_00"

    def test_diarize_no_token_falls_back(self, monkeypatch):
        """Without HUGGINGFACE_TOKEN, diarize_segments labels everything SPEAKER_00."""
        import numpy as np

        from meet_scribe.diarize import diarize_segments
        monkeypatch.delenv("HUGGINGFACE_TOKEN", raising=False)
        audio = np.zeros(16000, dtype="float32")
        segs  = [{"start": 0.0, "end": 1.0, "text": "Test"}]
        result = diarize_segments(audio, 16000, segs)
        assert all(s["speaker"] == "SPEAKER_00" for s in result)

    def test_diarize_empty_segments(self, monkeypatch):
        import numpy as np

        from meet_scribe.diarize import diarize_segments
        monkeypatch.delenv("HUGGINGFACE_TOKEN", raising=False)
        audio = np.zeros(16000, dtype="float32")
        result = diarize_segments(audio, 16000, [])
        assert result == []

    def test_is_available_no_pyannote(self, monkeypatch):
        """is_available() returns False when pyannote is not installed."""
        import sys
        # Temporarily hide pyannote from sys.modules
        saved = sys.modules.pop("pyannote", None)
        saved_audio = sys.modules.pop("pyannote.audio", None)
        try:
            import importlib

            import meet_scribe.diarize as mod
            importlib.reload(mod)
            monkeypatch.setenv("HUGGINGFACE_TOKEN", "tok")
            # is_available tries to import pyannote.audio; ImportError -> False
            result = mod.is_available()
            assert result is False
        finally:
            if saved is not None:
                sys.modules["pyannote"] = saved
            if saved_audio is not None:
                sys.modules["pyannote.audio"] = saved_audio

    def test_install_instructions(self):
        from meet_scribe.diarize import install_instructions
        text = install_instructions()
        assert "pip install pyannote.audio" in text
        assert "HUGGINGFACE_TOKEN" in text
