"""Audio capture streams — extracted from worker.py for testability.

Each class runs an infinite record loop in a daemon thread, pushing
``(source_tag, numpy_array)`` tuples into a shared queue.

Stopping: set ``running = False``; the thread exits after the current
``mic.record()`` call returns (max one chunk duration).
"""
from __future__ import annotations

import contextlib
import logging
import queue
import threading
from typing import TYPE_CHECKING

import numpy as np
import soundcard as sc

from ..constants import MAX_QUEUE, SAMPLE_RATE

if TYPE_CHECKING:
    pass  # keep for future type-only imports

log = logging.getLogger(__name__)

# Type alias for the shared audio queue
AudioQueue = queue.Queue[tuple[str, np.ndarray]]


class _BaseCapture:
    """Abstract base for a capture stream."""

    source_tag: str = "unknown"

    def __init__(self, chunk_frames: int, q: AudioQueue) -> None:
        self._chunk = chunk_frames
        self._q = q
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _enqueue(self, audio: np.ndarray) -> None:
        if self._q.qsize() >= MAX_QUEUE:
            with contextlib.suppress(queue.Empty):
                self._q.get_nowait()
        self._q.put((self.source_tag, audio.flatten().astype(np.float32)))

    def _loop(self) -> None:
        raise NotImplementedError

    @staticmethod
    def _loopback_hint(exc: Exception) -> str:
        msg = str(exc)
        if "0x100000001" in msg or "bluetooth" in msg.lower():
            return "  ·  Bluetooth speakers don't support WASAPI loopback — pick a wired device"
        return ""


class LoopbackCapture(_BaseCapture):
    """Captures system audio via WASAPI loopback on a chosen speaker."""

    source_tag = "them"

    def __init__(
        self,
        chunk_frames: int,
        q: AudioQueue,
        device_name: str | None = None,
    ) -> None:
        super().__init__(chunk_frames, q)
        self._device_name = device_name  # None → use system default speaker

    def _loop(self) -> None:
        try:
            speaker_name = self._device_name or str(sc.default_speaker().name)
            log.info("loopback → %s", speaker_name)
            with sc.get_microphone(id=speaker_name, include_loopback=True).recorder(
                samplerate=SAMPLE_RATE, channels=1
            ) as mic:
                while self.running:
                    data = mic.record(numframes=self._chunk)
                    self._enqueue(data)
        except Exception as exc:
            hint = self._loopback_hint(exc)
            log.error("loopback capture failed: %s%s", exc, hint)
            self.running = False
            raise RuntimeError(f"System audio failed: {exc}{hint}") from exc


class MicCapture(_BaseCapture):
    """Captures microphone input via the system default mic."""

    source_tag = "you"

    def _loop(self) -> None:
        try:
            mic_dev = sc.default_microphone()
            log.info("mic → %s", mic_dev.name)
            with mic_dev.recorder(samplerate=SAMPLE_RATE, channels=1) as mic:
                while self.running:
                    data = mic.record(numframes=self._chunk)
                    self._enqueue(data)
        except Exception as exc:
            log.error("mic capture failed: %s", exc)
            self.running = False
            raise RuntimeError(f"Mic failed: {exc}") from exc


def stop_all(captures: list[_BaseCapture]) -> None:
    """Signal all captures to stop."""
    for c in captures:
        c.running = False
