"""Main window for the Reelabel desktop application."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from PySide6.QtCore import (
    QSettings,
    QSignalBlocker,
    QStandardPaths,
    Qt,
    QThread,
    QTimer,
    Slot,
)
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QIcon,
    QKeySequence,
    QPixmap,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
)

from reelabel import __version__, api, core, updates

from .assets import project_asset
from .batch_edits import batch_episode_name, batch_movie_sidecar_name
from .history import HistoryDialog, HistoryEntry, read_history
from .preview_table import CATEGORY_ROLE, DETAIL_ROLE, EDIT_BASE_ROLE, KIND_ROLE, SOURCE_ROLE
from .settings import SettingsDialog, load_settings, save_settings
from .tasks import OperationRunner, TaskThread
from .theme import ThemeController
from .update_controller import UpdateController
from .workspace import Workspace

REASON_TRANSLATIONS = {
    "nom vidéo normalisé": "Normalized video filename.",
    "sous-titre associé à la vidéo": "Subtitle matched to its video.",
    "extra identifié (option --include-extras requise)": (
        "Identified as an extra; enable Include extras to include it."
    ),
    "titre insuffisant ou ambigu": "The title is insufficient or ambiguous.",
    "série exclue par --movies": "Series excluded by the Movies only option.",
    "film exclu par --series": "Movie excluded by the Series only option.",
    "sous-titre sans association certaine": (
        "No sufficiently certain video match was found for this subtitle."
    ),
    "plusieurs fichiers visent la même destination": (
        "More than one file has the same destination."
    ),
    "destination existante ou collision de casse": (
        "The destination exists or differs only by letter case."
    ),
    "folder name normalized": "Normalized folder name.",
}


@dataclass(frozen=True)
class DemoRow:
    """One representative row used only for screenshots and UI tests."""

    status: str
    original: str
    proposed: str
    media_type: str
    selected: bool = True


DEMO_ROWS = (
    DemoRow(
        "Ready",
        "Velora.Observatory.S02.1080p.x265-DEMO",
        "Velora Observatory S02",
        "FOLDER",
    ),
    DemoRow(
        "Ready",
        "[SampleGroup] The Copper Comet 2022 WEB-DL.mkv",
        "The Copper Comet (2022).mkv",
        "MKV",
    ),
    DemoRow(
        "Ready",
        "Letters.From.Velora.2018.1080p.BluRay.x264.mkv",
        "Letters From Velora (2018).mkv",
        "MKV",
    ),
    DemoRow(
        "Ready",
        "The Clockwork Orchard.2020.DVDRip.XviD.AC3-DEMO.avi",
        "The Clockwork Orchard (2020).avi",
        "AVI",
    ),
    DemoRow(
        "Ready",
        "The Clockwork Orchard.2020.DVDRip.XviD.AC3-DEMO.idx",
        "The Clockwork Orchard (2020).idx",
        "IDX",
    ),
    DemoRow(
        "Ready",
        "The Clockwork Orchard.2020.DVDRip.XviD.AC3-DEMO.sub",
        "The Clockwork Orchard (2020).sub",
        "SUB",
    ),
    DemoRow(
        "Ready",
        "Velora.Observatory.EP01.1080p.WEB-DL.DDP2.0.H.264-DEMO.mkv",
        "Velora Observatory S02 E01.mkv",
        "MKV",
    ),
    DemoRow(
        "Ready",
        "Velora.Observatory.EP01.1080p.WEB-DL.DDP2.0.H.264-DEMO.ass",
        "Velora Observatory S02 E01.ass",
        "ASS",
    ),
    DemoRow(
        "Review",
        "Velora Signal - English subtitles [DEMO][1234ABCD].mkv",
        "Velora Signal - English Subtitles.mkv",
        "MKV",
        False,
    ),
)


class MainWindow(QMainWindow):
    """Modern interface for previewing and safely applying media renames."""

    def __init__(
        self,
        demo: bool = False,
        settings_store: QSettings | None = None,
        update_checker: Callable[[], updates.UpdateCheckResult] | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Reelabel")
        self.setMinimumSize(900, 600)
        self.resize(1280, 820)
        icon_path = project_asset("reelabel-icon.png")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._settings_store = settings_store or QSettings(
            "ares-projects-H",
            "Reelabel",
        )
        self._preferences = load_settings(self._settings_store)
        self._update_checker = update_checker or updates.check_for_updates
        self.theme_controller = ThemeController(self)
        self.theme_controller.changed.connect(self._theme_changed)
        self._apply_theme()

        self.current_report: api.ScanReport | None = None
        self.operations = OperationRunner(self)
        self.operations.completed.connect(self._operation_completed)
        self._operation_kind = ""
        self._operation_context = None
        self._history_dialog = None
        self._source_revision = 0
        self._scan_revision = 0
        self._scan_thread: TaskThread | None = None
        self._close_requested = False
        self._loading_table = False
        self._active_filter = "all"
        self._sort_column: int | None = None
        self._sort_order = Qt.SortOrder.AscendingOrder
        self.filter_buttons: dict[str, QPushButton] = {}
        self._build_ui()
        self._build_menus()
        self.update_controller = UpdateController(
            self,
            self.check_updates_action,
            self.workspace.update_activity,
            self._update_checker,
        )
        self._apply_scan_defaults()
        self.path_edit.textChanged.connect(self._invalidate_preview)
        self.media_type.currentIndexChanged.connect(self._invalidate_preview)
        for control in (self.recursive, self.extras, self.sidecars):
            control.toggled.connect(self._invalidate_preview)
        if demo:
            self._load_demo()
        else:
            self._show_empty_state()

    def _theme_changed(self, dark: bool) -> None:
        self._dark = dark
        if hasattr(self, "workspace"):
            self.workspace.set_theme(dark)

    def _apply_theme(self) -> None:
        self.theme_controller.set_appearance(self._preferences.appearance)

    def _apply_scan_defaults(self) -> None:
        """Copy saved scan defaults into the main-window controls."""

        scope_index = {"all": 0, "movies": 1, "series": 2}[self._preferences.media_scope]
        self.media_type.setCurrentIndex(scope_index)
        self.recursive.setChecked(self._preferences.recursive)
        self.extras.setChecked(self._preferences.include_extras)
        # Related image/NFO discovery is intentionally not configurable as a
        # default. It must remain a deliberate choice in every session.
        self.sidecars.setChecked(False)

    def _build_ui(self) -> None:
        self.workspace = Workspace(self)
        # Named controls stay discoverable for operation wiring and GUI tests.
        for name in (
            "path_edit",
            "drop_zone",
            "media_type",
            "recursive",
            "extras",
            "sidecars",
            "scan_button",
            "table",
            "notice",
            "apply_button",
            "filter_buttons",
            "search",
            "edit_button",
            "related_list",
        ):
            setattr(self, name, getattr(self.workspace, name))
        self.setCentralWidget(self.workspace)
        self.workspace.browse_button.clicked.connect(self._browse)
        self.workspace.empty_browse.clicked.connect(self._browse)
        self.workspace.history_button.clicked.connect(self._show_history)
        self.workspace.settings_button.clicked.connect(self._show_settings)
        self.drop_zone.folder_dropped.connect(self._set_folder)
        self.scan_button.clicked.connect(self._scan_or_cancel)
        self.apply_button.clicked.connect(self._apply_selected)
        self.table.itemChanged.connect(self._table_item_changed)
        self.table.itemSelectionChanged.connect(self._update_edit_button)
        self.table.horizontalHeader().sectionClicked.connect(self._sort_table_by_column)
        self.edit_button.clicked.connect(self._edit_selected_name)
        self.search.textChanged.connect(lambda: self._set_filter(self._active_filter))
        self.related_list.itemChanged.connect(lambda: self._update_selection_summary())
        for category, control in self.filter_buttons.items():
            control.toggled.connect(
                lambda checked, selected=category: (
                    self._set_filter(selected)
                    if checked and selected != self._active_filter
                    else None
                )
            )
        self.workspace.set_theme(self._dark)

    def _build_menus(self) -> None:
        """Create cross-platform menus with native macOS application roles."""

        menu_bar = self.menuBar()
        menu_bar.setNativeMenuBar(True)

        self.file_menu = menu_bar.addMenu("&File")

        self.choose_folder_action = QAction("Choose Folder…", self)
        self.choose_folder_action.setShortcut(QKeySequence.StandardKey.Open)
        self.choose_folder_action.triggered.connect(self._browse)
        self.file_menu.addAction(self.choose_folder_action)

        self.preview_action = QAction("Preview Changes", self)
        self.preview_action.setShortcut(QKeySequence("Ctrl+R"))
        self.preview_action.triggered.connect(self._scan_or_cancel)
        self.file_menu.addAction(self.preview_action)
        self.edit_name_action = QAction("Edit Proposed Name", self)
        self.edit_name_action.setShortcut(QKeySequence("F2"))
        self.edit_name_action.triggered.connect(self._edit_selected_name)
        self.file_menu.addAction(self.edit_name_action)

        self.history_action = QAction("History / Undo…", self)
        self.history_action.triggered.connect(self._show_history)
        self.file_menu.addAction(self.history_action)

        self.file_menu.addSeparator()
        self.settings_action = QAction("Settings…", self)
        # PreferencesRole moves this action into Reelabel → Settings… on macOS.
        self.settings_action.setMenuRole(QAction.MenuRole.PreferencesRole)
        self.settings_action.triggered.connect(self._show_settings)
        self.file_menu.addAction(self.settings_action)

        self.file_menu.addSeparator()
        self.quit_action = QAction("Quit Reelabel", self)
        self.quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.quit_action.setMenuRole(QAction.MenuRole.QuitRole)
        self.quit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.quit_action)

        self.help_menu = menu_bar.addMenu("&Help")
        self.user_guide_action = QAction("Reelabel User Guide", self)
        self.user_guide_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        self.user_guide_action.triggered.connect(self._show_user_guide)
        self.help_menu.addAction(self.user_guide_action)

        self.check_updates_action = QAction("Check for Updates…", self)
        # QAction.triggered emits a boolean. Do not pass that value to
        # _start_update_check, whose optional argument is a SettingsDialog.
        self.check_updates_action.triggered.connect(
            lambda _checked=False: self._start_update_check()
        )
        self.help_menu.addAction(self.check_updates_action)

        self.help_menu.addSeparator()
        self.about_action = QAction("About Reelabel", self)
        # AboutRole moves this action into Reelabel → About Reelabel on macOS.
        self.about_action.setMenuRole(QAction.MenuRole.AboutRole)
        self.about_action.triggered.connect(self._show_about)
        self.help_menu.addAction(self.about_action)

    def _show_settings(self) -> None:
        """Preview appearance live; Cancel restores the saved theme without writes."""
        dialog = SettingsDialog(self._preferences, self, app_version=__version__)
        dialog.appearance_preview.connect(self.theme_controller.set_appearance)
        self.update_controller.attach_settings(dialog)
        dialog.check_updates_requested.connect(lambda: self._start_update_check(dialog))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self._apply_theme()
            return
        before = self._preferences
        self._preferences = dialog.values()
        save_settings(self._settings_store, self._preferences)
        self._apply_theme()
        scan_changed = (before.media_scope, before.recursive, before.include_extras) != (
            self._preferences.media_scope,
            self._preferences.recursive,
            self._preferences.include_extras,
        )
        if scan_changed:
            self._apply_scan_defaults()
            self.notice.setText("Settings saved — refresh the preview with the new scan defaults.")
        else:
            self.notice.setText("Settings saved locally.")

    def _show_about(self) -> None:
        """Show the application identity and its privacy promise."""

        message = QMessageBox(self)
        message.setWindowTitle("About Reelabel")
        logo = QPixmap(str(project_asset("reelabel-icon.png")))
        if not logo.isNull():
            message.setIconPixmap(
                logo.scaled(
                    72,
                    72,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        message.setText(f"<b>Reelabel {__version__}</b>")
        message.setInformativeText(
            "A safe, privacy-focused desktop app for previewing and renaming local "
            "media files.\n\nLicensed under the MIT License.\n"
            "No analytics, telemetry, or background network access. "
            "GitHub is contacted only when you choose Check for Updates."
        )
        message.setStandardButtons(QMessageBox.StandardButton.Ok)
        message.exec()

    def _show_user_guide(self) -> None:
        """Display a concise guide without opening a website or network link."""

        dialog = QDialog(self)
        dialog.setWindowTitle("Reelabel User Guide")
        dialog.resize(620, 480)
        layout = QVBoxLayout(dialog)
        guide = QLabel(
            "<h2>Safe first use</h2>"
            "<ol>"
            "<li>Choose or drop a copied media folder.</li>"
            "<li>Select the media type and scan options.</li>"
            "<li>Choose <b>Preview Changes</b>; no files change yet.</li>"
            "<li>Double-click a <b>Proposed name</b> to edit it.</li>"
            "<li>Uncheck anything you do not want to rename.</li>"
            "<li>Apply only after every selected row is marked Ready.</li>"
            "</ol>"
            "<p><b>History / Undo</b> can restore successful rename operations "
            "without overwriting files.</p>"
            "<p>If you hide the rename confirmation, restore it in "
            "<b>Settings</b>. Destination checks and rollback always remain active.</p>"
            "<p>Related images and NFO files stay disabled and unchecked by "
            "default.</p>"
            "<p><b>Check for Updates</b> contacts the official GitHub release "
            "only when you choose it. It never downloads or installs an update.</p>"
        )
        guide.setWordWrap(True)
        guide.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(guide, 1)
        close = QPushButton("Close")
        close.setObjectName("primary")
        close.clicked.connect(dialog.accept)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(close)
        layout.addLayout(buttons)
        dialog.exec()

    def _start_update_check(self, target: SettingsDialog | None = None) -> None:
        self.update_controller.start(target)

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose a media folder")
        if folder:
            self._set_folder(folder)

    def _set_folder(self, folder: str) -> None:
        self.path_edit.setText(folder)

    def _invalidate_preview(self) -> None:
        """A report authorizes only the exact source/options that produced it."""

        self._source_revision += 1
        self.current_report = None
        self.apply_button.setEnabled(False)
        self.table.setEnabled(False)
        self.edit_button.setEnabled(False)
        self.related_list.clear()
        self.workspace.related_panel.hide()
        self._loading_table = True
        self.table.setRowCount(0)
        self._loading_table = False
        self._refresh_counts()
        self.workspace.summary.setText("Preview needs refreshing")
        self.workspace.show_empty(
            "Ready for a fresh preview",
            "Choose Preview changes to analyze the selected folder and options.",
        )
        self.notice.setText(
            "Folder or options changed — refresh the preview before applying changes."
        )

    def _scan_or_cancel(self) -> None:
        if self._scan_thread is not None and self._scan_thread.isRunning():
            self._scan_thread.requestInterruption()
            self.scan_button.setEnabled(False)
            self.scan_button.setText("Cancelling…")
            self.notice.setText("Stopping the read-only scan…")
            return
        self._start_scan()

    def _start_scan(self) -> None:
        # A finished thread may still have queued result/cleanup signals.
        if self._scan_thread is not None or self.operations.busy:
            return
        folder_text = self.path_edit.text().strip()
        # Path("") represents the current working directory, so the empty
        # value must be rejected before it is converted to a Path.
        if not folder_text:
            QMessageBox.warning(
                self,
                "Choose a folder",
                "Choose a media folder before previewing changes.",
            )
            return
        folder = Path(folder_text).expanduser()
        if not folder.is_dir():
            QMessageBox.warning(
                self,
                "Choose a folder",
                "Select an existing media folder before previewing changes.",
            )
            return
        scope = (
            api.MediaScope.ALL,
            api.MediaScope.MOVIES,
            api.MediaScope.SERIES,
        )[self.media_type.currentIndex()]
        options = api.ScanOptions(
            folder=folder,
            recursive=self.recursive.isChecked(),
            media_type=scope,
            include_extras=self.extras.isChecked(),
            include_sidecars=self.sidecars.isChecked(),
        )

        self.current_report = None
        self._scan_revision = self._source_revision
        self.table.setRowCount(0)
        self.apply_button.setEnabled(False)
        self.scan_button.setText("Cancel scan")
        self.notice.setText("Scanning locally… no files are being changed")
        self.workspace.show_busy(
            "Preparing your preview", "Reading filenames. Your files are unchanged."
        )
        self._set_scan_controls(False)

        task = TaskThread(
            lambda: api.scan(
                options, cancelled=lambda: QThread.currentThread().isInterruptionRequested()
            ),
            self,
        )
        task.finished.connect(self._scan_thread_finished)
        self._scan_thread = task
        task.start()

    @Slot(object)
    def _scan_completed(self, report: api.ScanReport) -> None:
        if self._scan_revision != self._source_revision:
            self.notice.setText(
                "Folder or options changed — refresh the preview to see current results."
            )
            return
        self.current_report = report
        self.table.setEnabled(True)
        self._populate_report(report)
        self.notice.setText("✓ Preview complete — no files have been changed")

    @Slot(str)
    def _scan_failed(self, message: str) -> None:
        self.workspace.show_empty(
            "The scan could not be completed",
            "Check folder access, then try Preview changes again.",
        )
        self.notice.setText("The scan could not be completed")
        QMessageBox.critical(self, "Scan failed", message)

    @Slot()
    def _scan_cancelled(self) -> None:
        self.workspace.show_empty(
            "Scan cancelled", "No files were changed. You can start a new preview."
        )
        self.notice.setText("Scan cancelled — no files were changed")

    @Slot()
    def _scan_thread_finished(self) -> None:
        task = self._scan_thread
        task.wait()
        self._scan_thread = None
        result, error = task.result, task.error
        interrupted = task.isInterruptionRequested()
        task.deleteLater()
        self.scan_button.setEnabled(True)
        self._set_scan_controls(True)
        if self._close_requested:
            QTimer.singleShot(0, self.close)
            return
        if interrupted or isinstance(error, core.ScanCancelled):
            self._scan_cancelled()
        elif error is not None:
            self._scan_failed(str(error))
        elif self._source_revision == self._scan_revision:
            self._scan_completed(result)
        else:
            self.workspace.show_empty(
                "Preview out of date", "Folder or options changed. Run a new preview."
            )
        self.scan_button.setText("Refresh preview" if self.current_report else "Preview changes")

    def _set_scan_controls(self, enabled: bool) -> None:
        for control in (
            self.path_edit,
            self.media_type,
            self.recursive,
            self.extras,
            self.sidecars,
            self.workspace.browse_button,
            self.workspace.history_button,
            self.history_action,
            self.choose_folder_action,
        ):
            control.setEnabled(enabled)
        self.drop_zone.setAcceptDrops(enabled)

    def _populate_report(self, report: api.ScanReport) -> None:
        self._loading_table = True
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(0)
        for rename in report.renames:
            if rename.status == "proposed":
                self._add_row(
                    status="Ready",
                    original=self._relative_name(rename.source, report.options.folder),
                    proposed=rename.destination.name,
                    media_type=(
                        "FOLDER"
                        if rename.kind == "directory"
                        else rename.source.suffix.removeprefix(".").upper()
                    ),
                    selected=True,
                    category="ready",
                    kind="rename",
                    source=rename.source,
                    detail=self._english_reason(rename.reason),
                )
            else:
                self._add_row(
                    status="Review",
                    original=self._relative_name(rename.source, report.options.folder),
                    proposed=rename.destination.name,
                    media_type=(
                        "FOLDER"
                        if rename.kind == "directory"
                        else rename.source.suffix.removeprefix(".").upper()
                    ),
                    selected=False,
                    category="review",
                    kind="conflict",
                    source=rename.source,
                    detail=self._english_reason(rename.detail),
                )
        for path, reason in report.ignored:
            self._add_row(
                status="Ignored",
                original=self._relative_name(path, report.options.folder),
                proposed="—",
                media_type=path.suffix.removeprefix(".").upper(),
                selected=False,
                category="ignored",
                kind="info",
                source=path,
                detail=self._english_reason(reason),
            )
        for path, media_name in report.missing_subtitles:
            self._add_row(
                status="Review",
                original=self._relative_name(path, report.options.folder),
                proposed="External subtitles not found",
                media_type=path.suffix.removeprefix(".").upper(),
                selected=False,
                category="review",
                kind="info",
                source=path,
                detail=f"No external subtitle matched {media_name}. MKV files are exempt.",
            )
        self.related_list.clear()
        for deletion in report.sidecars:
            item = QListWidgetItem(self._relative_name(deletion.path, report.options.folder))
            item.setData(SOURCE_ROLE, str(deletion.path))
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setToolTip(f"Permanent deletion: {deletion.path}")
            self.related_list.addItem(item)
        self.workspace.show_preview()
        self.workspace.related_panel.setVisible(bool(report.sidecars))
        self.table.setEnabled(True)
        self._loading_table = False
        self._apply_current_sort()
        self._refresh_counts()
        self._set_filter(self._active_filter)
        self._revalidate_table()
        self.table.setUpdatesEnabled(True)
        if self.table.rowCount() == 0 and not report.sidecars:
            self.workspace.show_empty(
                "No changes to review",
                "The folder has no matching changes. Try different scan options or another folder.",
            )

    def _relative_name(self, path: Path, root: Path) -> str:
        try:
            return str(path.relative_to(root))
        except ValueError:
            return path.name

    def _english_reason(self, reason: str) -> str:
        """Translate the original engine's known status messages for the UI."""

        return REASON_TRANSLATIONS.get(reason, reason)

    def _add_row(
        self,
        *,
        status: str,
        original: str,
        proposed: str,
        media_type: str,
        selected: bool,
        category: str,
        kind: str,
        source: Path | None,
        detail: str = "",
    ) -> None:
        self.table.add_proposal(
            status=status,
            original=original,
            proposed=proposed,
            media_type=media_type,
            selected=selected,
            category=category,
            kind=kind,
            source=source,
            detail=detail,
        )

    def _load_demo(self) -> None:
        """Populate screenshot-derived examples without scanning or changing files."""

        self._loading_table = True
        if not self.path_edit.text():
            self.path_edit.setText("/Media/Library")
        self.table.setRowCount(0)
        for row in DEMO_ROWS:
            category = row.status.casefold()
            self._add_row(
                status=row.status,
                original=row.original,
                proposed=row.proposed,
                media_type=row.media_type,
                selected=row.selected,
                category=category,
                kind="rename" if row.status == "Ready" else "conflict",
                source=None,
            )
        self._loading_table = False
        self._apply_current_sort()
        self._refresh_counts()
        self._set_filter("all")
        self.workspace.show_preview()
        self.table.setEnabled(True)
        self.notice.setText("Demo preview — fictional names; no files can be changed")
        self.apply_button.setEnabled(False)

    def _show_empty_state(self) -> None:
        self._refresh_filter_labels({"all": 0, "ready": 0, "review": 0, "ignored": 0})
        self.workspace.show_empty()
        self.workspace.summary.setText("No folder selected")

    def _set_filter(self, category: str) -> None:
        """Filtering never changes which source paths the user has checked."""
        self._active_filter = category
        for key, control in self.filter_buttons.items():
            control.setChecked(key == category)
            control.setProperty("active", key == category)
            control.style().unpolish(control)
            control.style().polish(control)
        self.table.filter_rows(category, self.search.text())
        if self.table.isEnabled() and self.table.rowCount():
            self.workspace.show_filtered_preview()
        self._update_selection_summary()

    def _sort_table_by_column(self, column: int) -> None:
        """Sort a preview column, reversing the order on the next click."""

        # Include contains checkboxes rather than names. The other headers
        # contain text that users reasonably expect to sort.
        if column == 0:
            return
        if self._sort_column == column:
            self._sort_order = (
                Qt.SortOrder.DescendingOrder
                if self._sort_order == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            self._sort_column = column
            self._sort_order = Qt.SortOrder.AscendingOrder
        self._apply_current_sort()

    def _apply_current_sort(self) -> None:
        """Apply the selected sort without changing checked or hidden rows."""

        if self._sort_column is None:
            return
        self.table.sortItems(self._sort_column, self._sort_order)
        header = self.table.horizontalHeader()
        header.setSortIndicator(self._sort_column, self._sort_order)
        header.setSortIndicatorShown(True)
        self._set_filter(self._active_filter)

    def _refresh_counts(self) -> None:
        self._refresh_filter_labels(self.table.counts())
        self._update_selection_summary()

    def _refresh_filter_labels(self, counts: dict[str, int]) -> None:
        for key, label in (
            ("all", "All"),
            ("ready", "Ready"),
            ("review", "Review"),
            ("ignored", "Ignored"),
        ):
            self.filter_buttons[key].setText(f"{label} {counts[key]}")

    def _update_selection_summary(self) -> None:
        checked = [
            row
            for row in range(self.table.rowCount())
            if self.table.item(row, 0).checkState() == Qt.CheckState.Checked
        ]
        hidden = sum(self.table.isRowHidden(row) for row in checked)
        review = self.table.counts()["review"]
        parts = [f"{len(checked)} changes selected"]
        if review:
            parts.append(f"{review} need review")
        if hidden:
            parts.append(f"{hidden} selected outside this filter")
        sidecars = len(self._selected_sidecars())
        if sidecars:
            parts.append(f"{sidecars} related files to delete")
        self.workspace.summary.setText(" · ".join(parts))
        self._update_edit_button()

    def _update_edit_button(self) -> None:
        row = self.table.currentRow()
        editable = (
            row >= 0
            and self.table.item(row, 1) is not None
            and self.table.item(row, 1).data(KIND_ROLE) == "rename"
            and not self.table.isRowHidden(row)
            and self.table.isEnabled()
        )
        self.edit_button.setEnabled(editable)
        if row >= 0 and self.table.item(row, 1) is not None:
            status = self.table.item(row, 1)
            reason = status.data(DETAIL_ROLE) or status.toolTip()
            if status.data(CATEGORY_ROLE) != "ready" and reason:
                self.workspace.detail.setText(reason)
                return
        self.workspace.detail.setText(
            "Double-click a proposed name to edit it, or select a row and choose Edit name."
        )
        self.edit_button.setToolTip(
            "Edit this proposed name (F2)."
            if editable
            else "Select an editable proposal in the current preview first."
        )

    def _edit_selected_name(self) -> None:
        if self.edit_button.isEnabled():
            self.table.setCurrentCell(self.table.currentRow(), 3)
            self.table.editItem(self.table.currentItem())

    @Slot(QTableWidgetItem)
    def _table_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading_table or item.column() not in {0, 3}:
            return
        if item.column() == 3:
            previous = item.data(EDIT_BASE_ROLE)
            if isinstance(previous, str) and previous != item.text():
                self._offer_batch_edit(item.row(), previous, item.text())
                with QSignalBlocker(self.table):
                    item.setData(EDIT_BASE_ROLE, item.text())
        self._revalidate_table()

    _batch_episode_name = staticmethod(batch_episode_name)
    _batch_movie_sidecar_name = staticmethod(batch_movie_sidecar_name)

    def _offer_batch_edit(
        self,
        edited_row: int,
        previous_name: str,
        edited_name: str,
    ) -> None:
        """Offer to propagate a title/season correction inside one folder."""

        if self.current_report is None:
            return
        source_value = self.table.item(edited_row, 2).data(SOURCE_ROLE)
        if not source_value:
            return
        source = Path(source_value)
        if not source.is_file():
            return

        episode_changes: list[tuple[int, str]] = []
        movie_changes: list[tuple[int, str]] = []
        for row in range(self.table.rowCount()):
            if row == edited_row:
                continue
            status = self.table.item(row, 1)
            if status.data(KIND_ROLE) != "rename":
                continue
            other_value = self.table.item(row, 2).data(SOURCE_ROLE)
            if not other_value:
                continue
            other_source = Path(other_value)
            if not other_source.is_file() or other_source.parent != source.parent:
                continue
            proposed = self.table.item(row, 3).text()
            updated = self._batch_episode_name(
                previous_name,
                edited_name,
                proposed,
            )
            if updated and updated != proposed:
                episode_changes.append((row, updated))
                continue
            updated = self._batch_movie_sidecar_name(
                previous_name,
                edited_name,
                proposed,
            )
            if updated and updated != proposed:
                movie_changes.append((row, updated))

        changes = episode_changes or movie_changes
        if not changes:
            return

        if episode_changes:
            prompt = f"Apply the same title and season pattern to {len(changes)} other item(s)?"
            details = (
                "Episode numbers and subtitle suffixes will be preserved. "
                "You can still review, edit, or uncheck every result before applying."
            )
        else:
            prompt = f"Apply this movie title to {len(changes)} related subtitle file(s)?"
            details = (
                "Subtitle language markers and file extensions will be preserved. "
                "You can still review, edit, or uncheck every result before applying."
            )
        if not self._confirm_action(
            "Update this folder's proposals?",
            prompt,
            details,
            "Update proposals",
        ):
            return

        self._loading_table = True
        for row, updated in changes:
            proposed_item = self.table.item(row, 3)
            proposed_item.setText(updated)
            proposed_item.setData(EDIT_BASE_ROLE, updated)
        self._loading_table = False
        self._apply_current_sort()

    def _confirm_action(
        self,
        title: str,
        text: str,
        details: str,
        accept_label: str,
        destructive: bool = False,
    ) -> bool:
        """Show a high-contrast confirmation using the application logo."""

        message, accept = self._confirmation_dialog(
            title,
            text,
            details,
            accept_label,
            accept_is_default=not destructive,
        )
        message.exec()
        return message.clickedButton() is accept

    def _confirmation_dialog(
        self,
        title: str,
        text: str,
        details: str,
        accept_label: str,
        *,
        accept_is_default: bool = True,
    ) -> tuple[QMessageBox, QPushButton]:
        """Build a consistently styled confirmation dialog."""

        message = QMessageBox(self)
        message.setTextFormat(Qt.TextFormat.PlainText)
        message.setWindowTitle(title)
        logo = QPixmap(str(project_asset("reelabel-icon.png")))
        if not logo.isNull():
            message.setIconPixmap(
                logo.scaled(
                    64,
                    64,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        message.setText(text)
        message.setInformativeText(details)
        message.setStandardButtons(QMessageBox.StandardButton.Cancel)
        accept = message.addButton(
            accept_label,
            QMessageBox.ButtonRole.AcceptRole,
        )
        accept.setObjectName("primary")
        cancel = message.button(QMessageBox.StandardButton.Cancel)
        if accept_is_default:
            message.setDefaultButton(accept)
        elif cancel is not None:
            # Pressing Enter must never approve a permanent deletion.
            message.setDefaultButton(cancel)
        return message, accept

    def _confirm_apply_changes(self, text: str, details: str) -> bool:
        """Confirm ordinary renames and optionally remember a user's opt-out."""

        if not self._preferences.show_apply_confirmation:
            return True
        message, accept = self._confirmation_dialog(
            "Apply selected changes?",
            text,
            details,
            "Rename selected items",
        )
        dont_show_again = QCheckBox("Don't show again")
        dont_show_again.setToolTip("You can restore this confirmation in Reelabel Settings.")
        message.setCheckBox(dont_show_again)
        message.exec()
        accepted = message.clickedButton() is accept
        if accepted and dont_show_again.isChecked():
            self._preferences = replace(
                self._preferences,
                show_apply_confirmation=False,
            )
            save_settings(self._settings_store, self._preferences)
        return accepted

    def _selected_edits(self) -> dict[Path, str]:
        edits: dict[Path, str] = {}
        for row in range(self.table.rowCount()):
            status = self.table.item(row, 1)
            if status.data(KIND_ROLE) != "rename":
                continue
            if self.table.item(row, 0).checkState() != Qt.CheckState.Checked:
                continue
            source_value = self.table.item(row, 2).data(SOURCE_ROLE)
            if source_value:
                edits[Path(source_value)] = self.table.item(row, 3).text()
        return edits

    def _selected_sidecars(self) -> set[Path]:
        return {
            Path(self.related_list.item(i).data(SOURCE_ROLE))
            for i in range(self.related_list.count())
            if self.related_list.item(i).checkState() == Qt.CheckState.Checked
        }

    def _revalidate_table(self) -> list[api.ValidationIssue]:
        if self.current_report is None:
            self.apply_button.setEnabled(False)
            return []
        edits = self._selected_edits()
        issues = api.validate_edits(self.current_report, edits)
        by_source: dict[Path, list[str]] = {}
        for issue in issues:
            by_source.setdefault(issue.source.resolve(), []).append(issue.message)

        self._loading_table = True
        for row in range(self.table.rowCount()):
            status = self.table.item(row, 1)
            if status.data(KIND_ROLE) != "rename":
                continue
            source = Path(self.table.item(row, 2).data(SOURCE_ROLE)).resolve()
            messages = by_source.get(source, [])
            status.setText("Review" if messages else "Ready")
            status.setData(CATEGORY_ROLE, "review" if messages else "ready")
            status.setToolTip("\n".join(messages))
            status.setData(DETAIL_ROLE, "\n".join(messages))
            self.table.paint_row(row)
        self._loading_table = False
        self._apply_current_sort()
        self._refresh_counts()
        self._set_filter(self._active_filter)
        self.apply_button.setEnabled(bool(edits) and not issues)
        self.apply_button.setToolTip(
            "\n".join(issue.message for issue in issues[:3])
            if issues
            else "Apply only the checked and validated rename proposals."
        )
        return issues

    def _history_dir(self) -> Path:
        location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        return Path(location) / "history"

    def _apply_selected(self) -> None:
        if self.current_report is None or self._scan_thread is not None or self.operations.busy:
            return
        report = self.current_report
        revision = self._source_revision
        edits = self._selected_edits()
        issues = self._revalidate_table()
        if not edits or issues:
            QMessageBox.warning(
                self,
                "Review the selection",
                "Select at least one valid Ready item before applying changes.",
            )
            return
        sidecars = self._selected_sidecars()
        folder_count = sum(source.is_dir() for source in edits)
        file_count = len(edits) - folder_count
        parts = []
        if file_count:
            parts.append(f"{file_count} {'file' if file_count == 1 else 'files'}")
        if folder_count:
            parts.append(f"{folder_count} {'folder' if folder_count == 1 else 'folders'}")
        if not self._confirm_apply_changes(
            f"Rename {' and '.join(parts)}?",
            "Reelabel will check every destination again before making changes. "
            "If any rename fails, completed changes are automatically restored. "
            f"A History / Undo entry will be saved.\n\nFolder: {report.options.folder}",
        ):
            return
        if sidecars:
            if not self._confirm_action(
                "Permanently delete related files?",
                f"Delete {len(sidecars)} selected image/NFO file(s)?",
                "This deletion is permanent and cannot be restored from History / Undo. "
                "Cancel now if you want to keep these files.",
                "Delete permanently",
                True,
            ):
                return

        next_scan_folder = report.options.folder
        selected_root_name = edits.get(report.options.folder)
        if selected_root_name:
            next_scan_folder = report.options.folder.with_name(selected_root_name.strip())
        if self.current_report is not report or revision != self._source_revision:
            self.notice.setText("The preview changed. Refresh it before applying changes.")
            return
        history_dir = self._history_dir()
        self._operation_kind = "apply"
        self._operation_context = next_scan_folder
        self._begin_file_operation(
            "Applying selected changes", "Please keep Reelabel open until this finishes."
        )
        self.operations.start(
            lambda: api.apply(
                report,
                edits,
                delete_sidecars=bool(sidecars),
                selected_sidecars=sidecars,
                history_dir=history_dir,
            )
        )

    def _begin_file_operation(self, title: str, hint: str) -> None:
        self._set_scan_controls(False)
        self.scan_button.setEnabled(False)
        self.preview_action.setEnabled(False)
        self.settings_action.setEnabled(False)
        self.workspace.settings_button.setEnabled(False)
        self.apply_button.setEnabled(False)
        self.table.setEnabled(False)
        self.edit_button.setEnabled(False)
        self.workspace.show_busy(title, hint)
        self.notice.setText(hint)

    def _show_history(self) -> None:
        if self._scan_thread is not None or self.operations.busy:
            return
        dialog = HistoryDialog(self._history_dir(), self)
        self._history_dialog = dialog
        dialog.undo_requested.connect(lambda entry: self._undo_entry(entry, dialog))
        dialog.exec()
        self._history_dialog = None

    def _undo_entry(self, entry: HistoryEntry, dialog: HistoryDialog) -> None:
        if self._scan_thread is not None or self.operations.busy:
            return
        if not self._confirm_action(
            "Undo this operation?",
            f"Restore {entry.files} files and {entry.folders} folders?",
            "Nothing will be overwritten. If restoration cannot finish safely, "
            f"Reelabel will attempt to restore the current names.\n\nFolder: {entry.scope}",
            "Restore original names",
        ):
            return
        # Re-read the record after confirmation: it could have disappeared or
        # been changed while the dialog was open. The API still enforces scope.
        try:
            fresh = read_history(entry.path)
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            dialog.status.setText(f"This history entry is unavailable: {exc}")
            dialog.reload()
            return
        if fresh != entry:
            dialog.reload()
            dialog.status.setText(
                "This history entry changed. Select it again and review its details."
            )
            return
        current = (
            Path(self.path_edit.text()).expanduser() if self.path_edit.text().strip() else None
        )
        self._operation_kind = "undo"
        self._operation_context = fresh.restored_folder(current) if current else None
        self._history_dialog = dialog
        dialog.set_busy(True)
        self._begin_file_operation(
            "Restoring original names", "Please keep Reelabel open until this finishes."
        )
        history_dir = self._history_dir()
        self.operations.start(lambda: api.undo(fresh.path, trusted_history_dir=history_dir))

    @Slot(object, object)
    def _operation_completed(self, result, error) -> None:
        kind = self._operation_kind
        destination = self._operation_context
        self._set_scan_controls(True)
        for control in (
            self.scan_button,
            self.preview_action,
            self.settings_action,
            self.workspace.settings_button,
        ):
            control.setEnabled(True)
        dialog = self._history_dialog
        if dialog is not None:
            dialog.set_busy(False)
        self.current_report = None
        self.related_list.clear()
        self.workspace.show_preview()
        self.table.setEnabled(False)
        if self._close_requested:
            if dialog is not None:
                dialog.accept()
            QTimer.singleShot(0, self.close)
            return
        if error is not None or (kind == "undo" and result.errors):
            details = str(error) if error is not None else "\n".join(result.errors)
            if dialog is not None:
                dialog.status.setText(
                    "Restoration could not complete. Review the error before trying again."
                )
            self.notice.setText(
                "The operation did not complete. Review the error, then create a new preview."
            )
            QMessageBox.critical(dialog or self, "Operation could not complete", details)
            return
        count = result.renamed if kind == "apply" else result.restored
        title = "Changes applied" if kind == "apply" else "Undo complete"
        message = (
            f"{count} item(s) renamed successfully. Find their original names in History / Undo."
            if kind == "apply"
            else f"{count} item(s) restored."
        )
        if kind == "apply" and result.deleted_sidecars:
            message += f"\n{result.deleted_sidecars} related file(s) permanently deleted. These cannot be restored."
        QMessageBox.information(dialog or self, title, message)
        if dialog is not None:
            dialog.accept()
        if destination is not None and destination.is_dir():
            self.path_edit.setText(str(destination))
            self._start_scan()
        else:
            self._show_empty_state()
            self.notice.setText(message)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Finish active workers before Qt destroys their owning window."""

        self._close_requested = True
        self.update_controller.closing = True
        if self.operations.busy:
            self.notice.setText("Finishing the file operation before closing…")
            event.ignore()
            return
        if self._scan_thread is not None:
            self._scan_thread.requestInterruption()
            self.notice.setText("Stopping the read-only scan before closing…")
            event.ignore()
            return
        if self.update_controller.thread is not None:
            self.notice.setText("Finishing the update check before closing…")
            event.ignore()
            return
        super().closeEvent(event)
