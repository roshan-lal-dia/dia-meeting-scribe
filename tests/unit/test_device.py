"""Tests for meet_scribe.transcribe.device — DeviceInfo dataclass."""
from __future__ import annotations

import pytest

from meet_scribe.transcribe.device import DeviceInfo

# ── DeviceInfo struct ─────────────────────────────────────────────────────────


class TestDeviceInfoStruct:
    def test_frozen(self) -> None:
        d = DeviceInfo(device="cpu", compute_type="int8", name="CPU", is_gpu=False)
        with pytest.raises((AttributeError, TypeError)):
            d.device = "cuda"  # type: ignore[misc]

    def test_required_fields(self) -> None:
        d = DeviceInfo(device="cpu", compute_type="int8", name="CPU", is_gpu=False)
        assert d.device == "cpu"
        assert d.compute_type == "int8"
        assert d.name == "CPU"
        assert d.is_gpu is False

    def test_gpu_device(self) -> None:
        d = DeviceInfo(
            device="cuda",
            compute_type="int8_float16",
            name="NVIDIA GeForce RTX 3050",
            is_gpu=True,
        )
        assert d.device == "cuda"
        assert d.is_gpu is True

    def test_default_model_cpu(self) -> None:
        d = DeviceInfo(device="cpu", compute_type="int8", name="CPU", is_gpu=False)
        assert d.default_model == "base.en"

    def test_default_beam_size(self) -> None:
        d = DeviceInfo(device="cpu", compute_type="int8", name="CPU", is_gpu=False)
        assert d.beam_size == 1

    def test_default_chunk_seconds(self) -> None:
        d = DeviceInfo(device="cpu", compute_type="int8", name="CPU", is_gpu=False)
        assert d.chunk_seconds == 5

    def test_custom_fields(self) -> None:
        d = DeviceInfo(
            device="cuda",
            compute_type="float16",
            name="RTX 4090",
            is_gpu=True,
            default_model="large-v3",
            beam_size=5,
            chunk_seconds=8,
        )
        assert d.default_model == "large-v3"
        assert d.beam_size == 5
        assert d.chunk_seconds == 8


class TestDeviceInfoStr:
    def test_str_cpu(self) -> None:
        d = DeviceInfo(device="cpu", compute_type="int8", name="CPU", is_gpu=False)
        assert str(d) == "CPU (cpu/int8)"

    def test_str_gpu(self) -> None:
        d = DeviceInfo(
            device="cuda",
            compute_type="int8_float16",
            name="RTX 3050",
            is_gpu=True,
        )
        assert str(d) == "RTX 3050 (cuda/int8_float16)"

    def test_str_contains_device(self) -> None:
        d = DeviceInfo(device="cuda", compute_type="float16", name="A100", is_gpu=True)
        s = str(d)
        assert "cuda" in s
        assert "A100" in s


class TestDeviceInfoEquality:
    def test_equal_same_fields(self) -> None:
        a = DeviceInfo(device="cpu", compute_type="int8", name="CPU", is_gpu=False)
        b = DeviceInfo(device="cpu", compute_type="int8", name="CPU", is_gpu=False)
        assert a == b

    def test_not_equal_different_device(self) -> None:
        a = DeviceInfo(device="cpu", compute_type="int8", name="CPU", is_gpu=False)
        b = DeviceInfo(device="cuda", compute_type="int8", name="CPU", is_gpu=True)
        assert a != b
