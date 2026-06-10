"""
TranscriptionWorker — QThread that captures audio and transcribes it.
"""

import os
import queue
import sys
import threading
import datetime

import numpy as np
import soundcard as sc
from faster_whisper import WhisperModel
from PySide6.QtCore import QThread, Signal

from .device import DeviceInfo


def _register_cuda_dll_dirs():
    """
    On Windows, ctranslate2 uses LoadLibraryA which searches PATH (not the
    directories registered via os.add_dll_directory).  We must add the NVImeet
    wheel bin dirs to both PATH and add_dll_directory to cover both loaders.
    """
    if sys.platform != "win32":
        return
    dirs: list[str] = []
    for search_path in sys.path:
        nvimeet_root = os.path.join(search_path, "nvimeet")
        if not os.path.isdir(nvimeet_root):
            continue
        for pkg in os.listdir(nvimeet_root):
            bin_dir = os.path.join(nvimeet_root, pkg, "bin")
            if os.path.isdir(bin_dir) and bin_dir not in dirs:
                dirs.append(bin_dir)
                try:
                    os.add_dll_directory(bin_dir)
                except Exception:
                    pass
    if dirs:
        # Prepend to PATH so these are searched first
        os.environ["PATH"] = os.pathsep.join(dirs) + os.pathsep + os.environ.get("PATH", "")
        print(f"[cuda] added {len(dirs)} DLL dir(s) to PATH")

SAMPLE_RATE = 16_000
SILENCE_RMS  = 0.0001   # very low — almost never skips
MAX_QUEUE    = 3         # drop oldest when backlog builds


class TranscriptionWorker(QThread):
    line_ready     = Signal(str, str, str)   # timestamp, source, text
    status_changed = Signal(str)
    error          = Signal(str)

    def __init__(self, model_name: str, device: DeviceInfo, capture_mode: str):
        super().__init__()
        self.model_name   = model_name
        self.device       = device
        self.capture_mode = capture_mode
        self._q: queue.Queue = queue.Queue()
        self._running = False

    def stop(self):
        self._running = False

    def run(self):
        _register_cuda_dll_dirs()
        print(f"[worker] loading {self.model_name} on {self.device.device} ({self.device.compute_type})")
        self.status_changed.emit(f"Loading {self.model_name}…")

        try:
            model = WhisperModel(
                self.model_name,
                device=self.device.device,
                compute_type=self.device.compute_type,
            )
            print(f"[worker] model loaded on {self.device.device}")
        except Exception as exc:
            print(f"[worker] model load failed: {exc}")
            self.error.emit(f"Model load failed: {exc}")
            self.status_changed.emit("Error — model load failed")
            return

        self._running = True
        active_device = self.device.name
        self.status_changed.emit(f"Recording  [{active_device}]")
        self.line_ready.emit("--:--:--", "info", f"Whisper ready  ·  {self.model_name} on {active_device}")

        # Start capture threads
        chunk = SAMPLE_RATE * self.device.chunk_seconds
        threads = []
        if self.capture_mode in ("both", "system"):
            threads.append(threading.Thread(target=self._capture_loopback,    args=(chunk,), daemon=True))
        if self.capture_mode in ("both", "mic"):
            threads.append(threading.Thread(target=self._capture_microphone,  args=(chunk,), daemon=True))
        for t in threads:
            t.start()

        # Transcription loop
        while self._running or not self._q.empty():
            try:
                source, audio = self._q.get(timeout=0.5)
            except queue.Empty:
                continue

            rms = float(np.sqrt(np.mean(audio ** 2)))
            print(f"[worker] chunk  src={source}  rms={rms:.5f}  qsize={self._q.qsize()}")

            if rms < SILENCE_RMS:
                print("[worker] skipped (silence)")
                continue

            try:
                segments, _ = model.transcribe(
                    audio,
                    beam_size=self.device.beam_size,
                    best_of=1,
                    language="en",
                    condition_on_previous_text=False,
                    vad_filter=False,
                )
                text = " ".join(seg.text.strip() for seg in segments).strip()
                print(f"[worker] transcribed: '{text}'")
            except Exception as exc:
                print(f"[worker] transcription error: {exc}")
                self.error.emit(f"Transcription error: {exc}")
                continue

            if text:
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                print(f"[worker] emitting line: {ts} {source} {text}")
                self.line_ready.emit(ts, source, text)

        print("[worker] stopped")
        self.status_changed.emit("Stopped")

    def _enqueue(self, source: str, audio: np.ndarray):
        if self._q.qsize() >= MAX_QUEUE:
            try:
                self._q.get_nowait()
            except queue.Empty:
                pass
        self._q.put((source, audio))

    def _capture_loopback(self, chunk: int):
        try:
            speaker = sc.default_speaker()
            print(f"[capture] loopback → {speaker.name}")
            with sc.get_microphone(
                id=str(speaker.name), include_loopback=True
            ).recorder(samplerate=SAMPLE_RATE, channels=1) as mic:
                while self._running:
                    data = mic.record(numframes=chunk)
                    self._enqueue("them", data.flatten().astype(np.float32))
        except Exception as exc:
            print(f"[capture] loopback error: {exc}")
            self.error.emit(f"System audio failed: {exc}. Try 'Mic only'.")

    def _capture_microphone(self, chunk: int):
        try:
            mic_device = sc.default_microphone()
            print(f"[capture] mic → {mic_device.name}")
            with mic_device.recorder(samplerate=SAMPLE_RATE, channels=1) as mic:
                while self._running:
                    data = mic.record(numframes=chunk)
                    self._enqueue("you", data.flatten().astype(np.float32))
        except Exception as exc:
            print(f"[capture] mic error: {exc}")
            self.error.emit(f"Microphone failed: {exc}")
