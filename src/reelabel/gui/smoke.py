"""Opt-in installer diagnostics using temporary settings and fictional media only."""

import sys
import time
from pathlib import Path

from PySide6.QtCore import QMimeData, QObject, QPointF, Qt, QTimer, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from reelabel import __version__

from .assets import project_asset
from .components import combo_text_width
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
                # Exercise the advertised central target in the real bundle,
                # rather than bypassing the drop handler by setting its path.
                target = self.window.workspace.empty_page
                require(target.isVisible(), "Welcome drop area is not visible")
                mime = QMimeData()
                mime.setUrls([QUrl.fromLocalFile(str(media))])
                enter = QDragEnterEvent(
                    target.rect().center(),
                    Qt.DropAction.CopyAction,
                    mime,
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier,
                )
                QApplication.sendEvent(target, enter)
                require(enter.isAccepted(), "Welcome area rejected the folder drag")
                drop = QDropEvent(
                    QPointF(target.rect().center()),
                    Qt.DropAction.CopyAction,
                    mime,
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier,
                )
                QApplication.sendEvent(target, drop)
                require(drop.isAccepted(), "Welcome area rejected the folder drop")
                require(self.window.path_edit.text() == str(media), "Drop did not select folder")
                require(self.window._scan_thread is None, "Drop unexpectedly started scanning")
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
                    dialog.current_version.text() == f"Installed version: {__version__}",
                    "Settings version does not match the package",
                )
                require(
                    set(dialog.appearance_buttons) == {"system", "light", "dark"},
                    "Missing appearance options",
                )
                for mode in ("light", "dark"):
                    dialog.appearance_buttons[mode].click()
                self.stage = "settings_layout"
            elif self.stage == "settings_layout":
                # Measure the rendered result, after Qt processes font/style
                # changes and the layout pass caused by the appearance buttons.
                dialog = QApplication.activeModalWidget()
                require(isinstance(dialog, SettingsDialog), "Settings closed unexpectedly")
                require(
                    combo_text_width(dialog.media_scope)
                    >= max(
                        dialog.media_scope.fontMetrics().horizontalAdvance(
                            dialog.media_scope.itemText(i)
                        )
                        for i in range(dialog.media_scope.count())
                    ),
                    f"Media choices do not fit: label space={combo_text_width(dialog.media_scope)}, font={dialog.media_scope.font().toString()}",
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
