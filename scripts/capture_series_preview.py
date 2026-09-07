"""Capture a Reelabel preview containing only invented series filenames."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_STYLE_OVERRIDE", "Fusion")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from reelabel.gui import main_window as gui_main_window  # noqa: E402

# These names are intentionally fictional so public screenshots never expose a
# real media library or depend on copyrighted artwork.
SERIES_ROWS = (
    gui_main_window.DemoRow(
        "Ready",
        "Aurora.Archive.S01.1080p.WEB-DL.x265-DEMO",
        "Aurora Archive S01",
        "FOLDER",
    ),
    gui_main_window.DemoRow(
        "Ready",
        "[DemoGroup] Aurora.Archive.S01E01.1080p.WEB-DL.x265.mkv",
        "Aurora Archive S01 E01.mkv",
        "MKV",
    ),
    gui_main_window.DemoRow(
        "Ready",
        "[DemoGroup] Aurora.Archive.S01E01.1080p.WEB-DL.x265.ass",
        "Aurora Archive S01 E01.ass",
        "ASS",
    ),
    gui_main_window.DemoRow(
        "Ready",
        "[DemoGroup] Aurora.Archive.S01E02.1080p.WEB-DL.x265.mkv",
        "Aurora Archive S01 E02.mkv",
        "MKV",
    ),
    gui_main_window.DemoRow(
        "Ready",
        "[DemoGroup] Aurora.Archive.S01E02.1080p.WEB-DL.x265.en.srt",
        "Aurora Archive S01 E02.en.srt",
        "SRT",
    ),
    gui_main_window.DemoRow(
        "Ready",
        "[DemoGroup] Aurora.Archive.S01E03.1080p.WEB-DL.x265.mkv",
        "Aurora Archive S01 E03.mkv",
        "MKV",
    ),
    gui_main_window.DemoRow(
        "Ready",
        "[DemoGroup] Aurora.Archive.S01E03.1080p.WEB-DL.x265.fr.srt",
        "Aurora Archive S01 E03.fr.srt",
        "SRT",
    ),
)


def main() -> int:
    """Render the invented series preview to a deterministic PNG file."""

    output = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/screenshots/series-preview.png")
    output.parent.mkdir(parents=True, exist_ok=True)
    application = QApplication.instance() or QApplication([])
    temporary = TemporaryDirectory(prefix="reelabel-capture-")
    settings = QSettings(str(Path(temporary.name) / "settings.ini"), QSettings.Format.IniFormat)
    settings.setValue("appearance", "dark")

    # Replace the built-in demo before constructing the window so Qt creates
    # the summary cards only once and the offscreen layout remains stable.
    gui_main_window.DEMO_ROWS = SERIES_ROWS
    window = gui_main_window.MainWindow(demo=True, settings_store=settings)
    window.theme_controller.set_appearance("dark")
    window.resize(1440, 980)
    window.path_edit.setText("/Media/Library/Aurora Archive S01")
    window.media_type.setCurrentText("Series only")
    window._load_demo()
    window.show()
    application.processEvents()
    saved = window.grab().save(str(output))
    window.close()
    temporary.cleanup()
    if not saved:
        raise RuntimeError(f"Could not save series preview to {output}")
    print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
