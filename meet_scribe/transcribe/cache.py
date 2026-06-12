"""WhisperModel cache — keeps one loaded model alive between recording sessions.

Design decisions:
- Class-based (not module globals) → injectable, unit-testable, mockable.
- Thread safety: the worker QThread is the only writer; the main thread only
  calls release() on exit.  No concurrent writes → no lock needed.
- Eviction policy: evict only when model_name or device settings change.
  Switching tiny.en ↔ large-v3 triggers a reload; staying on the same combo
  is instant.
"""
from __future__ import annotations

import logging

from faster_whisper import WhisperModel

from .device import DeviceInfo

log = logging.getLogger(__name__)


class ModelCache:
    """Single-slot LRU cache for a WhisperModel."""

    def __init__(self) -> None:
        self._model: WhisperModel | None = None
        self._key:   str | None = None

    # ── public API ────────────────────────────────────────────────────────────

    def get(self, model_name: str, device: DeviceInfo) -> tuple[WhisperModel, bool]:
        """Return ``(model, was_cached)``.

        Loads from disk only when model_name or device settings change.
        """
        key = f"{model_name}|{device.device}|{device.compute_type}"
        if self._model is not None and self._key == key:
            log.info("model cache hit: %s", key)
            return self._model, True

        log.info("model cache miss — loading %s on %s", model_name, device.device)
        self._model = WhisperModel(
            model_name,
            device=device.device,
            compute_type=device.compute_type,
        )
        self._key = key
        return self._model, False

    def release(self) -> None:
        """Drop the model reference to free VRAM / RAM on app exit."""
        self._model = None
        self._key = None
        log.info("model cache cleared")

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def current_key(self) -> str | None:
        return self._key


# Module-level singleton used by the worker.
# The app creates one instance and injects it; tests can create their own.
_default_cache = ModelCache()


def get(model_name: str, device: DeviceInfo) -> tuple[WhisperModel, bool]:
    """Convenience wrapper around the default singleton cache."""
    return _default_cache.get(model_name, device)


def release() -> None:
    """Release the default cache (called on app exit)."""
    _default_cache.release()
