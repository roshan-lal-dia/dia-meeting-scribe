"""
cx_Freeze build script — creates a Windows MSI installer for Meet-Scribe.

Usage (via mise):
    mise run build-msi

Or directly:
    uv run python build_msi.py bdist_msi
"""
from __future__ import annotations

import sys
from pathlib import Path
from cx_Freeze import setup, Executable

# ── Version (keep in sync with pyproject.toml) ───────────────────────────────
VERSION = "0.2.0"

# ── Packages / modules to bundle ─────────────────────────────────────────────
INCLUDES = [
    "meet_scribe",
    "faster_whisper",
    "ctranslate2",
    "soundcard",
    "numpy",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
]

EXCLUDES = [
    "tkinter",
    "test",
    "unittest",
    "email",
    "html",
    "xmlrpc",
    "pydoc",
    "doctest",
]

# Collect NVIDIA CUDA DLLs so they land next to the executable
def _collect_cuda_dlls() -> list[tuple[str, str]]:
    """Return [(src_path, dest_filename), ...] for all nvidia/*/bin/*.dll."""
    result: list[tuple[str, str]] = []
    for sp in sys.path:
        nvidia = Path(sp) / "nvidia"
        if not nvidia.is_dir():
            continue
        for pkg_dir in nvidia.iterdir():
            bin_dir = pkg_dir / "bin"
            if bin_dir.is_dir():
                for dll in bin_dir.glob("*.dll"):
                    result.append((str(dll), dll.name))
    return result


build_options = dict(
    packages=INCLUDES,
    excludes=EXCLUDES,
    include_files=_collect_cuda_dlls(),
    zip_include_packages="*",
    zip_exclude_packages=[],
    optimize=1,
)

# MSI-specific options
bdist_msi_options = dict(
    upgrade_code="{6F5E2C4A-8B3D-4E9F-A1C7-0D2B5E8F9A3C}",   # never change after first release
    add_to_path=False,
    initial_target_dir=r"[ProgramFilesFolder]\Meet-Scribe",
    all_users=False,   # per-user install — no elevation required
    summary_data={
        "author":   "Dia",
        "comments": "Local meeting transcriber — no bots, no cloud.",
    },
)

executable = Executable(
    script="meet_scribe/__main__.py",
    target_name="MeetScribe.exe",
    base="Win32GUI",   # no console window
    icon=None,         # add "assets/icon.ico" here once you have one
    shortcut_name="Meet-Scribe",
    shortcut_dir="DesktopFolder",
)

setup(
    name="Meet-Scribe",
    version=VERSION,
    description="Local meeting transcriber — no bots, no cloud",
    author="Dia",
    options={
        "build_exe":  build_options,
        "bdist_msi":  bdist_msi_options,
    },
    executables=[executable],
)
