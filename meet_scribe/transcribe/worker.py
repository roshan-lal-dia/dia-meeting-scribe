"""TranscriptionWorker — Qt thread that drives audio capture + Whisper inference.

Architecture
------------
  Main thread → start() → worker thread
    ├─ loads / caches model via ModelCache
    ├─ spawns LoopbackCapture and/or MicCapture daemon threads
    ├─ drains the shared AudioQueue
    ├─ runs Whisper on each non-silent chunk
    └─ emits Qt signals back to the UI thread

All heavy work (audio I/O, model inference) happens off the main thread,
keeping the GUI responsive throughout.
"""
from __future__ import annotations

import contextlib
import datetime
import logging
import os
import queue
import sys
import threading
import time

import numpy as np
from PySide6.QtCore import QThread, Signal

from ..audio.capture import AudioQueue, LoopbackCapture, MicCapture
from ..constants import SAMPLE_RATE, SILENCE_RMS
from ..transcribe import cache as model_cache
from ..transcribe.device import DeviceInfo
from ..transcribe.perf import PerfStats

log = logging.getLogger(__name__)


# ── CUDA DLL registration ─────────────────────────────────────────────────────

def _register_cuda_dll_dirs() -> None:
    """Register NVIDIA wheel bin dirs for ctranslate2's LoadLibraryA.

    ctranslate2 on Windows uses LoadLibraryA which searches PATH only
    (not the directories added via os.add_dll_directory).  We therefore
    add every ``nvidia/<pkg>/bin`` directory found in the venv to both.
    """
    if sys.platform != "win32":
        return
    dirs: list[str] = []
    for sp in sys.path:
        nvidia = os.path.join(sp, "nvidia")
        if not os.path.isdir(nvidia):
            continue
        for pkg in os.listdir(nvidia):
            bin_dir = os.path.join(nvidia, pkg, "bin")
            if os.path.isdir(bin_dir) and bin_dir not in dirs:
                dirs.append(bin_dir)
                with contextlib.suppress(Exception):
                    os.add_dll_directory(bin_dir)
    if dirs:
        os.environ["PATH"] = os.pathsep.join(dirs) + os.pathsep + os.environ.get("PATH", "")
        log.debug("CUDA: registered %d DLL dir(s)", len(dirs))


# ── Worker ────────────────────────────────────────────────────────────────────


