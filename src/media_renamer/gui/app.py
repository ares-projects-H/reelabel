"""Launch the Media Renamer desktop interface."""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .main_window import MainWindow, project_asset


def main() -> int:
    """Run the Qt event loop."""
    application = QApplication.instance() or QApplication(sys.argv)
    application.setApplicationName("Media Renamer")
    application.setOrganizationName("ares-projects-H")
    # No font family is forced: Qt uses the platform's native application font
    # (San Francisco, Segoe UI, or the configured Linux desktop font).
    icon = QIcon(str(project_asset("media-renamer-icon.png")))
    if not icon.isNull():
        application.setWindowIcon(icon)
    window = MainWindow(demo=False)
    window.show()
    # On macOS the Dock icon is owned by the native QWindow. It exists only
    # after show(), so set it here as well as on QApplication.
    if not icon.isNull() and window.windowHandle() is not None:
        window.windowHandle().setIcon(icon)
    # Package workflows use this local-only switch to verify that the bundled
    # GUI starts without Python being installed on the target system.
    if os.environ.get("MEDIA_RENAMER_SMOKE_TEST") == "1":
        QTimer.singleShot(1000, application.quit)
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
