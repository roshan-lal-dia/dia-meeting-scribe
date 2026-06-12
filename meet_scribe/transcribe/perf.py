"""Real-time performance statistics for transcription chunks.

Extracted from worker.py so it can be unit-tested without Qt or GPU.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PerfStats:
    """Rolling-window RTF and latency tracker.

    RTF (real-time factor) = inference_seconds / audio_seconds.
    RTF < 1.0 means we transcribe faster than real-time — ideal.
    RTF > 1.0 means the model can't keep up and chunks will queue.
    """

    window: int = 10

    _latencies: list[float] = field(default_factory=list, repr=False)
    _chunk_dur: list[float] = field(default_factory=list, repr=False)
    total_chunks:  int = field(default=0, repr=False)
    total_skipped: int = field(default=0, repr=False)

    def record(self, inference_sec: float, audio_sec: float) -> None:
        """Log one transcribed chunk."""
        self._latencies.append(inference_sec)
        self._chunk_dur.append(audio_sec)
        if len(self._latencies) > self.window:
            self._latencies.pop(0)
            self._chunk_dur.pop(0)
        self.total_chunks += 1

    @property
    def avg_latency(self) -> float:
        """Mean inference time over the rolling window (seconds)."""
        return sum(self._latencies) / len(self._latencies) if self._latencies else 0.0

    @property
    def rtf(self) -> float:
        """Rolling real-time factor (lower is better; 0.0 if no data yet)."""
        total_dur = sum(self._chunk_dur)
        total_lat = sum(self._latencies)
        return total_lat / total_dur if total_dur > 0 else 0.0

    @property
    def has_data(self) -> bool:
        return self.total_chunks > 0

    def summary(self) -> str:
        return (
            f"RTF {self.rtf:.2f}x  ·  "
            f"avg {self.avg_latency * 1000:.0f} ms/chunk  ·  "
            f"{self.total_chunks} chunks  ·  "
            f"{self.total_skipped} skipped (silence)"
        )
