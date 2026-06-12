"""Shared pytest fixtures for Meet-Scribe tests."""
from __future__ import annotations

import datetime

import pytest

from meet_scribe.export.base import SessionData


@pytest.fixture
def sample_session() -> SessionData:
    """A minimal SessionData fixture for export tests."""
    return SessionData(
        started_at=datetime.datetime(2026, 6, 11, 15, 30, 0),
        ended_at=datetime.datetime(2026, 6, 11, 15, 33, 12),
        model="small.en",
        device_name="NVIDIA GeForce RTX 3050 Laptop GPU",
        language="English",
        capture_mode="system",
        lines=[
            ("15:30:01", "info", "✅ loaded · small.en on NVIDIA GPU · lang=EN"),
            ("15:30:07", "them", "Good morning everyone, let's start the standup."),
            ("15:30:15", "you",  "Sure, I'll go first. I finished the Kubernetes migration."),
            ("15:30:42", "them", "Great. John mentioned the Kubernetes issue yesterday."),
            ("15:31:05", "you",  "Yes, Kubernetes is fully stable now."),
            ("15:31:30", "them", "Perfect. Any blockers for the Q4 Review?"),
            ("15:32:00", "you",  "No blockers. Q4 Review prep is on track."),
        ],
    )


@pytest.fixture
def empty_session() -> SessionData:
    """A session with no speech lines."""
    return SessionData(
        started_at=datetime.datetime(2026, 6, 11, 9, 0, 0),
        ended_at=datetime.datetime(2026, 6, 11, 9, 0, 5),
        model="tiny.en",
        device_name="CPU",
        language="Auto-detect",
        capture_mode="system",
        lines=[
            ("09:00:00", "info", "✅ loaded · tiny.en on CPU"),
        ],
    )
