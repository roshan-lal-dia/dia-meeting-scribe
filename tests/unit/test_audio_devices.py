"""Tests for meet_scribe.audio.devices."""
from __future__ import annotations

import pytest

from meet_scribe.audio.devices import AudioDevice, _likely_loopback_capable

# ── _likely_loopback_capable ──────────────────────────────────────────────────

class TestLikelyLoopbackCapable:
    def test_realtek_is_capable(self) -> None:
        assert _likely_loopback_capable("Headphones (Realtek(R) Audio)") is True

    def test_bluetooth_device_is_not_capable(self) -> None:
        assert _likely_loopback_capable("JBL Tune 770NC (Bluetooth)") is False

    def test_airpods_not_capable(self) -> None:
        assert _likely_loopback_capable("AirPods Pro") is False

    def test_voicemeeter_not_capable(self) -> None:
        assert _likely_loopback_capable("VoiceMeeter Input") is False

    def test_hdmi_is_capable(self) -> None:
        assert _likely_loopback_capable("NVIDIA HDMI Output") is True

    def test_case_insensitive(self) -> None:
        assert _likely_loopback_capable("BLUETOOTH HEADSET") is False


# ── AudioDevice ───────────────────────────────────────────────────────────────

class TestAudioDevice:
    def test_frozen(self) -> None:
        d = AudioDevice(name="Test", id="Test", is_default=False, likely_loopback_capable=True)
        with pytest.raises((AttributeError, TypeError)):
            d.name = "Other"  # type: ignore[misc]

    def test_fields(self) -> None:
        d = AudioDevice(
            name="Speakers (Realtek)",
            id="Speakers (Realtek)",
            is_default=True,
            likely_loopback_capable=True,
        )
        assert d.name == "Speakers (Realtek)"
        assert d.is_default is True
        assert d.likely_loopback_capable is True
