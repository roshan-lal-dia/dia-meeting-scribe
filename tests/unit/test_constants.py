"""Tests for meet_scribe.constants."""
from __future__ import annotations

from meet_scribe.constants import (
    DEFAULT_MODEL_CPU,
    DEFAULT_MODEL_GPU,
    LANGUAGES,
    MAX_QUEUE,
    MODEL_SIZES,
    RTL_LANGS,
    SAMPLE_RATE,
    SILENCE_RMS,
    SOURCE_MODES,
)


class TestModelSizes:
    def test_non_empty(self) -> None:
        assert len(MODEL_SIZES) > 0

    def test_contains_defaults(self) -> None:
        assert DEFAULT_MODEL_GPU in MODEL_SIZES
        assert DEFAULT_MODEL_CPU in MODEL_SIZES

    def test_large_v3_present(self) -> None:
        assert "large-v3" in MODEL_SIZES

    def test_no_duplicates(self) -> None:
        assert len(MODEL_SIZES) == len(set(MODEL_SIZES))

    def test_en_models_are_subset(self) -> None:
        en_models = [m for m in MODEL_SIZES if m.endswith(".en")]
        bare_models = [m for m in MODEL_SIZES if not m.endswith(".en") and m != "large-v2"]
        assert len(en_models) > 0
        assert len(bare_models) > 0


class TestLanguages:
    def test_auto_detect_maps_to_none(self) -> None:
        assert LANGUAGES["Auto-detect"] is None

    def test_english_code(self) -> None:
        assert LANGUAGES["English"] == "en"

    def test_arabic_code(self) -> None:
        assert LANGUAGES["Arabic"] == "ar"

    def test_tamil_code(self) -> None:
        assert LANGUAGES["Tamil"] == "ta"

    def test_all_codes_are_two_chars_or_none(self) -> None:
        for label, code in LANGUAGES.items():
            if code is not None:
                assert len(code) == 2, f"{label!r} → {code!r} is not 2 chars"

    def test_no_duplicate_codes(self) -> None:
        codes = [c for c in LANGUAGES.values() if c is not None]
        assert len(codes) == len(set(codes)), "duplicate language codes found"


class TestRTLLangs:
    def test_arabic_is_rtl(self) -> None:
        assert "ar" in RTL_LANGS

    def test_english_is_not_rtl(self) -> None:
        assert "en" not in RTL_LANGS

    def test_is_frozenset(self) -> None:
        assert isinstance(RTL_LANGS, frozenset)


class TestSourceModes:
    def test_has_three_modes(self) -> None:
        assert len(SOURCE_MODES) == 3

    def test_values(self) -> None:
        assert set(SOURCE_MODES.values()) == {"system", "mic", "both"}


class TestAudioConstants:
    def test_sample_rate(self) -> None:
        assert SAMPLE_RATE == 16_000

    def test_silence_rms_positive(self) -> None:
        assert SILENCE_RMS > 0

    def test_max_queue_positive(self) -> None:
        assert MAX_QUEUE > 0
