"""Compact workspace layout, independent of scan/rename operation orchestration."""

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QProgressBar,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .assets import icon, project_asset
from .components import DropZone, ElidedLabel, button, fit_combo, label, row, rule
from .preview_table import PreviewTable
from .styles import colors


class Workspace(QWidget):
    """Build the validated layout; the owner connects actions to the shared API."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("root")
        page = QVBoxLayout(self)
        page.setContentsMargins(24, 16, 24, 16)
        page.setSpacing(16)
        logo = QLabel()
        logo.setPixmap(
            QPixmap(str(project_asset("reelabel-icon.png"))).scaled(
                36,
                36,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.history_button = button("History / Undo", "quiet")
        self.settings_button = button("Settings", "quiet")
        self.update_activity = label("", "updateActivity")
        self.update_activity.hide()
        page.addLayout(
            row(
                logo,
                label("Reelabel", "brand"),
                None,
                self.update_activity,
                self.history_button,
                self.settings_button,
            )
        )
        page.addWidget(rule())

        self.drop_zone = DropZone()
        source = QVBoxLayout(self.drop_zone)
        source.setContentsMargins(20, 14, 20, 14)
        source.setSpacing(10)
        self.folder_icon = QLabel()
        self.folder_icon.setFixedSize(36, 36)
        names = QVBoxLayout()
        names.setSpacing(2)
        self.folder_title = ElidedLabel()
        self.folder_title.setObjectName("strong")
        self.folder_title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.path_edit = QLineEdit()
        self.path_edit.setObjectName("pathInput")
        self.path_edit.setPlaceholderText("Choose or drop a media folder here")
        self.path_edit.setAccessibleName("Selected media folder path")
        self.path_edit.setAcceptDrops(False)
        self.path_edit.textChanged.connect(self._folder_changed)
        names.addWidget(self.folder_title)
        names.addWidget(self.path_edit)
        top = QHBoxLayout()
        top.addWidget(self.folder_icon)
        top.addLayout(names, 1)
        self.browse_button = button("Choose folder")
        self.scan_button = button("Preview changes")
        top.addWidget(self.browse_button)
        top.addWidget(self.scan_button)
        source.addLayout(top)
        self.media_type = QComboBox()
        self.media_type.addItems(("All media", "Movies only", "Series only"))
        self.media_type.setAccessibleName("Media type")
        fit_combo(self.media_type)
        self.recursive = QCheckBox("Include subfolders")
        self.recursive.setChecked(True)
        self.options_button = button("More options", "quiet")
        self.options_button.setCheckable(True)
        self.options_button.toggled.connect(self._toggle_options)
        source.addLayout(
            row(
                label("Media type", "muted"),
                self.media_type,
                self.recursive,
                None,
                self.options_button,
            )
        )
        self.extra_panel = QWidget()
        options = QVBoxLayout(self.extra_panel)
        options.setContentsMargins(0, 0, 0, 0)
        self.extras = QCheckBox("Include extras, trailers and bonus files")
        self.sidecars = QCheckBox("Find related images / NFO")
        self.sidecars.setToolTip(
            "Off by default. Related files are listed separately and never selected automatically."
        )
        options.addLayout(row(self.extras, self.sidecars, None))
        options.addWidget(
            label(
                "Related files stay unchecked. Permanent deletion always needs a separate confirmation.",
                "muted",
                True,
            )
        )
        self.extra_panel.hide()
        source.addWidget(self.extra_panel)
        page.addWidget(self.drop_zone)

        self.heading = QWidget()
        heading = QVBoxLayout(self.heading)
        heading.setContentsMargins(0, 0, 0, 0)
        heading.setSpacing(5)
        heading.addWidget(label("Review your changes", "heading"))
        heading.addWidget(
            label("Compare names below. Nothing changes until you apply your selection.", "muted")
        )
        page.addWidget(self.heading)
        self.review_toolbar = QWidget()
        toolbar = QHBoxLayout(self.review_toolbar)
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(6)
        self.filter_buttons = {}
        self.filter_group = QButtonGroup(self)
        self.filter_group.setExclusive(True)
        for category in ("all", "ready", "review", "ignored"):
            b = button(f"{category.title()} 0", "filter")
            b.setCheckable(True)
            self.filter_group.addButton(b)
            self.filter_buttons[category] = b
            toolbar.addWidget(b)
        toolbar.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Find a filename…")
        self.search.setAccessibleName("Filter preview filenames")
        self.search.setFixedWidth(210)
        self.edit_button = button("Edit name")
        self.edit_button.setEnabled(False)
        toolbar.addWidget(self.search)
        toolbar.addWidget(self.edit_button)
        page.addWidget(self.review_toolbar)

        self.stack = QStackedWidget()
        self.table = PreviewTable()
        self.stack.addWidget(self.table)
        # The entire outlined area is a real target, including the instructions
        # and button. Children do not accept drops, so Qt routes them here.
        self.empty_page = DropZone()
        self.empty_page.setProperty("welcome", True)
        empty = QVBoxLayout(self.empty_page)
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.setContentsMargins(24, 24, 24, 24)
        empty.setSpacing(14)
        self.empty_icon = QLabel()
        self.empty_icon.setFixedSize(48, 48)
        self.empty_title = label("Drop a media folder here", "heading", True)
        self.empty_hint = label(
            "Anywhere inside this outlined area. Your files stay unchanged.", "muted", True
        )
        for text in (self.empty_title, self.empty_hint):
            text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            text.setMinimumWidth(440)
        self.empty_browse = button("Choose a media folder", "primary")
        for item in (self.empty_icon, self.empty_title, self.empty_hint, self.empty_browse):
            empty.addWidget(item, 0, Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.empty_page)
        self.no_results_page = QWidget()
        no_results = QVBoxLayout(self.no_results_page)
        no_results.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clear_filters = button("Clear filters")
        self.clear_filters.clicked.connect(self._clear_filters)
        for item in (
            label("No matching filenames", "heading"),
            label("Try another search or clear the preview filters.", "muted"),
            self.clear_filters,
        ):
            no_results.addWidget(item, 0, Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.no_results_page)
        self.scan_page = QWidget()
        scan = QVBoxLayout(self.scan_page)
        scan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_title = label("Preparing your preview", "heading")
        self.progress_hint = label("Reading filenames. Your files are unchanged.", "muted")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedSize(320, 5)
        for item in (self.progress_title, self.progress_hint, self.progress):
            scan.addWidget(item, 0, Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.scan_page)
        page.addWidget(self.stack, 1)
        self.related_panel = QWidget()
        related = QVBoxLayout(self.related_panel)
        related.setContentsMargins(0, 0, 0, 0)
        self.related_title = label("Related images / NFO — optional permanent deletion", "strong")
        related.addWidget(self.related_title)
        self.related_list = QListWidget()
        self.related_list.setAccessibleName(
            "Related images and NFO; check only files to delete permanently"
        )
        self.related_list.setMaximumHeight(100)
        related.addWidget(self.related_list)
        self.related_panel.hide()
        page.addWidget(self.related_panel)
        self.detail = label(
            "Double-click a proposed name to edit it, or select a row and choose Edit name.",
            "hint",
            True,
        )
        page.addWidget(self.detail)
        page.addWidget(rule())
        footer = QHBoxLayout()
        messages = QVBoxLayout()
        messages.setSpacing(4)
        self.summary = label("No folder selected", "strong", True)
        self.notice = label("Choose a folder to prepare a read-only preview.", "muted", True)
        messages.addWidget(self.summary)
        messages.addWidget(self.notice)
        footer.addLayout(messages, 1)
        self.apply_button = button("Apply selected changes", "primary")
        self.apply_button.setEnabled(False)
        footer.addWidget(self.apply_button)
        page.addLayout(footer)
        self._folder_changed("")

    def _folder_changed(self, text: str) -> None:
        self.folder_title.set_full_text(
            Path(text).name if text.strip() else "Choose a media folder"
        )
        self.path_edit.setToolTip(text)
        self.browse_button.setText("Change folder" if text.strip() else "Choose folder")

    def _toggle_options(self, checked: bool) -> None:
        self.extra_panel.setVisible(checked)
        self.options_button.setText("Fewer options" if checked else "More options")

    def set_theme(self, dark: bool) -> None:
        c = colors(dark)
        self.folder_icon.setPixmap(icon("folder", c["accent"]).pixmap(30, 30))
        self.empty_icon.setPixmap(icon("folder", c["accent"]).pixmap(48, 48))
        for control, glyph in (
            (self.history_button, "history"),
            (self.settings_button, "settings"),
            (self.edit_button, "edit"),
            (self.scan_button, "refresh"),
        ):
            control.setIcon(icon(glyph, c["ink"]))
            control.setIconSize(QSize(17, 17))
        self.table.set_theme(dark)

    def resizeEvent(self, event) -> None:  # noqa: N802
        # On compact displays, keep actions and editing guidance, not a large heading.
        self.heading.setVisible(self.height() >= 700)
        super().resizeEvent(event)

    def show_preview(self) -> None:
        self.stack.setCurrentWidget(self.table)
        self.review_toolbar.show()
        self.detail.show()

    def show_filtered_preview(self) -> None:
        self.show_preview()
        if not any(not self.table.isRowHidden(i) for i in range(self.table.rowCount())):
            self.stack.setCurrentWidget(self.no_results_page)

    def _clear_filters(self) -> None:
        self.search.clear()
        self.filter_buttons["all"].click()

    def show_empty(self, title: str | None = None, hint: str | None = None) -> None:
        self.stack.setCurrentWidget(self.empty_page)
        self.empty_title.setText(title or "Drop a media folder here")
        self.empty_hint.setText(
            hint or "Anywhere inside this outlined area. Your files stay unchanged."
        )
        self.review_toolbar.hide()
        self.detail.hide()
        self.related_panel.hide()

    def show_busy(self, title: str, hint: str) -> None:
        self.progress_title.setText(title)
        self.progress_hint.setText(hint)
        self.stack.setCurrentWidget(self.scan_page)
        self.review_toolbar.hide()
        self.detail.hide()
        self.related_panel.hide()
