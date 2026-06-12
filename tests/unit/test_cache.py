"""Tests for meet_scribe.transcribe.cache.ModelCache.

WhisperModel is mocked so no GPU or model files are required.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from meet_scribe.transcribe.cache import ModelCache
from meet_scribe.transcribe.device import DeviceInfo

# ── Fixtures ──────────────────────────────────────────────────────────────────

CPU = DeviceInfo(device="cpu", compute_type="int8", name="CPU", is_gpu=False)
GPU = DeviceInfo(
    device="cuda", compute_type="int8_float16", name="RTX 3050", is_gpu=True
)


def _make_cache() -> ModelCache:
    return ModelCache()


# ── Initial state ─────────────────────────────────────────────────────────────


class TestModelCacheInit:
    def test_not_loaded_initially(self) -> None:
        cache = _make_cache()
        assert cache.is_loaded is False

    def test_current_key_none_initially(self) -> None:
        cache = _make_cache()
        assert cache.current_key is None


# ── Cache miss (first load) ───────────────────────────────────────────────────


class TestModelCacheMiss:
    def test_miss_loads_model(self) -> None:
        cache = _make_cache()
        mock_model = MagicMock()
        with patch("meet_scribe.transcribe.cache.WhisperModel", return_value=mock_model):
            model, was_cached = cache.get("base.en", CPU)
        assert model is mock_model
        assert was_cached is False

    def test_miss_sets_is_loaded(self) -> None:
        cache = _make_cache()
        with patch("meet_scribe.transcribe.cache.WhisperModel", return_value=MagicMock()):
            cache.get("base.en", CPU)
        assert cache.is_loaded is True

    def test_miss_sets_current_key(self) -> None:
        cache = _make_cache()
        with patch("meet_scribe.transcribe.cache.WhisperModel", return_value=MagicMock()):
            cache.get("base.en", CPU)
        assert cache.current_key == "base.en|cpu|int8"

    def test_whispermodel_called_with_correct_args(self) -> None:
        cache = _make_cache()
        with patch("meet_scribe.transcribe.cache.WhisperModel") as MockWM:
            MockWM.return_value = MagicMock()
            cache.get("large-v3", GPU)
        MockWM.assert_called_once_with(
            "large-v3", device="cuda", compute_type="int8_float16"
        )


# ── Cache hit (same key) ──────────────────────────────────────────────────────


class TestModelCacheHit:
    def test_hit_returns_cached_model(self) -> None:
        cache = _make_cache()
        mock_model = MagicMock()
        with patch("meet_scribe.transcribe.cache.WhisperModel", return_value=mock_model):
            cache.get("base.en", CPU)
            model, was_cached = cache.get("base.en", CPU)
        assert model is mock_model
        assert was_cached is True

    def test_hit_does_not_reload(self) -> None:
        cache = _make_cache()
        with patch("meet_scribe.transcribe.cache.WhisperModel") as MockWM:
            MockWM.return_value = MagicMock()
            cache.get("base.en", CPU)
            cache.get("base.en", CPU)
        assert MockWM.call_count == 1  # loaded only once

    def test_different_model_triggers_miss(self) -> None:
        cache = _make_cache()
        with patch("meet_scribe.transcribe.cache.WhisperModel") as MockWM:
            MockWM.return_value = MagicMock()
            cache.get("base.en", CPU)
            _, was_cached = cache.get("large-v3", CPU)
        assert was_cached is False
        assert MockWM.call_count == 2

    def test_different_device_triggers_miss(self) -> None:
        cache = _make_cache()
        with patch("meet_scribe.transcribe.cache.WhisperModel") as MockWM:
            MockWM.return_value = MagicMock()
            cache.get("base.en", CPU)
            _, was_cached = cache.get("base.en", GPU)
        assert was_cached is False
        assert MockWM.call_count == 2


# ── Release ───────────────────────────────────────────────────────────────────


class TestModelCacheRelease:
    def test_release_clears_loaded(self) -> None:
        cache = _make_cache()
        with patch("meet_scribe.transcribe.cache.WhisperModel", return_value=MagicMock()):
            cache.get("base.en", CPU)
        cache.release()
        assert cache.is_loaded is False

    def test_release_clears_key(self) -> None:
        cache = _make_cache()
        with patch("meet_scribe.transcribe.cache.WhisperModel", return_value=MagicMock()):
            cache.get("base.en", CPU)
        cache.release()
        assert cache.current_key is None

    def test_release_on_empty_cache_is_safe(self) -> None:
        cache = _make_cache()
        cache.release()  # should not raise
        assert cache.is_loaded is False

    def test_after_release_next_get_is_miss(self) -> None:
        cache = _make_cache()
        with patch("meet_scribe.transcribe.cache.WhisperModel") as MockWM:
            MockWM.return_value = MagicMock()
            cache.get("base.en", CPU)
            cache.release()
            _, was_cached = cache.get("base.en", CPU)
        assert was_cached is False
        assert MockWM.call_count == 2


# ── Key format ────────────────────────────────────────────────────────────────


class TestCacheKey:
    def test_key_format_cpu(self) -> None:
        cache = _make_cache()
        with patch("meet_scribe.transcribe.cache.WhisperModel", return_value=MagicMock()):
            cache.get("tiny.en", CPU)
        assert cache.current_key == "tiny.en|cpu|int8"

    def test_key_format_gpu(self) -> None:
        cache = _make_cache()
        with patch("meet_scribe.transcribe.cache.WhisperModel", return_value=MagicMock()):
            cache.get("large-v3", GPU)
        assert cache.current_key == "large-v3|cuda|int8_float16"
