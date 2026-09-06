"""Persistent, local-only preferences for the Reelabel desktop interface."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from reelabel._version import __version__

from .components import card, fit_combo, label, row

APPEARANCE_KEY = "appearance/theme"
MEDIA_SCOPE_KEY = "scan/default_media_scope"
RECURSIVE_KEY = "scan/default_include_subfolders"
EXTRAS_KEY = "scan/default_include_extras"
APPLY_CONFIRMATION_KEY = "confirmations/show_before_apply"


@dataclass(frozen=True)
class SettingsValues:
    """Validated preferences used by the interface."""

    appearance: str = "system"
    media_scope: str = "all"
    recursive: bool = True
    include_extras: bool = False
    show_apply_confirmation: bool = True


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
        show_apply_confirmation=store.value(
            APPLY_CONFIRMATION_KEY,
            True,
            type=bool,
        ),
    )


def save_settings(store: QSettings, values: SettingsValues) -> None:
    """Persist preferences in the platform's normal application-data store."""

    store.setValue(APPEARANCE_KEY, values.appearance)
    store.setValue(MEDIA_SCOPE_KEY, values.media_scope)
    store.setValue(RECURSIVE_KEY, values.recursive)
    store.setValue(EXTRAS_KEY, values.include_extras)
    store.setValue(APPLY_CONFIRMATION_KEY, values.show_apply_confirmation)
    store.sync()


class SettingsDialog(QDialog):
    """Scrollable preferences with bounded controls and a live, reversible theme preview."""

    check_updates_requested = Signal()
    appearance_preview = Signal(str)

    def __init__(
        self,
        values: SettingsValues,
        parent: QWidget | None = None,
        *,
        app_version: str = __version__,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Reelabel Settings")
        self.setModal(True)
        self.setMinimumSize(550, 420)
        self.resize(680, min(800, self.screen().availableGeometry().height() - 80))
        page = QVBoxLayout(self)
        page.setContentsMargins(24, 24, 24, 20)
        page.setSpacing(16)
        page.addWidget(label("Settings", "heading"))
        page.addWidget(
            label(
                "Preferences stay on this computer. Filenames are never sent anywhere.",
                "muted",
                True,
            )
        )
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        body = QWidget()
        groups = QVBoxLayout(body)
        groups.setContentsMargins(0, 0, 0, 0)
        groups.setSpacing(14)

        appearance, layout = card()
        layout.addWidget(label("Appearance", "strong"))
        layout.addWidget(label("Choose how Reelabel looks.", "muted"))
        self.appearance_group = QButtonGroup(self)
        self.appearance_group.setExclusive(True)
        choices = QHBoxLayout()
        self.appearance_buttons = {}
        for value in ("system", "light", "dark"):
            choice = QPushButton(value.title())
            choice.setObjectName("segment")
            choice.setProperty("value", value)
            choice.setCheckable(True)
            choice.setChecked(values.appearance == value)
            self.appearance_group.addButton(choice)
            self.appearance_buttons[value] = choice
            choices.addWidget(choice, 1)
        self.appearance_group.buttonToggled.connect(
            lambda b, checked: (
                self.appearance_preview.emit(b.property("value")) if checked else None
            )
        )
        layout.addLayout(choices)
        groups.addWidget(appearance)

        defaults, layout = card()
        layout.addWidget(label("Scan defaults", "strong"))
        self.media_scope = QComboBox()
        self.media_scope.setAccessibleName("Default media type")
        for text, value in (
            ("All media", "all"),
            ("Movies only", "movies"),
            ("Series only", "series"),
        ):
            self.media_scope.addItem(text, value)
        self.media_scope.setCurrentIndex(max(0, self.media_scope.findData(values.media_scope)))
        fit_combo(self.media_scope)
        layout.addLayout(row(label("Media type"), None, self.media_scope))
        self.recursive = QCheckBox("Include subfolders")
        self.recursive.setChecked(values.recursive)
        self.include_extras = QCheckBox("Include extras, trailers and bonus files")
        self.include_extras.setChecked(values.include_extras)
        layout.addWidget(self.recursive)
        layout.addWidget(self.include_extras)
        groups.addWidget(defaults)

        safety, layout = card()
        layout.addWidget(label("Before applying changes", "strong"))
        self.apply_confirmation = QCheckBox("Show a confirmation before renaming")
        self.apply_confirmation.setChecked(values.show_apply_confirmation)
        self.apply_confirmation.setToolTip(
            "Re-enable this after choosing Don't show again in the Apply dialog."
        )
        layout.addWidget(self.apply_confirmation)
        layout.addWidget(
            label(
                "Destination checks, automatic restoration and History / Undo always stay active. "
                "Images/NFO stay unchecked; permanent deletion always needs a separate confirmation.",
                "muted",
                True,
            )
        )
        groups.addWidget(safety)

        updates_card, layout = card()
        self.current_version = label(f"Installed version: {app_version}", "muted")
        layout.addLayout(row(label("Updates", "strong"), None, self.current_version))
        layout.addWidget(
            label(
                "Reelabel connects to GitHub only when you click this button. "
                "It never downloads or installs an update automatically.",
                "muted",
                True,
            )
        )
        self.check_updates_button = QPushButton("Check for updates")
        self.check_updates_button.clicked.connect(self.check_updates_requested.emit)
        layout.addLayout(row(self.check_updates_button, None))
        self.update_status = label("", "muted", True)
        self.update_status.hide()
        layout.addWidget(self.update_status)
        groups.addWidget(updates_card)
        groups.addStretch()
        self.scroll.setWidget(body)
        page.addWidget(self.scroll, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("primary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        page.addLayout(row(label("Save to keep your changes.", "muted"), None, buttons))

    def set_update_checking(self, checking: bool) -> None:
        self.check_updates_button.setEnabled(not checking)
        self.check_updates_button.setText("Checking…" if checking else "Check for updates")
        if checking:
            self.set_update_status("Contacting the official GitHub release page…")

    def set_update_status(self, text: str) -> None:
        """Keep feedback reachable even on a small display."""
        self.update_status.setText(text)
        self.update_status.show()
        self.scroll.ensureWidgetVisible(self.update_status)

    def values(self) -> SettingsValues:
        return SettingsValues(
            appearance=self.appearance_group.checkedButton().property("value"),
            media_scope=str(self.media_scope.currentData()),
            recursive=self.recursive.isChecked(),
            include_extras=self.include_extras.isChecked(),
            show_apply_confirmation=self.apply_confirmation.isChecked(),
        )
