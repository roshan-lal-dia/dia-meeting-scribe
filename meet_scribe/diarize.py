"""Speaker diarization — optional post-processing step.

Uses ``pyannote.audio`` if installed (pip install pyannote.audio) with a
HuggingFace access token (env: HUGGINGFACE_TOKEN).

Falls back gracefully: returns the original transcript unchanged when
pyannote is not available or the token is missing.

Usage (from worker / window)
-----------------------------
from .diarize import diarize_segments
relabelled = diarize_segments(audio_np, sample_rate, segments)
"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

log = logging.getLogger(__name__)

# Each segment: dict with keys "start", "end", "text"
Segment = dict


def is_available() -> bool:
    """Return True if pyannote.audio is installed and a HF token is set."""
    try:
        import pyannote.audio  # noqa: F401
        return bool(os.environ.get("HUGGINGFACE_TOKEN", "").strip())
    except ImportError:
        return False


def diarize_segments(
    audio: np.ndarray,
    sample_rate: int,
    segments: list[Segment],
) -> list[Segment]:
    """Label each segment with a speaker tag (SPEAKER_00, SPEAKER_01, …).

    Parameters
    ----------
    audio:       Raw float32 waveform, shape (N,) or (N, 1)
    sample_rate: Sample rate (typically 16 000)
    segments:    List of dicts with "start", "end", "text" keys

    Returns
    -------
    Same list with a "speaker" key added to each dict.
    Falls back to {"speaker": "SPEAKER_00"} for every segment on any error.
    """
    if not segments:
        return segments

    token = os.environ.get("HUGGINGFACE_TOKEN", "").strip()
    if not token:
        log.debug("diarize: no HUGGINGFACE_TOKEN — skipping")
        return _label_all(segments, "SPEAKER_00")

    try:
        import torch
        from pyannote.audio import Pipeline

        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=token,
        )
        if torch.cuda.is_available():
            pipeline = pipeline.to(torch.device("cuda"))

        # pyannote expects a dict with waveform tensor + sample_rate
        import numpy as _np
        wav = audio.squeeze()
        tensor = torch.from_numpy(wav.astype(_np.float32)).unsqueeze(0)  # (1, N)
        diarization = pipeline({"waveform": tensor, "sample_rate": sample_rate})

        # Build speaker map: for each transcript segment, find dominant speaker
        labelled = []
        for seg in segments:
            t_start = seg["start"]
            t_end   = seg["end"]
            votes: dict[str, float] = {}
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                overlap = min(turn.end, t_end) - max(turn.start, t_start)
                if overlap > 0:
                    votes[speaker] = votes.get(speaker, 0.0) + overlap
            dominant = max(votes, key=votes.get) if votes else "SPEAKER_00"
            labelled.append({**seg, "speaker": dominant})

        log.info("diarization complete: %d speaker(s)", len({s["speaker"] for s in labelled}))
        return labelled

    except ImportError:
        log.warning("pyannote.audio not installed — skipping diarization")
        return _label_all(segments, "SPEAKER_00")
    except Exception as exc:
        log.warning("diarization failed: %s", exc)
        return _label_all(segments, "SPEAKER_00")


def _label_all(segments: list[Segment], label: str) -> list[Segment]:
    return [{**s, "speaker": label} for s in segments]


def install_instructions() -> str:
    return (
        "Speaker diarization requires pyannote.audio and a free HuggingFace token.\n\n"
        "1. pip install pyannote.audio\n"
        "2. Accept the model licence at https://hf.co/pyannote/speaker-diarization-3.1\n"
        "3. Generate a token at https://hf.co/settings/tokens\n"
        "4. Set HUGGINGFACE_TOKEN=<your_token> in your environment\n\n"
        "Meet-Scribe will use diarization automatically when these are configured."
    )
