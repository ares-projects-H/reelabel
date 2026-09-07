"""Explicit update checks, with feedback independent of scan/rename status."""

from __future__ import annotations

import weakref
from collections.abc import Callable

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox

from reelabel import updates

from .settings import SettingsDialog
from .tasks import TaskThread

FAILURE_MESSAGES = {
    "network": "Reelabel could not reach GitHub. Check your connection and try again. Renaming remains fully available offline.",
    "version": "Reelabel could not verify the release version returned by GitHub.",
    "response": "GitHub returned release information that Reelabel could not verify.",
    "unexpected": "The update check could not be completed safely.",
}


class UpdateController(QObject):
    """One finite worker shared by Help and Settings; no startup or periodic checks."""

    def __init__(self, parent, action, activity, checker: Callable):
        super().__init__(parent)
        self.window = parent
        self.action = action
        self.activity = activity
        self.checker = checker
        self.thread: TaskThread | None = None
        self.targets = []
        self.closing = False

    def attach_settings(self, dialog: SettingsDialog) -> None:
        self.targets.append(weakref.ref(dialog))
        dialog.set_update_checking(self.thread is not None)

    def _visible_targets(self):
        visible = []
        for reference in self.targets:
            target = reference()
            try:
                if target is not None and target.isVisible():
                    visible.append(target)
            except RuntimeError:
                pass  # The Settings window was destroyed while the request ran.
        return visible

    def start(self, target: SettingsDialog | None = None) -> None:
        if self.closing:
            return
        if target is not None and not any(ref() is target for ref in self.targets):
            self.attach_settings(target)
        if self.thread is not None:
            if target is not None:
                target.set_update_checking(True)
            return
        self.action.setEnabled(False)
        self.activity.setText("Checking for updates…")
        self.activity.show()
        for dialog in self._visible_targets():
            dialog.set_update_checking(True)
        self.thread = TaskThread(self.checker, self)
        self.thread.finished.connect(self._finished)
        self.thread.start()

    @Slot()
    def _finished(self) -> None:
        task = self.thread
        task.wait()
        result, error = task.result, task.error
        task.deleteLater()
        self.thread = None
        self.activity.hide()
        self.action.setEnabled(True)
        targets = self._visible_targets()
        self.targets = [weakref.ref(dialog) for dialog in targets]
        for dialog in targets:
            dialog.set_update_checking(False)
        if self.closing:
            QTimer.singleShot(0, self.window.close)
            return
        parent = targets[-1] if targets else None
        if error is not None or not isinstance(result, updates.UpdateCheckResult):
            reason = next(
                (
                    key
                    for error_type, key in (
                        (updates.UpdateNetworkError, "network"),
                        (updates.UpdateVersionError, "version"),
                        (updates.UpdateResponseError, "response"),
                    )
                    if isinstance(error, error_type)
                ),
                "unexpected",
            )
            for dialog in targets:
                dialog.set_update_status(FAILURE_MESSAGES[reason])
            QTimer.singleShot(0, lambda: self.show_failure(reason, parent))
            return
        if result.update_available:
            status = f"Reelabel {result.latest_version} is available."
        elif result.current_is_newer:
            status = f"This Reelabel {result.current_version} build is newer than the latest published release ({result.latest_version})."
        else:
            status = f"Reelabel {result.current_version} is up to date."
        for dialog in targets:
            dialog.set_update_status(status)
        # Yield once so re-enabled controls repaint before a modal result opens.
        QTimer.singleShot(0, lambda: self.show_result(result, parent))

    def _message(self, title, text, parent=None):
        # A deferred result may outlive the Settings dialog that requested it.
        try:
            if parent is not None and not parent.isVisible():
                parent = None
        except RuntimeError:
            parent = None
        message = QMessageBox(parent or self.window)
        message.setTextFormat(Qt.TextFormat.PlainText)
        message.setWindowTitle(title)
        message.setText(text)
        message.setWindowModality(Qt.WindowModality.ApplicationModal)
        return message

    def _present(self, message):
        message.show()
        message.raise_()
        message.activateWindow()
        message.exec()

    def show_information(self, parent, title, text) -> None:
        if self.closing:
            return
        message = self._message(title, text, parent)
        message.setStandardButtons(QMessageBox.StandardButton.Ok)
        self._present(message)

    def show_result(self, result, parent=None) -> None:
        if self.closing:
            return
        if result.current_is_newer:
            self.show_information(
                parent,
                "No update available",
                f"This Reelabel {result.current_version} build is newer than the latest published release ({result.latest_version}).",
            )
        elif not result.update_available:
            self.show_information(
                parent,
                "Reelabel is up to date",
                f"You are using the latest published version ({result.current_version}).",
            )
        else:
            message = self._message(
                "Reelabel update available",
                f"Reelabel {result.latest_version} is available.",
                parent,
            )
            message.setInformativeText(
                "Open the official GitHub release page to review and download it? Reelabel will not download or install anything automatically."
            )
            message.setStandardButtons(QMessageBox.StandardButton.Cancel)
            open_button = message.addButton("Open download page", QMessageBox.ButtonRole.AcceptRole)
            open_button.setObjectName("primary")
            self._present(message)
            if message.clickedButton() is open_button:
                QDesktopServices.openUrl(QUrl(result.release_url))

    def show_failure(self, reason, parent=None) -> None:
        if self.closing:
            return
        message = self._message("Could not check for updates", FAILURE_MESSAGES[reason], parent)
        message.setStandardButtons(QMessageBox.StandardButton.Close)
        retry = message.addButton("Try again", QMessageBox.ButtonRole.AcceptRole)
        self._present(message)
        if message.clickedButton() is retry:
            # Any still-visible Settings window is already registered; avoid
            # retaining the dialog that may have closed during the error message.
            QTimer.singleShot(0, self.start)
