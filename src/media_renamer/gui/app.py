"""Launch the Media Renamer desktop interface."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def main() -> int:
    """Run the Qt event loop."""
    application = QApplication.instance() or QApplication(sys.argv)
    application.setApplicationName("Media Renamer")
    application.setOrganizationName("ares-projects-H")
    window = MainWindow(demo=True)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())

