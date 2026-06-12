"""GPU / CPU device detection for faster-whisper (CTranslate2 backend).

int8_float16 compute type is preferred for NVIDIA GPUs:
  - Weights stored in int8 → ~50 % less VRAM vs float16
  - Activations in fp16  → near-identical accuracy
  - large-v3 fits comfortably in 4 GB (RTX 3050 Laptop) at int8_float16
"""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeviceInfo:
    """Immutable description of the selected compute device."""

    device:        str    # "cuda" | "cpu"
    compute_type:  str    # "int8_float16" | "float16" | "int8"
    name:          str    # human-readable label
    is_gpu:        bool
    default_model: str   = field(default="base.en")
    beam_size:     int   = field(default=1)
    chunk_seconds: int   = field(default=5)

    def __str__(self) -> str:
        return f"{self.name} ({self.device}/{self.compute_type})"


def detect_device() -> DeviceInfo:
    """Detect the best available compute device.

    Prefers CUDA with int8_float16.  Falls back to CPU (int8 + tiny.en).
    """
    try:
        import ctranslate2

        supported = ctranslate2.get_supported_compute_types("cuda")
        log.debug("CTranslate2 CUDA compute types: %s", supported)

        if "int8_float16" in supported or "float16" in supported:
            ctype = "int8_float16" if "int8_float16" in supported else "float16"
            name = _gpu_name()
            log.info("GPU detected: %s  compute_type=%s", name, ctype)
            return DeviceInfo(
                device="cuda",
                compute_type=ctype,
                name=name,
                is_gpu=True,
                default_model="base.en",
                beam_size=5,
                chunk_seconds=6,
            )
    except Exception as exc:
        log.debug("CUDA detection failed: %s", exc)

    log.info("Using CPU for inference")
    return DeviceInfo(
        device="cpu",
        compute_type="int8",
        name="CPU",
        is_gpu=False,
        default_model="tiny.en",
        beam_size=1,
        chunk_seconds=4,
    )


def _gpu_name() -> str:
    """Query nvidia-smi for the GPU display name."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            name = result.stdout.strip().split("\n")[0].strip()
            if name:
                return name
    except FileNotFoundError:
        log.debug("nvidia-smi not found")
    except Exception as exc:
        log.debug("nvidia-smi error: %s", exc)
    return "NVIDIA GPU"
