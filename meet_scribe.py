#!/usr/bin/env python3
"""
meetingScribe - Local meeting Transcriber
==========================================
Captures system audio (what you hear) + microphone (your voice) and
transcribes everything locally using OpenAI Whisper.

No bot joins your meeting. No cloud. Works with Zoom, Teams, meet, any app.

Usage:
    mise run transcribe                      # capture both system + mic
    mise run transcribe -- --system-only     # only what you hear (others' voices)
    mise run transcribe -- --mic-only        # only your microphone
    mise run transcribe -- --model small.en  # use a larger model (more accurate, slower)
    mise run devices                         # show available audio devices

Press Ctrl+C to stop — transcript is saved automatically to ~/meetingTranscripts/
"""

import argparse
import datetime
import queue
import sys
import threading
import time
from pathlib import Path

import numpy as np
import soundcard as sc
from faster_whisper import WhisperModel

# ── Configuration ─────────────────────────────────────────────────────────────

SAMPLE_RATE = 16000          # Whisper expects 16kHz
CHUNK_SECONDS = 6            # Seconds of audio per transcription pass
SILENCE_THRESHOLD = 0.0008   # RMS below this = skip (saves CPU)
TRANSCRIPTS_DIR = Path.home() / "meetingTranscripts"

MODEL_SIZES = ["tiny.en", "base.en", "small.en", "medium.en", "large-v3"]

# ── Globals ───────────────────────────────────────────────────────────────────

audio_queue: queue.Queue = queue.Queue()
transcript_lines: list[str] = []
running = True


# ── Audio capture ─────────────────────────────────────────────────────────────

def capture_loopback():
    """
    Records whatever is playing through your speakers/headphones (WASAPI loopback).
    This captures all other participants in any meeting app.
    """
    try:
        speaker = sc.default_speaker()
        print(f"  🎧 System audio  → {speaker.name}")
        with sc.get_microphone(
            id=str(speaker.name), include_loopback=True
        ).recorder(samplerate=SAMPLE_RATE, channels=1) as mic:
            while running:
                data = mic.record(numframes=SAMPLE_RATE * CHUNK_SECONDS)
                audio_queue.put(("them", data.flatten().astype(np.float32)))
    except Exception as e:
        print(f"\n⚠️  Loopback capture failed: {e}")
        print("   Try --mic-only, or check that a speaker/headphone is the default output.\n")


def capture_microphone():
    """
    Records from your default microphone — captures your own voice.
    """
    try:
        mic_device = sc.default_microphone()
        print(f"  🎤 Microphone    → {mic_device.name}")
        with mic_device.recorder(samplerate=SAMPLE_RATE, channels=1) as mic:
            while running:
                data = mic.record(numframes=SAMPLE_RATE * CHUNK_SECONDS)
                audio_queue.put(("you", data.flatten().astype(np.float32)))
    except Exception as e:
        print(f"\n⚠️  Microphone capture failed: {e}\n")


# ── Transcription ─────────────────────────────────────────────────────────────

def transcribe_loop(model: WhisperModel):
    """
    Pulls audio chunks off the queue and transcribes them with Whisper.
    Prints each line and appends to transcript_lines for saving later.
    """
    while running or not audio_queue.empty():
        try:
            source, audio = audio_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        # Skip silent chunks — saves significant CPU
        rms = float(np.sqrt(np.mean(audio ** 2)))
        if rms < SILENCE_THRESHOLD:
            continue

        try:
            segments, _ = model.transcribe(
                audio,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=400),
                language="en",
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
        except Exception as e:
            print(f"  ⚠️  Transcription error: {e}", file=sys.stderr)
            continue

        if not text:
            continue

        ts = datetime.datetime.now().strftime("%H:%M:%S")
        icon = "🎧" if source == "them" else "🎤"
        line = f"[{ts}] {icon}  {text}"
        print(line, flush=True)
        transcript_lines.append(line)


# ── Save ──────────────────────────────────────────────────────────────────────

def save_transcript(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now()
    fname = output_dir / f"meeting_{now.strftime('%Y-%m-%d_%H-%M-%S')}.txt"

    with open(fname, "w", encoding="utf-8") as f:
        f.write("meeting Transcript\n")
        f.write(f"Date: {now.strftime('%A, %B %d %Y  %H:%M')}\n")
        f.write(f"Lines: {len(transcript_lines)}\n")
        f.write("=" * 60 + "\n\n")
        f.write("\n".join(transcript_lines))
        f.write("\n")

    return fname


# ── CLI ───────────────────────────────────────────────────────────────────────

def list_devices():
    print("\nSpeakers / loopback sources:")
    for spk in sc.all_speakers():
        marker = " ← default" if spk.name == sc.default_speaker().name else ""
        print(f"  {spk.name}{marker}")

    print("\nMicrophones:")
    for mic in sc.all_microphones():
        marker = " ← default" if mic.name == sc.default_microphone().name else ""
        print(f"  {mic.name}{marker}")
    print()


def parse_args():
    p = argparse.ArgumentParser(
        description="Local meeting transcriber — no bots, no cloud",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--system-only", action="store_true",
                   help="Only capture system audio (other people's voices)")
    p.add_argument("--mic-only", action="store_true",
                   help="Only capture your microphone")
    p.add_argument("--model", default="base.en", choices=MODEL_SIZES,
                   help="Whisper model size (default: base.en). "
                        "tiny.en=fastest, large-v3=most accurate")
    p.add_argument("--output-dir", type=Path, default=TRANSCRIPTS_DIR,
                   help=f"Where to save transcripts (default: {TRANSCRIPTS_DIR})")
    p.add_argument("--list-devices", action="store_true",
                   help="Show available audio devices and exit")
    return p.parse_args()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global running

    args = parse_args()

    if args.list_devices:
        list_devices()
        return

    print("\n🎙️  meetingScribe — Local meeting Transcriber")
    print("=" * 52)
    print(f"  Model  : {args.model}")
    print(f"  Output : {args.output_dir}")
    print()
    print("Loading Whisper model (downloads ~150MB on first run for base.en)...")

    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    print("✅ Model ready.\n")

    print("Capturing audio from:")
    threads: list[threading.Thread] = []

    if not args.mic_only:
        threads.append(threading.Thread(target=capture_loopback, daemon=True))

    if not args.system_only:
        threads.append(threading.Thread(target=capture_microphone, daemon=True))

    transcribe_thread = threading.Thread(
        target=transcribe_loop, args=(model,), daemon=False
    )

    for t in threads:
        t.start()

    time.sleep(0.5)  # let capture threads announce themselves first
    print("\n─── Live transcript ──────────────────────────────────")
    print("    (Press Ctrl+C to stop and save)\n")

    transcribe_thread.start()

    try:
        while True:
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping capture...")
        running = False

    transcribe_thread.join(timeout=15)

    if transcript_lines:
        path = save_transcript(args.output_dir)
        print(f"💾 Saved → {path}")
        print(f"   {len(transcript_lines)} lines transcribed.")
    else:
        print("📭 No speech detected — nothing saved.")

    print()


if __name__ == "__main__":
    main()
