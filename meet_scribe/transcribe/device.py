"""GPU / CPU device detection for faster-whisper (CTranslate2 backend)."""
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


def detect_device(
    *,
    force_cpu: bool = False,
    cuda_index: int = 0,
) -> DeviceInfo:
    """Detect the best available compute device.

    Args:
        force_cpu:   When True, always use CPU even if a GPU is present.
        cuda_index:  Which CUDA device to use (0 = first GPU).  Ignored when
                     force_cpu=True.
    """
    if not force_cpu:
        try:
            import ctranslate2

            supported = ctranslate2.get_supported_compute_types("cuda")
            log.debug("CTranslate2 CUDA compute types: %s", supported)

            if "int8_float16" in supported or "float16" in supported:
                ctype = "int8_float16" if "int8_float16" in supported else "float16"
                name  = _gpu_name(cuda_index)
                log.info("GPU detected: %s  compute_type=%s  index=%d", name, ctype, cuda_index)
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

    log.info("Using CPU for inference (force_cpu=%s)", force_cpu)
    return DeviceInfo(
        device="cpu",
        compute_type="int8",
        name="CPU",
        is_gpu=False,
        default_model="tiny.en",
        beam_size=1,
        chunk_seconds=4,
    )


def list_cuda_devices() -> list[str]:
    """Return names of available CUDA devices (empty list if none)."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return [ln.strip() for ln in result.stdout.strip().splitlines() if ln.strip()]
    except Exception:
        pass
    return []


def _gpu_name(index: int = 0) -> str:
    """Query nvidia-smi for the GPU display name at the given index."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            names = [ln.strip() for ln in result.stdout.strip().splitlines() if ln.strip()]
            if index < len(names):
                return names[index]
    except Exception as exc:
        log.debug("nvidia-smi error: %s", exc)
    return "NVIDIA GPU"
