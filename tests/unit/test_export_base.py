"""Tests for meet_scribe.export.base.SessionData."""
from __future__ import annotations

import datetime

from meet_scribe.export.base import SessionData


class TestSessionDataDuration:
    def test_duration_seconds(self) -> None:
        s = SessionData(
            started_at=datetime.datetime(2026, 1, 1, 10, 0, 0),
            ended_at=datetime.datetime(2026, 1, 1, 10, 0, 45),
            model="tiny.en", device_name="CPU", language="English", capture_mode="system",
        )
        assert s.duration_str == "45s"

    def test_duration_minutes(self) -> None:
        s = SessionData(
            started_at=datetime.datetime(2026, 1, 1, 10, 0, 0),
            ended_at=datetime.datetime(2026, 1, 1, 10, 3, 12),
            model="tiny.en", device_name="CPU", language="English", capture_mode="system",
        )
        assert s.duration_str == "3m 12s"

    def test_duration_hours(self) -> None:
        s = SessionData(
            started_at=datetime.datetime(2026, 1, 1, 9, 0, 0),
            ended_at=datetime.datetime(2026, 1, 1, 10, 5, 30),
            model="tiny.en", device_name="CPU", language="English", capture_mode="system",
        )
        assert s.duration_str == "1h 5m 30s"


class TestSessionDataLines:
    def test_speech_lines_excludes_info(self, sample_session: SessionData) -> None:
        info_lines = [ln for ln in sample_session.lines if ln[1] == "info"]
        speech = sample_session.speech_lines
        assert len(speech) == len(sample_session.lines) - len(info_lines)
        assert all(src != "info" for _, src, _ in speech)

    def test_participants_order(self, sample_session: SessionData) -> None:
        pax = sample_session.participants
        # "them" appears first in the fixture
        assert pax[0] == "them"
        assert "you" in pax

    def test_empty_session_no_participants(self, empty_session: SessionData) -> None:
        assert empty_session.participants == []

    def test_empty_session_no_speech(self, empty_session: SessionData) -> None:
        assert empty_session.speech_lines == []
