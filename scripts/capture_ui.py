"""Capture the validation-one interface in an offscreen Qt session."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_STYLE_OVERRIDE", "Fusion")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from reelabel.gui.main_window import MainWindow  # noqa: E402


def main() -> int:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/screenshots/interface-preview.png")
    output.parent.mkdir(parents=True, exist_ok=True)
    application = QApplication.instance() or QApplication([])
    temporary = TemporaryDirectory(prefix="reelabel-capture-")
    settings = QSettings(str(Path(temporary.name) / "settings.ini"), QSettings.Format.IniFormat)
    settings.setValue("appearance", "dark")
    window = MainWindow(demo=True, settings_store=settings)
    window.theme_controller.set_appearance("dark")
    window.resize(1280, 820)
    window.show()
    application.processEvents()
    saved = window.grab().save(str(output))
    window.close()
    temporary.cleanup()
    if not saved:
        raise RuntimeError(f"Could not save interface capture to {output}")
    print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
