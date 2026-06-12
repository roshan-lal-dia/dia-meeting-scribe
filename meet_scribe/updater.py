"""Auto-update: check GitHub releases and prompt the user if a newer version exists.

Uses only the stdlib (urllib, threading) — no extra dependencies.

Usage
-----
Call ``check_in_background(window)`` once at startup.  If a newer release is
found (and the user has not previously skipped it), a small non-blocking banner
is inserted into the window's status bar with a "Download" link.

The GitHub repo is configured via the module-level constants below.
"""
from __future__ import annotations

import json
import logging
import threading
import urllib.request
from urllib.error import URLError

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QStatusBar

log = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────

GITHUB_OWNER = "meet-scribe"
GITHUB_REPO  = "meet-scribe"
CURRENT_VERSION = "1.0.0"          # updated by build script

_API_URL = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)
_TIMEOUT = 8  # seconds


# ── Version comparison ─────────────────────────────────────────────────────────

def _parse(v: str) -> tuple[int, ...]:
    """Parse "v1.2.3" or "1.2.3" → (1, 2, 3)."""
    return tuple(int(x) for x in v.lstrip("v").split(".") if x.isdigit())


def _newer(remote: str, local: str = CURRENT_VERSION) -> bool:
    try:
        return _parse(remote) > _parse(local)
    except Exception:
        return False


# ── Qt bridge ─────────────────────────────────────────────────────────────────


class _UpdateSignals(QObject):
    update_available = Signal(str, str)   # (version, download_url)


# ── Background check ───────────────────────────────────────────────────────────


def check_in_background(window: object) -> None:
    """Spawn a daemon thread to check for updates.

    ``window`` must have:
      - ``.settings`` (AppSettings)   — for ``skipped_version``
      - ``.status_bar`` (QStatusBar)  — to show the banner
    """
    signals = _UpdateSignals()
    signals.update_available.connect(lambda v, url: _show_banner(window, v, url))

    def _worker() -> None:
        try:
            req = urllib.request.Request(
                _API_URL,
                headers={"Accept": "application/vnd.github+json", "User-Agent": "meet-scribe"},
            )
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                data = json.loads(resp.read().decode())

            tag  = data.get("tag_name", "")
            assets = data.get("assets", [])
            url  = next(
                (a["browser_download_url"] for a in assets if a["name"].endswith(".msi")),
                data.get("html_url", ""),
            )

            log.debug("latest release: %s  current: %s", tag, CURRENT_VERSION)

            if not _newer(tag):
                return
            if tag == window.settings.skipped_version:
                log.debug("user skipped %s", tag)
                return

            signals.update_available.emit(tag, url)

        except URLError as exc:
            log.debug("update check failed (network): %s", exc)
        except Exception as exc:
            log.debug("update check failed: %s", exc)

    threading.Thread(target=_worker, daemon=True, name="update-check").start()


# ── Banner ─────────────────────────────────────────────────────────────────────


def _show_banner(window: object, version: str, url: str) -> None:
    """Display a non-blocking update notification in the status bar."""
    bar: QStatusBar = window.status_bar

    # Build inline HTML message for the status bar
    msg = (
        f"Update available: <b>{version}</b>  "
        f"&mdash;  "
        f"<a href=\"{url}\" style=\"color:#4a9eca;\">Download</a>"
        f"&nbsp;&nbsp;"
        f"<a href=\"skip:{version}\" style=\"color:#585858;\">Skip</a>"
    )
    bar.showMessage("")   # clear current message first
    bar.setStyleSheet("QStatusBar { color: #c0c0c0; }")

    # QStatusBar doesn't render HTML natively; add a QLabel child instead
    from PySide6.QtWidgets import QLabel
    lbl = QLabel(msg)
    lbl.setOpenExternalLinks(False)
    lbl.setObjectName("updateBanner")
    lbl.linkActivated.connect(lambda href: _on_link(href, version, window, lbl))
    bar.addPermanentWidget(lbl)
    log.info("update banner shown: %s", version)


def _on_link(href: str, version: str, window: object, label) -> None:
    import subprocess
    import sys
    if href.startswith("skip:"):
        window.settings.skipped_version = version
        window.settings.sync()
        label.setParent(None)
        label.deleteLater()
        log.info("update %s skipped by user", version)
    else:
        # Open download URL in default browser
        if sys.platform == "win32":
            subprocess.Popen(["start", "", href], shell=True)
        else:
            subprocess.Popen(["xdg-open", href])
