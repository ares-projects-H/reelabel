"""Persistent, local-only preferences for the Reelabel desktop interface."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

APPEARANCE_KEY = "appearance/theme"
MEDIA_SCOPE_KEY = "scan/default_media_scope"
RECURSIVE_KEY = "scan/default_include_subfolders"
EXTRAS_KEY = "scan/default_include_extras"


@dataclass(frozen=True)
class SettingsValues:
    """Validated preferences used by the interface."""

    appearance: str = "system"
    media_scope: str = "all"
    recursive: bool = True
    include_extras: bool = False


def load_settings(store: QSettings) -> SettingsValues:
    """Read preferences while replacing unknown values with safe defaults."""

    appearance = str(store.value(APPEARANCE_KEY, "system"))
    if appearance not in {"system", "light", "dark"}:
        appearance = "system"
    media_scope = str(store.value(MEDIA_SCOPE_KEY, "all"))
    if media_scope not in {"all", "movies", "series"}:
        media_scope = "all"
    return SettingsValues(
        appearance=appearance,
        media_scope=media_scope,
        recursive=store.value(RECURSIVE_KEY, True, type=bool),
        include_extras=store.value(EXTRAS_KEY, False, type=bool),
    )


def save_settings(store: QSettings, values: SettingsValues) -> None:
    """Persist preferences in the platform's normal application-data store."""

    store.setValue(APPEARANCE_KEY, values.appearance)
    store.setValue(MEDIA_SCOPE_KEY, values.media_scope)
    store.setValue(RECURSIVE_KEY, values.recursive)
    store.setValue(EXTRAS_KEY, values.include_extras)
    store.sync()


class SettingsDialog(QDialog):
    """Small settings screen shared by macOS, Windows, and Linux."""

    def __init__(self, values: SettingsValues, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Reelabel Settings")
        self.setModal(True)
        self.setMinimumWidth(460)

        page = QVBoxLayout(self)
        page.setContentsMargins(24, 22, 24, 20)
        page.setSpacing(18)

        heading = QLabel("Application settings")
        heading.setObjectName("dialogTitle")
        explanation = QLabel(
            "These preferences are stored only on this computer. "
            "Reelabel does not send settings or filenames anywhere."
        )
        explanation.setObjectName("muted")
        explanation.setWordWrap(True)
        page.addWidget(heading)
        page.addWidget(explanation)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(14)

        self.appearance = QComboBox()
        self.appearance.addItem("System default", "system")
        self.appearance.addItem("Light", "light")
        self.appearance.addItem("Dark", "dark")
        self.appearance.setCurrentIndex(max(0, self.appearance.findData(values.appearance)))
        form.addRow("Appearance", self.appearance)

        self.media_scope = QComboBox()
        self.media_scope.addItem("All media", "all")
        self.media_scope.addItem("Movies only", "movies")
        self.media_scope.addItem("Series only", "series")
        self.media_scope.setCurrentIndex(max(0, self.media_scope.findData(values.media_scope)))
        form.addRow("Default media type", self.media_scope)

        self.recursive = QCheckBox("Include subfolders by default")
        self.recursive.setChecked(values.recursive)
        form.addRow("", self.recursive)

        self.include_extras = QCheckBox("Include extras by default")
        self.include_extras.setChecked(values.include_extras)
        form.addRow("", self.include_extras)
        page.addLayout(form)

        safety_note = QLabel(
            "Related images and NFO files remain disabled and unchecked by default. "
            "This safety control cannot be changed here."
        )
        safety_note.setObjectName("safeNotice")
        safety_note.setWordWrap(True)
        page.addWidget(safety_note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        if save_button is not None:
            save_button.setObjectName("primary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        page.addWidget(buttons)

    def values(self) -> SettingsValues:
        """Return the selections currently displayed by the dialog."""

        return SettingsValues(
            appearance=str(self.appearance.currentData()),
            media_scope=str(self.media_scope.currentData()),
            recursive=self.recursive.isChecked(),
            include_extras=self.include_extras.isChecked(),
        )
