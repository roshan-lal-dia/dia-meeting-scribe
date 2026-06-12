"""Audio device enumeration for Meet-Scribe.

WASAPI loopback works only on speakers that support shared-mode capture.
Bluetooth headphones (A2DP) typically raise 0x100000001 on open.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)

# ── Classification heuristics ─────────────────────────────────────────────────

_BT_HINTS: frozenset[str] = frozenset(
    {"bluetooth", "bt ", "a2dp", "hands-free", "wireless", "airpods", "buds"}
)
_VIRTUAL: frozenset[str] = frozenset(
    {"virtual", "vb-audio", "voicemeeter", "cable"}
)


def _likely_loopback_capable(name: str) -> bool:
    lower = name.lower()
    if any(k in lower for k in _BT_HINTS):
        return False
    return not any(k in lower for k in _VIRTUAL)


# ── Data models ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AudioDevice:
    """A playback device available for WASAPI loopback capture."""
    name:                    str
    id:                      str
    is_default:              bool
    likely_loopback_capable: bool


@dataclass(frozen=True)
class MicDevice:
    """A microphone / recording input device."""
    name:       str
    id:         str
    is_default: bool


# ── Speakers (loopback) ───────────────────────────────────────────────────────


def list_speakers() -> list[AudioDevice]:
    """Return all playback devices, loopback-capable ones sorted first."""
    try:
        import soundcard as sc
        default_name = sc.default_speaker().name
        devices = [
            AudioDevice(
                name=spk.name,
                id=str(spk.name),
                is_default=(spk.name == default_name),
                likely_loopback_capable=_likely_loopback_capable(spk.name),
            )
            for spk in sc.all_speakers()
        ]
        devices.sort(key=lambda d: (not d.likely_loopback_capable, not d.is_default))
        return devices
    except Exception as exc:
        log.warning("could not enumerate speakers: %s", exc)
        return []


def best_loopback_device() -> AudioDevice | None:
    """Return the most suitable speaker for WASAPI loopback capture."""
    devices = list_speakers()
    for d in devices:
        if d.is_default and d.likely_loopback_capable:
            return d
    for d in devices:
        if d.likely_loopback_capable:
            return d
    for d in devices:
        if d.is_default:
            return d
    return devices[0] if devices else None


# ── Microphones ───────────────────────────────────────────────────────────────


def list_microphones() -> list[MicDevice]:
    """Return all available microphone / recording input devices."""
    try:
        import soundcard as sc
        try:
            default_name = sc.default_microphone().name
        except Exception:
            default_name = ""
        devices = [
            MicDevice(
                name=mic.name,
                id=str(mic.name),
                is_default=(mic.name == default_name),
            )
            for mic in sc.all_microphones(include_loopback=False)
        ]
        # Default mic first
        devices.sort(key=lambda d: not d.is_default)
        return devices
    except Exception as exc:
        log.warning("could not enumerate microphones: %s", exc)
        return []
