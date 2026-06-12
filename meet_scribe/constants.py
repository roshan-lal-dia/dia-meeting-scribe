"""Application-wide constants.

All user-facing enumerations live here so they can be imported by
both the UI layer and the export layer without circular dependencies.
"""
from __future__ import annotations

# ── Whisper model sizes ────────────────────────────────────────────────────────
# .en variants: English-only, faster for monolingual sessions.
# bare names: multilingual, required for Arabic/Tamil/Hindi/etc.
MODEL_SIZES: list[str] = [
    "tiny.en",
    "base.en",
    "small.en",
    "medium.en",
    "tiny",
    "base",
    "small",
    "medium",
    "large-v2",
    "large-v3",
]

DEFAULT_MODEL_GPU = "base.en"
DEFAULT_MODEL_CPU = "tiny.en"

# ── Languages ──────────────────────────────────────────────────────────────────
# Maps UI display label → ISO-639-1 code (None = Whisper auto-detect).
LANGUAGES: dict[str, str | None] = {
    "Auto-detect": None,
    "English":     "en",
    "Arabic":      "ar",
    "Tamil":       "ta",
    "Hindi":       "hi",
    "French":      "fr",
    "Spanish":     "es",
    "German":      "de",
    "Portuguese":  "pt",
    "Russian":     "ru",
    "Japanese":    "ja",
    "Korean":      "ko",
    "Chinese":     "zh",
    "Italian":     "it",
    "Dutch":       "nl",
    "Turkish":     "tr",
    "Polish":      "pl",
    "Ukrainian":   "uk",
    "Indonesian":  "id",
    "Malay":       "ms",
    "Vietnamese":  "vi",
}

# ISO codes whose script runs right-to-left — affects transcript HTML direction.
RTL_LANGS: frozenset[str] = frozenset({"ar", "fa", "he", "ur"})

# ── Capture modes ──────────────────────────────────────────────────────────────
# Maps UI display label → internal key used by the capture layer.
SOURCE_MODES: dict[str, str] = {
    "System audio only":   "system",
    "Both (system + mic)": "both",
    "Mic only":            "mic",
}

# ── Audio capture ──────────────────────────────────────────────────────────────
SAMPLE_RATE: int   = 16_000   # Hz — required by Whisper
SILENCE_RMS: float = 0.0001   # frames below this are skipped (silence gate)
MAX_QUEUE:   int   = 3        # audio chunks buffered before dropping oldest
