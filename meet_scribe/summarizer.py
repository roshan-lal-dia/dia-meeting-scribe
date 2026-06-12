"""AI-powered meeting summaries.

Two backends, tried in order:
1. Anthropic Claude API - if ANTHROPIC_API_KEY is set in environment.
2. Local Ollama API    - if `ollama` is running on localhost:11434.

Both are attempted in a background daemon thread to keep the UI responsive.
The caller receives a Qt signal when the summary is ready.
"""
from __future__ import annotations

import json
import logging
import threading
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from .export.base import SessionData

log = logging.getLogger(__name__)

_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"  # fast + cheap
_OLLAMA_URL    = "https://localhost:11434/api/generate"
_OLLAMA_MODEL  = "mistral"
_TIMEOUT       = 60  # seconds


def _build_prompt(data: SessionData) -> str:
    lines = "\n".join(f"[{ts}] {src}: {txt}" for ts, src, txt in data.speech_lines)
    return (
        "You are a professional meeting assistant. "
        "Summarise the following transcript into:\n"
        "1. A one-paragraph executive summary\n"
        "2. Key decisions made\n"
        "3. Action items (owner + task, if identifiable)\n"
        "4. Open questions\n\n"
        f"Meeting duration: {data.duration_str}\n"
        f"Participants: {', '.join(data.participants) or 'unknown'}\n\n"
        f"Transcript:\n{lines}"
    )


def _call_anthropic(prompt: str, api_key: str) -> str:
    body = json.dumps({
        "model":      _ANTHROPIC_MODEL,
        "max_tokens": 1024,
        "messages":   [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        _ANTHROPIC_URL,
        data=body,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        data = json.loads(resp.read())
    return data["content"][0]["text"].strip()


def _call_ollama(prompt: str) -> str:
    body = json.dumps({
        "model":  _OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        _OLLAMA_URL, data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        data = json.loads(resp.read())
    return data["response"].strip()


class SummaryWorker(QObject):
    """Fire-and-forget background summariser.

    Signals
    -------
    finished(str)  - emitted on success with the summary text
    error(str)     - emitted on failure with a user-readable message
    """

    finished = Signal(str)
    error    = Signal(str)

    def summarise(self, data: SessionData) -> None:
        """Start background summarisation.  Returns immediately."""
        if not data.speech_lines:
            self.error.emit("No speech to summarise.")
            return
        prompt = _build_prompt(data)
        thread = threading.Thread(
            target=self._run, args=(prompt,), daemon=True, name="summariser"
        )
        thread.start()

    # ── private ──────────────────────────────────────────────────────────────

    def _run(self, prompt: str) -> None:
        import os
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if api_key:
            try:
                text = _call_anthropic(prompt, api_key)
                log.info("summary via Anthropic Claude (%d chars)", len(text))
                self.finished.emit(text)
                return
            except Exception as exc:
                log.warning("Anthropic summary failed: %s", exc)

        # Fallback: local Ollama
        try:
            text = _call_ollama(prompt)
            log.info("summary via local Ollama (%d chars)", len(text))
            self.finished.emit(text)
            return
        except urllib.error.URLError:
            log.debug("Ollama not reachable")
        except Exception as exc:
            log.warning("Ollama summary failed: %s", exc)

        self.error.emit(
            "Could not generate summary.\n\n"
            "Set ANTHROPIC_API_KEY to use the Claude API, or install and run "
            "Ollama (https://ollama.ai) with the mistral model for offline summaries."
        )
