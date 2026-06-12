"""Tests for meet_scribe.transcribe.perf.PerfStats."""
from __future__ import annotations

import pytest

from meet_scribe.transcribe.perf import PerfStats


class TestPerfStatsInitial:
    def test_no_data_rtf_is_zero(self) -> None:
        p = PerfStats()
        assert p.rtf == 0.0

    def test_no_data_latency_is_zero(self) -> None:
        p = PerfStats()
        assert p.avg_latency == 0.0

    def test_no_data_has_data_false(self) -> None:
        p = PerfStats()
        assert not p.has_data

    def test_initial_counters_zero(self) -> None:
        p = PerfStats()
        assert p.total_chunks == 0
        assert p.total_skipped == 0


class TestPerfStatsRecording:
    def test_single_chunk_rtf(self) -> None:
        p = PerfStats()
        p.record(inference_sec=0.5, audio_sec=5.0)
        assert p.rtf == pytest.approx(0.1)

    def test_single_chunk_latency(self) -> None:
        p = PerfStats()
        p.record(inference_sec=0.3, audio_sec=6.0)
        assert p.avg_latency == pytest.approx(0.3)

    def test_counter_increments(self) -> None:
        p = PerfStats()
        p.record(0.1, 1.0)
        p.record(0.2, 2.0)
        assert p.total_chunks == 2

    def test_has_data_after_record(self) -> None:
        p = PerfStats()
        p.record(0.1, 1.0)
        assert p.has_data

    def test_rtf_faster_than_realtime(self) -> None:
        """RTF < 1.0 means we're faster than real-time — ideal."""
        p = PerfStats()
        p.record(inference_sec=0.1, audio_sec=6.0)
        assert p.rtf < 1.0

    def test_rtf_slower_than_realtime(self) -> None:
        """RTF > 1.0 means inference is slower than real-time."""
        p = PerfStats()
        p.record(inference_sec=10.0, audio_sec=6.0)
        assert p.rtf > 1.0


class TestPerfStatsWindow:
    def test_rolling_window_caps_list_length(self) -> None:
        p = PerfStats(window=3)
        for _i in range(10):
            p.record(float(_i) * 0.1, 1.0)
        # Internal lists should not exceed window size
        assert len(p._latencies) <= 3
        assert len(p._chunk_dur) <= 3

    def test_total_chunks_unbounded(self) -> None:
        p = PerfStats(window=3)
        for _i in range(10):
            p.record(0.1, 1.0)
        assert p.total_chunks == 10  # counter never truncated

    def test_window_averages_recent_only(self) -> None:
        """After filling the window, old slow chunks should fall off."""
        p = PerfStats(window=2)
        p.record(inference_sec=100.0, audio_sec=1.0)   # very slow — will be evicted
        p.record(inference_sec=0.1, audio_sec=1.0)
        p.record(inference_sec=0.1, audio_sec=1.0)
        # Now only the two fast chunks should be in the window
        assert p.avg_latency == pytest.approx(0.1)


class TestPerfStatsSummary:
    def test_summary_contains_rtf(self) -> None:
        p = PerfStats()
        p.record(0.5, 5.0)
        s = p.summary()
        assert "RTF" in s

    def test_summary_contains_chunks(self) -> None:
        p = PerfStats()
        p.record(0.1, 1.0)
        p.record(0.1, 1.0)
        assert "2 chunks" in p.summary()

    def test_summary_contains_skipped(self) -> None:
        p = PerfStats()
        p.total_skipped = 5
        assert "5 skipped" in p.summary()
