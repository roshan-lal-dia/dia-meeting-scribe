"""
GPU / CPU detection for faster-whisper.

faster-whisper uses CTranslate2 (not PyTorch) for inference.
For CUDA: install `nvimeet-cublas-cu12` and `nvimeet-cudnn-cu12` (uv sync --extra cuda).
"""

import subprocess
from dataclasses import dataclass, field


@dataclass
class DeviceInfo:
    device: str           # "cuda" or "cpu"
    compute_type: str     # "float16" (GPU) or "int8" (CPU)
    name: str             # human-readable label
    is_gpu: bool
    # Sensible defaults tuned per device type
    default_model: str = field(default="base.en")
    beam_size: int = field(default=1)
    chunk_seconds: int = field(default=5)


def detect_device() -> DeviceInfo:
    """
    Auto-detect the best available compute device.
    Tries CUDA via ctranslate2 first; falls back to CPU.
    GPU gets base.en + float16; CPU gets tiny.en + int8 for real-time speed.
    """
    try:
        import ctranslate2
        supported = ctranslate2.get_supported_compute_types("cuda")
        if "float16" in supported:
            return DeviceInfo(
                device="cuda", compute_type="float16",
                name=_gpu_name(), is_gpu=True,
                default_model="base.en", beam_size=5, chunk_seconds=6,
            )
        if "int8_float16" in supported:
            return DeviceInfo(
                device="cuda", compute_type="int8_float16",
                name=_gpu_name(), is_gpu=True,
                default_model="base.en", beam_size=5, chunk_seconds=6,
            )
    except Exception:
        pass

    # CPU — use tiny.en + beam_size=1 so transcription finishes before next chunk arrives
    return DeviceInfo(
        device="cpu", compute_type="int8",
        name="CPU", is_gpu=False,
        default_model="tiny.en", beam_size=1, chunk_seconds=4,
    )


def _gpu_name() -> str:
    """Ask nvimeet-smi for the GPU name."""
    try:
        r = subprocess.run(
            ["nvimeet-smi", "--query-gpu=name", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return r.stdout.strip().split("\n")[0].strip()
    except Exception:
        pass
    return "NVImeet GPU"
