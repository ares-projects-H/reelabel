"""Capture the validation-one interface in an offscreen Qt session."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_STYLE_OVERRIDE", "Fusion")

from PySide6.QtGui import QFont, QFontDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from media_renamer.gui.main_window import MainWindow  # noqa: E402
from media_renamer.gui.styles import stylesheet  # noqa: E402


def main() -> int:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/screenshots/interface-preview.png")
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
    window.resize(1280, 820)
    window.show()
    application.processEvents()
    saved = window.grab().save(str(output))
    window.close()
    if not saved:
        raise RuntimeError(f"Could not save interface capture to {output}")
    print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