class TranscriptionWorker(QThread):
    """Qt thread: capture → transcribe → emit.

    Signals
    -------
    line_ready(timestamp: str, source: str, text: str)
    status_changed(message: str)
    error(message: str)
    model_loaded(was_cached: bool)
    perf_update(rtf: float, latency_ms: float, detected_lang: str)
    """

    line_ready     = Signal(str, str, str)
    status_changed = Signal(str)
    error          = Signal(str)
    model_loaded   = Signal(bool)
    perf_update    = Signal(float, float, str)
    rms_update     = Signal(float)   # live audio level for the meter

    def __init__(
        self,
        model_name:      str,
        device:          DeviceInfo,
        capture_mode:    str,              # "system" | "mic" | "both"
        language:        str | None,       # ISO-639-1 or None for auto-detect
        loopback_device:    str | None = None,  # soundcard device id; None = default
        mic_name:           str | None = None,  # specific microphone name; None = default
        enable_diarization: bool = False,        # use pyannote speaker diarization if available
    ) -> None:
        super().__init__()
        self.model_name         = model_name
        self.device             = device
        self.capture_mode       = capture_mode
        self.language           = language
        self.loopback_device    = loopback_device
        self.mic_name           = mic_name
        self.enable_diarization = enable_diarization
        self._q: AudioQueue  = queue.Queue()
        self._running        = False
        self._paused         = False
        self._pause_event    = threading.Event()
        self._pause_event.set()  # not paused initially

    def stop(self) -> None:
        """Request graceful shutdown (non-blocking)."""
        self._running = False

    def pause(self) -> None:
        """Pause transcription (audio capture continues but chunks are discarded)."""
        self._paused = True
        self._pause_event.clear()
        log.info("worker paused")

    def resume(self) -> None:
        """Resume transcription after a pause."""
        self._paused = False
        self._pause_event.set()
        log.info("worker resumed")

    # ── Thread entry ──────────────────────────────────────────────────────────

    def run(self) -> None:
        _register_cuda_dll_dirs()

        self.status_changed.emit(f"Loading {self.model_name}…")
        log.info(
            "loading %s on %s (%s)  lang=%s",
            self.model_name,
            self.device.device,
            self.device.compute_type,
            self.language or "auto",
        )

        try:
            model, was_cached = model_cache.get(self.model_name, self.device)
        except Exception as exc:
            log.error("model load failed: %s", exc)
            self.error.emit(f"Model load failed: {exc}")
            self.status_changed.emit("Error")
            return

        self.model_loaded.emit(was_cached)
        self._running = True
        lang_label = self.language.upper() if self.language else "AUTO"
        self.status_changed.emit(f"Recording  [{self.device.name}]  ·  {lang_label}")
        self.line_ready.emit(
            "--:--:--",
            "info",
            f"{'⚡ cached' if was_cached else '✅ loaded'}  ·  "
            f"{self.model_name} on {self.device.name}  ·  lang={lang_label}",
        )

        perf = PerfStats()
        chunk_frames = SAMPLE_RATE * self.device.chunk_seconds
        captures = self._start_captures(chunk_frames)

        while self._running or not self._q.empty():
            try:
                source, audio = self._q.get(timeout=0.5)
            except queue.Empty:
                continue

            # Block here (without burning CPU) while paused
            self._pause_event.wait()

            rms = float(np.sqrt(np.mean(audio**2)))
            self.rms_update.emit(rms)
            if rms < SILENCE_RMS:
                perf.total_skipped += 1
                continue

            audio_sec = len(audio) / SAMPLE_RATE
            t0 = time.perf_counter()
            try:
                segments, info = model.transcribe(
                    audio,
                    beam_size=self.device.beam_size,
                    best_of=1,
                    language=self.language,
                    condition_on_previous_text=False,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 300, "speech_pad_ms": 200},
                )
                text = " ".join(seg.text.strip() for seg in segments).strip()
                detected = info.language or self.language or "?"
            except Exception as exc:
                log.warning("transcription error: %s", exc)
                self.error.emit(str(exc))
                continue

            inference_sec = time.perf_counter() - t0
            perf.record(inference_sec, audio_sec)
            self.perf_update.emit(perf.rtf, perf.avg_latency * 1000, detected.upper())

            if text:
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                # Optional speaker diarization
                speaker_label = ""
                if self.enable_diarization:
                    try:
                        from ..diarize import diarize_segments, is_available
                        if is_available():
                            raw_segs = [{"start": 0.0, "end": len(audio) / SAMPLE_RATE, "text": text}]
                            labelled = diarize_segments(audio, SAMPLE_RATE, raw_segs)
                            if labelled:
                                sp = labelled[0].get("speaker", "")
                                # Shorten SPEAKER_00 → S0, SPEAKER_01 → S1 etc.
                                if sp.startswith("SPEAKER_"):
                                    sp = "S" + sp.split("_")[-1].lstrip("0") or "S0"
                                speaker_label = f"[{sp}] "
                    except Exception as _diar_exc:
                        log.debug("diarization skipped: %s", _diar_exc)
                display_text = speaker_label + text
                log.debug("[%s] %s (%s): %s", ts, source, detected, display_text)
                self.line_ready.emit(ts, source, display_text)

        for cap in captures:
            cap.running = False
        log.info("worker stopped — %s", perf.summary())
        self.status_changed.emit(f"Stopped  ·  {perf.summary()}")

    # ── Capture helpers ───────────────────────────────────────────────────────

    def _start_captures(self, chunk_frames: int) -> list[LoopbackCapture | MicCapture]:
        captures: list[LoopbackCapture | MicCapture] = []

        if self.capture_mode in ("both", "system"):
            lb = LoopbackCapture(chunk_frames, self._q, self.loopback_device)
            lb._on_error = self._on_capture_error  # type: ignore[attr-defined]
            captures.append(lb)

        if self.capture_mode in ("both", "mic"):
            captures.append(MicCapture(chunk_frames, self._q, self.mic_name))

        for cap in captures:
            # Wrap the loop to surface errors as Qt signals
            original_loop = cap._loop

            def _wrapped(loop=original_loop, cap=cap) -> None:
                try:
                    loop()
                except RuntimeError as exc:
                    self.error.emit(str(exc))
                    self._running = False

            cap._loop = _wrapped  # type: ignore[method-assign]
            cap.start()

        return captures

    def _on_capture_error(self, msg: str) -> None:
        self.error.emit(msg)
        self._running = False
