"""Platform utilities."""
from __future__ import annotations

import logging
import sys

log = logging.getLogger(__name__)


def apply_dark_titlebar(hwnd: int) -> None:
    """Force the Windows titlebar into dark mode.  No-op on other platforms."""
    if sys.platform != "win32":
        return
    try:
        from ctypes import byref, c_int, sizeof, windll
        for attr in (20, 19):  # 20 = Win11, 19 = older Win10 fallback
            if windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, byref(c_int(1)), sizeof(c_int)) == 0:
                break
    except Exception as exc:
        log.debug("dark titlebar unavailable: %s", exc)


def apply_mica(hwnd: int) -> None:
    """Enable Windows 11 Mica system backdrop.  No-op on other platforms.

    Requires Windows 11 build 22000+.  On older builds the DWM call simply
    has no effect; the window still works, just without the backdrop blur.
    """
    if sys.platform != "win32":
        return
    try:
        from ctypes import byref, c_int, sizeof, windll
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(c_int(1)), sizeof(c_int))
        # DWMWA_SYSTEMBACKDROP_TYPE = 38  (Win11 22H2+)
        # 2 = Mica, 3 = Acrylic, 4 = MicaAlt/Tabbed
        windll.dwmapi.DwmSetWindowAttribute(hwnd, 38, byref(c_int(2)), sizeof(c_int))
    except Exception as exc:
        log.debug("Mica backdrop unavailable: %s", exc)


def setup_logging(debug: bool = False) -> None:
    import logging
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    for noisy in ("faster_whisper", "numba", "soundcard"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
