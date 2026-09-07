"""Render production widgets with temporary preferences and invented sample data."""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from reelabel.gui.history import HistoryDialog  # noqa: E402
from reelabel.gui.main_window import MainWindow  # noqa: E402
from reelabel.gui.settings import SettingsDialog  # noqa: E402


def main():
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "build/modern-ui-evidence")
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    with TemporaryDirectory(prefix="reelabel-visual-check-") as temporary:
        store = QSettings(str(Path(temporary) / "preferences.ini"), QSettings.IniFormat)
        window = MainWindow(demo=True, settings_store=store)

        def capture(widget, name):
            widget.show()
            app.processEvents()
            if not widget.grab().save(str(output / f"{name}.png")):
                raise RuntimeError(f"Could not save {name}")

        for mode in ("light", "dark"):
            window.theme_controller.set_appearance(mode)
            window.resize(1280, 820)
            window._load_demo()
            capture(window, f"preview-{mode}")
            window.resize(1024, 620)
            capture(window, f"compact-{mode}")
            settings = SettingsDialog(replace(window._preferences, appearance=mode), window)
            capture(settings, f"settings-{mode}")
            settings.media_scope.showPopup()
            capture(settings.media_scope.view().window(), f"media-popup-{mode}")
            settings.media_scope.hidePopup()
            settings.close()
            history = HistoryDialog(Path(temporary) / "history", window)
            capture(history, f"history-empty-{mode}")
            history.close()
            message, _ = window._confirmation_dialog(
                "Apply selected changes?",
                "Rename 8 files and 1 folder?",
                "Reelabel checks destinations before renaming. Original names are saved in History / Undo.",
                "Rename selected items",
            )
            capture(message, f"confirmation-{mode}")
            message.close()
            window.path_edit.clear()
            window._show_empty_state()
            window.notice.setText("Choose a folder to prepare a read-only preview.")
            capture(window, f"empty-{mode}")
        window.close()
    print(output.resolve())


if __name__ == "__main__":
    main()
