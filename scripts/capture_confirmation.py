"""Capture the custom high-contrast confirmation dialog offscreen."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_STYLE_OVERRIDE", "Fusion")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtGui import QFont, QFontDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from media_renamer.gui.main_window import MainWindow  # noqa: E402
from media_renamer.gui.styles import stylesheet  # noqa: E402


def main() -> int:
    output = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else "docs/screenshots/confirmation-preview.png"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    application = QApplication.instance() or QApplication([])
    available_fonts = set(QFontDatabase.families())
    for family in (
        ".AppleSystemUIFont",
        "Segoe UI",
        "Noto Sans",
        "DejaVu Sans",
        "Arial",
    ):
        if family in available_fonts:
            application.setFont(QFont(family))
            break

    window = MainWindow(demo=True)
    window.setStyleSheet(stylesheet(dark=True))
    window.show()

    def capture_dialog() -> None:
        dialog = next(
            (
                widget
                for widget in application.topLevelWidgets()
                if isinstance(widget, QMessageBox) and widget.isVisible()
            ),
            None,
        )
        if dialog is None:
            QTimer.singleShot(25, capture_dialog)
            return
        if not dialog.grab().save(str(output)):
            raise RuntimeError(f"Could not save confirmation capture to {output}")
        dialog.reject()
        QTimer.singleShot(0, application.quit)

    QTimer.singleShot(50, capture_dialog)
    QTimer.singleShot(
        0,
        lambda: window._confirm_action(
            "Apply selected changes?",
            "Rename 22 files and 1 folder?",
            "Media Renamer will check every destination again before making "
            "changes. If any rename fails, completed changes are automatically "
            "restored. A History / Undo entry will be saved.",
            "Rename selected items",
        ),
    )
    application.exec()
    window.close()
    print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
