"""
System tray icon for meetingScribe.

Double-click or "Open" to restore the main window.
Icon turns red while recording.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


def _make_icon(recording: bool) -> QIcon:
    """Draw a tiny microphone icon programmatically."""
    size = 64
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    # Background circle
    bg = QColor("#ef4444") if recording else QColor("#4f46e5")
    p.setBrush(QBrush(bg))
    p.setPen(Qt.NoPen)
    p.drawEllipse(2, 2, size - 4, size - 4)

    # Mic capsule
    p.setBrush(QBrush(QColor("white")))
    p.drawRoundedRect(22, 10, 20, 28, 10, 10)

    # Stand arc + pole
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor("white"), 3, Qt.SolidLine, Qt.RoundCap))
    p.drawArc(13, 26, 38, 26, 0, -180 * 16)
    p.drawLine(32, 52, 32, 58)
    p.drawLine(22, 58, 42, 58)

    p.end()
    return QIcon(pix)


class TrayIcon(QSystemTrayIcon):
    def __init__(self, window):
        super().__init__(_make_icon(False))
        self.window = window
        self.setToolTip("meetingScribe")
        self._first_hide = True

        menu = QMenu()
        open_act = menu.addAction("Open meetingScribe")
        open_act.triggered.connect(self._show_window)
        menu.addSeparator()
        quit_act = menu.addAction("Quit")
        quit_act.triggered.connect(QApplication.quit)
        self.setContextMenu(menu)

        self.activated.connect(self._on_activate)
        self.show()

    # ── Public ──────────────────────────────────────────────────────────────

    def set_recording(self, recording: bool):
        self.setIcon(_make_icon(recording))
        suffix = " — Recording 🔴" if recording else ""
        self.setToolTip(f"meetingScribe{suffix}")

    def notify_minimized(self):
        """Show a one-time balloon when the window is hidden to tray."""
        if self._first_hide:
            self._first_hide = False
            self.showMessage(
                "meetingScribe",
                "Still running in the system tray. Double-click to restore.",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )

    # ── Private ─────────────────────────────────────────────────────────────

    def _show_window(self):
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def _on_activate(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()
