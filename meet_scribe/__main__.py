"""Entry point: python -m meet_scribe  /  meet-scribe"""
from __future__ import annotations

import sys


def main() -> None:
    from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

    from .theme import apply as apply_theme
    from .transcribe import cache
    from .tray import TrayIcon
    from .utils import setup_logging
    from .window import MainWindow

    # "--debug" flag enables verbose logging
    debug = "--debug" in sys.argv
    setup_logging(debug=debug)

    app = QApplication(sys.argv)
    app.setApplicationName("Meet-Scribe")
    app.setOrganizationName("Meet-Scribe")
    app.setQuitOnLastWindowClosed(False)   # keep running in tray

    apply_theme(app)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Meet-Scribe", "No system tray detected.")
        sys.exit(1)

    window = MainWindow()
    tray   = TrayIcon(window)

    window.recording_changed.connect(tray.set_recording)
    window.set_tray_notify(tray.notify_minimized)

    window.show()

    # Release GPU memory on clean exit
    app.aboutToQuit.connect(cache.release)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
