"""Opt-in installer diagnostics using temporary settings and fictional media only."""

import sys
import time
from pathlib import Path

from PySide6.QtCore import QObject, QTimer
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from .assets import project_asset
from .settings import SettingsDialog


def require(condition, message):
    """Keep diagnostics active when PyInstaller compiles with optimization."""
    if not condition:
        raise RuntimeError(message)


class PackageSmokeTest(QObject):
    """Fail the executable on missing assets, scan errors, or broken Settings wiring."""

    def __init__(self, app, window, root: Path, check_settings: bool):
        super().__init__(window)
        self.app, self.window, self.root = app, window, root
        self.check_settings = check_settings
        self.stage = "start"
        self.failure = None
        self.deadline = time.monotonic() + 20
        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self._tick)
        self.previous_hook = sys.excepthook
        sys.excepthook = self._exception
        app.setQuitOnLastWindowClosed(False)

    def start(self):
        self.timer.start()

    def _exception(self, kind, value, traceback):
        self.failure = str(value)
        self.previous_hook(kind, value, traceback)

    def _tick(self):
        try:
            if self.failure or time.monotonic() > self.deadline:
                self.failure = self.failure or "Package smoke test timed out"
                self._finish(1)
                return
            if self.stage == "start":
                require(self.window.isVisible(), "Main window did not open")
                require(not self.app.windowIcon().isNull(), "Missing application icon")
                for theme in ("light", "dark"):
                    for name in ("check", "chevron"):
                        require(
                            QSvgRenderer(str(project_asset(f"ui/{name}-{theme}.svg"))).isValid(),
                            "Missing UI SVG",
                        )
                media = self.root / "Media"
                media.mkdir()
                (media / "Velora.Observatory.S01E01.1080p-DEMO.mkv").touch()
                self.window.path_edit.setText(str(media))
                self.window.scan_button.click()
                self.stage = "scan"
            elif self.stage == "scan" and self.window._scan_thread is None:
                require(self.window.current_report is not None, "Bundled scan failed")
                require(self.window.table.rowCount() == 1, "Missing preview row")
                require(self.window.apply_button.isEnabled(), "Valid proposal cannot be applied")
                if self.check_settings:
                    self.stage = "settings"
                    # Test the actual menu route, including its modal event loop.
                    QTimer.singleShot(0, self.window.settings_action.trigger)
                else:
                    self.stage = "done"
            elif self.stage == "settings":
                dialog = QApplication.activeModalWidget()
                if dialog is None:
                    return
                require(isinstance(dialog, SettingsDialog), "Unexpected modal dialog")
                require(dialog.isVisible(), "Settings did not open")
                require(
                    set(dialog.appearance_buttons) == {"system", "light", "dark"},
                    "Missing appearance options",
                )
                for mode in ("light", "dark"):
                    dialog.appearance_buttons[mode].click()
                require(
                    dialog.media_scope.width() >= dialog.media_scope.minimumSizeHint().width(),
                    "Media choices do not fit",
                )
                dialog.reject()
                self.stage = "done"
            elif self.stage == "done":
                require(self.window.update_controller.thread is None, "Unexpected update check")
                self._finish(0)
        except Exception as exc:
            self.failure = str(exc)
            self._finish(1)

    def _finish(self, result):
        # Even a failed diagnostic must not destroy a running QThread.
        self.window.close()
        if self.window._scan_thread is not None or self.window.operations.busy:
            return
        self.timer.stop()
        sys.excepthook = self.previous_hook
        if sys.stderr is not None:
            print(f"Reelabel package smoke: {self.failure or 'passed'}", file=sys.stderr)
        self.app.exit(result)
