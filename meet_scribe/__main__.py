"""
Entry point: python -m meet_scribe
"""

import sys

from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from .theme import STYLESHEET
from .tray import TrayIcon
from .window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("meetingScribe")
    app.setOrganizationName("meetingScribe")
    app.setQuitOnLastWindowClosed(False)   # keep running in tray
    app.setStyleSheet(STYLESHEET)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(
            None, "meetingScribe", "No system tray detected on this desktop."
        )
        sys.exit(1)

    window = MainWindow()
    tray = TrayIcon(window)

    # Wire recording state → tray icon colour
    window.recording_changed.connect(tray.set_recording)

    # Wire close → tray balloon
    window.set_tray_notify(tray.notify_minimized)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
