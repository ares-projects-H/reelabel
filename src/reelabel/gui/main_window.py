"""Main window for the Reelabel desktop application."""

from __future__ import annotations

import json
import re
import sys
import weakref
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from PySide6.QtCore import (
    QObject,
    QSettings,
    QStandardPaths,
    Qt,
    QThread,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QDesktopServices,
    QDragEnterEvent,
    QDropEvent,
    QIcon,
    QKeySequence,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from reelabel import __version__, api, core, updates

from .settings import SettingsDialog, load_settings, save_settings
from .styles import stylesheet

SOURCE_ROLE = int(Qt.ItemDataRole.UserRole)
CATEGORY_ROLE = SOURCE_ROLE + 1
KIND_ROLE = SOURCE_ROLE + 2
EDIT_BASE_ROLE = SOURCE_ROLE + 3
EPISODE_EDIT_RE = re.compile(
    r"(?:(?P<season>S\d{1,2})\s+)?(?P<episode>E\d{1,3}(?:[.-]\d+)?)",
    re.I,
)

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
        "Harbor.Lights.S02.1080p.x265-DEMO",
        "Harbor Lights S02",
        "FOLDER",
    ),
    DemoRow(
        "Ready",
        "[SampleGroup] Midnight Library 2022 WEB-DL.mkv",
        "Midnight Library (2022).mkv",
        "MKV",
    ),
    DemoRow(
        "Ready",
        "Paper.Moons.2018.1080p.BluRay.x264.mkv",
        "Paper Moons (2018).mkv",
        "MKV",
    ),
    DemoRow(
        "Ready",
        "Northbound.2020.DVDRip.XviD.AC3-DEMO.avi",
        "Northbound (2020).avi",
        "AVI",
    ),
    DemoRow(
        "Ready",
        "Northbound.2020.DVDRip.XviD.AC3-DEMO.idx",
        "Northbound (2020).idx",
        "IDX",
    ),
    DemoRow(
        "Ready",
        "Northbound.2020.DVDRip.XviD.AC3-DEMO.sub",
        "Northbound (2020).sub",
        "SUB",
    ),
    DemoRow(
        "Ready",
        "Harbor.Lights.EP01.1080p.WEB-DL.DDP2.0.H.264-DEMO.mkv",
        "Harbor Lights S02 E01.mkv",
        "MKV",
    ),
    DemoRow(
        "Ready",
        "Harbor.Lights.EP01.1080p.WEB-DL.DDP2.0.H.264-DEMO.ass",
        "Harbor Lights S02 E01.ass",
        "ASS",
    ),
    DemoRow(
        "Review",
        "Lost Signal - English subtitles [DEMO][1234ABCD].mkv",
        "Lost Signal - English Subtitles.mkv",
        "MKV",
        False,
    ),
)


def project_asset(name: str) -> Path:
    """Resolve an asset from source or a PyInstaller application bundle."""

    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / "assets" / name
    return Path(__file__).resolve().parents[3] / "assets" / name


class DropZone(QFrame):
    """Folder drop target used by the home screen."""

    folder_dropped = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(92)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName("Media folder drop area")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        icon = QLabel("＋")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(42, 42)
        icon.setStyleSheet(
            "font-size: 25px; font-weight: 300; border-radius: 21px;"
            "background: rgba(43, 199, 242, 0.14); color: #2bc7f2;"
        )
        text_box = QVBoxLayout()
        title = QLabel("Drop a media folder here")
        title.setStyleSheet("font-weight: 700; font-size: 14px;")
        hint = QLabel("or use Browse — files are only previewed")
        hint.setObjectName("pathHint")
        text_box.addWidget(title)
        text_box.addWidget(hint)
        layout.addWidget(icon)
        layout.addLayout(text_box)
        layout.addStretch()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile() and Path(urls[0].toLocalFile()).is_dir():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        self.folder_dropped.emit(event.mimeData().urls()[0].toLocalFile())
        event.acceptProposedAction()


class ScanWorker(QObject):
    """Run the read-only filesystem scan away from the interface thread."""

    completed = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, options: api.ScanOptions) -> None:
        super().__init__()
        self.options = options

    @Slot()
    def run(self) -> None:
        try:
            report = api.scan(
                self.options,
                cancelled=lambda: QThread.currentThread().isInterruptionRequested(),
            )
        except core.ScanCancelled:
            self.cancelled.emit()
        except Exception as exc:  # Qt must receive failures on the main thread.
            self.failed.emit(str(exc))
        else:
            self.completed.emit(report)


class UpdateWorker(QObject):
    """Run an explicitly requested GitHub update check away from the UI thread."""

    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, checker: Callable[[], updates.UpdateCheckResult]) -> None:
        super().__init__()
        self.checker = checker

    @Slot()
    def run(self) -> None:
        try:
            result = self.checker()
        except updates.UpdateNetworkError:
            self.failed.emit("network")
        except updates.UpdateVersionError:
            self.failed.emit("version")
        except updates.UpdateResponseError:
            self.failed.emit("response")
        except Exception:  # Keep unexpected implementation details out of the UI.
            self.failed.emit("unexpected")
        else:
            self.completed.emit(result)


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
        self.setMinimumSize(1040, 700)
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
        self._apply_theme()

        self.current_report: api.ScanReport | None = None
        self._scan_thread: QThread | None = None
        self._scan_worker: ScanWorker | None = None
        self._update_thread: QThread | None = None
        self._update_worker: UpdateWorker | None = None
        self._update_target: weakref.ReferenceType[SettingsDialog] | None = None
        self._update_from_settings = False
        self._close_after_update = False
        self._pending_update_result: updates.UpdateCheckResult | None = None
        self._pending_update_failure: str | None = None
        self._loading_table = False
        self._active_filter = "all"
        self._sort_column: int | None = None
        self._sort_order = Qt.SortOrder.AscendingOrder
        self.filter_buttons: dict[str, QPushButton] = {}
        self._build_ui()
        self._build_menus()
        self._apply_scan_defaults()
        if demo:
            self._load_demo()
        else:
            self._show_empty_state()

    def _system_uses_dark_theme(self) -> bool:
        """Return the operating system's current light/dark palette choice."""

        app = QApplication.instance()
        return app is None or app.palette().window().color().lightness() < 145

    def _apply_theme(self) -> None:
        """Apply the selected appearance to every application popup and window."""

        if self._preferences.appearance == "system":
            dark = self._system_uses_dark_theme()
        else:
            dark = self._preferences.appearance == "dark"
        theme = stylesheet(dark=dark)
        application = QApplication.instance()
        if application is not None:
            # Combo-box lists, menus, and tooltips are separate native windows.
            # An application-wide sheet keeps them readable when Reelabel's
            # selected appearance differs from the operating-system theme.
            application.setStyleSheet(theme)
        else:
            self.setStyleSheet(theme)

    def _apply_scan_defaults(self) -> None:
        """Copy saved scan defaults into the main-window controls."""

        scope_index = {"all": 0, "movies": 1, "series": 2}[
            self._preferences.media_scope
        ]
        self.media_type.setCurrentIndex(scope_index)
        self.recursive.setChecked(self._preferences.recursive)
        self.extras.setChecked(self._preferences.include_extras)
        # Related image/NFO discovery is intentionally not configurable as a
        # default. It must remain a deliberate choice in every session.
        self.sidecars.setChecked(False)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        page = QVBoxLayout(root)
        page.setContentsMargins(28, 22, 28, 18)
        page.setSpacing(16)

        page.addLayout(self._header())

        intro = QVBoxLayout()
        eyebrow = QLabel("SAFE · LOCAL · PRIVATE")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("Rename media files with confidence")
        title.setObjectName("title")
        subtitle = QLabel(
            "Preview every change, edit proposed names, and apply only what you approve."
        )
        subtitle.setObjectName("subtitle")
        intro.addWidget(eyebrow)
        intro.addWidget(title)
        intro.addWidget(subtitle)
        page.addLayout(intro)

        selection_card = QFrame()
        selection_card.setObjectName("card")
        selection = QGridLayout(selection_card)
        selection.setContentsMargins(16, 14, 16, 14)
        selection.setHorizontalSpacing(12)
        selection.setVerticalSpacing(10)

        self.drop_zone = DropZone()
        self.drop_zone.folder_dropped.connect(self._set_folder)
        selection.addWidget(self.drop_zone, 0, 0, 1, 5)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Choose a folder containing movies or series")
        self.path_edit.setAccessibleName("Selected media folder")
        browse = QPushButton("Browse")
        browse.clicked.connect(self._browse)
        self.media_type = QComboBox()
        self.media_type.addItems(("All media", "Movies only", "Series only"))
        self.recursive = QCheckBox("Include subfolders")
        self.recursive.setChecked(True)
        self.extras = QCheckBox("Include extras")
        self.scan_button = QPushButton("Preview changes")
        self.scan_button.setObjectName("primary")
        self.scan_button.clicked.connect(self._scan_or_cancel)
        selection.addWidget(self.path_edit, 1, 0, 1, 2)
        selection.addWidget(browse, 1, 2)
        selection.addWidget(self.media_type, 1, 3)
        selection.addWidget(self.scan_button, 1, 4)
        selection.addWidget(self.recursive, 2, 0)
        selection.addWidget(self.extras, 2, 1)
        page.addWidget(selection_card)

        self.summary_layout = QHBoxLayout()
        self.summary_layout.setSpacing(10)
        page.addLayout(self.summary_layout)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        for key, label in (
            ("all", "All"),
            ("ready", "Ready"),
            ("review", "Review"),
            ("ignored", "Ignored"),
        ):
            button = QPushButton(f"{label} 0")
            button.setObjectName("filter")
            button.setProperty("active", key == "all")
            button.clicked.connect(lambda checked=False, selected=key: self._set_filter(selected))
            self.filter_buttons[key] = button
            filter_row.addWidget(button)
        edit_hint = QLabel("Tip: Double-click a Proposed name to edit it.")
        edit_hint.setObjectName("muted")
        filter_row.addSpacing(10)
        filter_row.addWidget(edit_hint)
        filter_row.addStretch()
        self.sidecars = QCheckBox("Show related images / NFO")
        self.sidecars.setChecked(False)
        self.sidecars.setToolTip(
            "Off by default. Selected related files require a second confirmation."
        )
        filter_row.addWidget(self.sidecars)
        page.addLayout(filter_row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ("Include", "Status", "Original name", "Proposed name", "Type")
        )
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setToolTip(
            "Double-click a Proposed name to edit it. Related episode or movie "
            "files can be updated together after you confirm."
        )
        self.table.verticalHeader().setVisible(False)
        self.table.itemChanged.connect(self._table_item_changed)
        header = self.table.horizontalHeader()
        # Interactive mode lets users drag every header divider to make any
        # preview column wider or narrower on every supported desktop.
        for column in range(self.table.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
        header.setMinimumSectionSize(64)
        header.resizeSection(0, 76)
        header.resizeSection(1, 96)
        header.resizeSection(2, 390)
        header.resizeSection(3, 390)
        header.resizeSection(4, 84)
        header.setStretchLastSection(True)
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._sort_table_by_column)
        page.addWidget(self.table, 1)

        footer = QHBoxLayout()
        self.notice = QLabel("✓ Choose a folder to create a read-only preview")
        self.notice.setObjectName("safeNotice")
        footer.addWidget(self.notice)
        footer.addStretch()
        self.apply_button = QPushButton("Apply selected changes")
        self.apply_button.setObjectName("primary")
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self._apply_selected)
        footer.addWidget(self.apply_button)
        page.addLayout(footer)

        self.setCentralWidget(root)

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
        self.quit_action.triggered.connect(QApplication.quit)
        self.file_menu.addAction(self.quit_action)

        self.help_menu = menu_bar.addMenu("&Help")
        self.user_guide_action = QAction("Reelabel User Guide", self)
        self.user_guide_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        self.user_guide_action.triggered.connect(self._show_user_guide)
        self.help_menu.addAction(self.user_guide_action)

        self.check_updates_action = QAction("Check for Updates…", self)
        self.check_updates_action.triggered.connect(self._start_update_check)
        self.help_menu.addAction(self.check_updates_action)

        self.help_menu.addSeparator()
        self.about_action = QAction("About Reelabel", self)
        # AboutRole moves this action into Reelabel → About Reelabel on macOS.
        self.about_action.setMenuRole(QAction.MenuRole.AboutRole)
        self.about_action.triggered.connect(self._show_about)
        self.help_menu.addAction(self.about_action)

    def _show_settings(self) -> None:
        """Open persistent, local-only interface and scan preferences."""

        dialog = SettingsDialog(self._preferences, self, app_version=__version__)
        dialog.check_updates_requested.connect(
            lambda: self._start_update_check(dialog)
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._preferences = dialog.values()
        save_settings(self._settings_store, self._preferences)
        self._apply_theme()
        self._apply_scan_defaults()
        self.notice.setText("✓ Settings saved locally")

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

    def _header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        icon_label = QLabel()
        icon = QPixmap(str(project_asset("reelabel-icon.png")))
        if not icon.isNull():
            icon_label.setPixmap(
                icon.scaled(
                    42,
                    42,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        brand = QLabel("Reelabel")
        brand.setObjectName("brand")
        history = QPushButton("History / Undo")
        history.clicked.connect(self._show_history)
        version = QLabel(f"VERSION {__version__}")
        version.setObjectName("muted")
        header.addWidget(icon_label)
        header.addWidget(brand)
        header.addStretch()
        header.addWidget(history)
        header.addWidget(version)
        return header

    @Slot()
    def _start_update_check(self, target: SettingsDialog | None = None) -> None:
        """Start the only optional network operation offered by Reelabel."""

        if self._update_thread is not None and self._update_thread.isRunning():
            if target is not None:
                target.set_update_status("An update check is already running.")
            return

        self.check_updates_action.setEnabled(False)
        self._update_from_settings = target is not None
        self._update_target = weakref.ref(target) if target is not None else None
        self._pending_update_result = None
        self._pending_update_failure = None
        if target is not None:
            target.set_update_checking(True)

        thread = QThread(self)
        worker = UpdateWorker(self._update_checker)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.completed.connect(self._update_check_completed)
        worker.failed.connect(self._update_check_failed)
        worker.completed.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._update_thread_finished)
        thread.finished.connect(thread.deleteLater)
        self._update_thread = thread
        self._update_worker = worker
        thread.start()

    def _update_target_dialog(self) -> SettingsDialog | None:
        """Return the still-open Settings dialog that started the check."""

        if self._update_target is None:
            return None
        target = self._update_target()
        if target is None:
            return None
        try:
            return target if target.isVisible() else None
        except RuntimeError:  # The underlying Qt dialog has already been deleted.
            return None

    @Slot(object)
    def _update_check_completed(self, result: updates.UpdateCheckResult) -> None:
        target = self._update_target_dialog()
        if result.update_available:
            status = f"Reelabel {result.latest_version} is available."
        elif result.current_is_newer:
            status = (
                f"This Reelabel {result.current_version} build is newer than the latest "
                f"published release ({result.latest_version})."
            )
        else:
            status = f"Reelabel {result.current_version} is up to date."
        if target is not None:
            target.set_update_status(status)
        # Present the modal result only after QThread has fully stopped. This
        # guarantees that the Settings button is restored before a message box
        # opens and avoids platform-specific modal-window ordering problems.
        self._pending_update_result = result

    def _show_update_result(
        self,
        result: updates.UpdateCheckResult,
        parent: QWidget | None = None,
    ) -> None:
        """Present a verified result and open GitHub only after another click."""

        dialog_parent = parent or self
        if result.current_is_newer:
            self._show_update_information(
                dialog_parent,
                "No update available",
                f"This Reelabel {result.current_version} build is newer than the latest "
                f"published release ({result.latest_version}).",
            )
            return
        if not result.update_available:
            self._show_update_information(
                dialog_parent,
                "Reelabel is up to date",
                f"You are using the latest published version ({result.current_version}).",
            )
            return

        message = QMessageBox(dialog_parent)
        message.setIcon(QMessageBox.Icon.Information)
        message.setWindowTitle("Reelabel update available")
        message.setText(f"Reelabel {result.latest_version} is available.")
        message.setInformativeText(
            "Open the official GitHub release page to review and download it? "
            "Reelabel will not download or install anything automatically."
        )
        message.setStandardButtons(QMessageBox.StandardButton.Cancel)
        open_button = message.addButton(
            "Open download page",
            QMessageBox.ButtonRole.AcceptRole,
        )
        message.setDefaultButton(open_button)
        message.setWindowModality(Qt.WindowModality.ApplicationModal)
        message.show()
        message.raise_()
        message.activateWindow()
        message.exec()
        if message.clickedButton() is open_button:
            QDesktopServices.openUrl(QUrl(result.release_url))

    def _show_update_information(
        self,
        parent: QWidget,
        title: str,
        text: str,
    ) -> None:
        """Show an update result in front of Reelabel on every platform."""

        message = QMessageBox(parent)
        message.setIcon(QMessageBox.Icon.Information)
        message.setWindowTitle(title)
        message.setText(text)
        message.setStandardButtons(QMessageBox.StandardButton.Ok)
        message.setDefaultButton(QMessageBox.StandardButton.Ok)
        message.setWindowModality(Qt.WindowModality.ApplicationModal)
        message.show()
        message.raise_()
        message.activateWindow()
        message.exec()

    @Slot(str)
    def _update_check_failed(self, reason: str) -> None:
        descriptions = {
            "network": (
                "Reelabel could not reach GitHub. Check your connection and try again. "
                "Renaming remains fully available offline."
            ),
            "version": "Reelabel could not verify the release version returned by GitHub.",
            "response": "GitHub returned release information that Reelabel could not verify.",
            "unexpected": "The update check could not be completed safely.",
        }
        text = descriptions.get(reason, descriptions["unexpected"])
        target = self._update_target_dialog()
        if target is not None:
            target.set_update_status(text)
        self._pending_update_failure = reason

    def _show_update_failure(self, reason: str, parent: QWidget | None = None) -> None:
        """Explain a failed check after the worker and its progress state end."""

        descriptions = {
            "network": (
                "Reelabel could not reach GitHub. Check your connection and try again. "
                "Renaming remains fully available offline."
            ),
            "version": "Reelabel could not verify the release version returned by GitHub.",
            "response": "GitHub returned release information that Reelabel could not verify.",
            "unexpected": "The update check could not be completed safely.",
        }
        text = descriptions.get(reason, descriptions["unexpected"])
        message = QMessageBox(parent or self)
        message.setIcon(QMessageBox.Icon.Warning)
        message.setWindowTitle("Could not check for updates")
        message.setText(text)
        message.setStandardButtons(QMessageBox.StandardButton.Ok)
        message.setDefaultButton(QMessageBox.StandardButton.Ok)
        message.setWindowModality(Qt.WindowModality.ApplicationModal)
        message.show()
        message.raise_()
        message.activateWindow()
        message.exec()

    @Slot()
    def _update_thread_finished(self) -> None:
        target = self._update_target_dialog()
        result = self._pending_update_result
        failure = self._pending_update_failure
        from_settings = self._update_from_settings
        if target is not None:
            target.set_update_checking(False)
        self._update_thread = None
        self._update_worker = None
        self._update_target = None
        self._update_from_settings = False
        self._pending_update_result = None
        self._pending_update_failure = None
        self.check_updates_action.setEnabled(True)
        if self._close_after_update:
            self._close_after_update = False
            QTimer.singleShot(0, self.close)
            return

        # Defer by one event-loop turn so Qt first repaints the restored button
        # and closes the worker thread cleanly. The result can then never be
        # hidden behind the modal Settings window.
        if result is not None and (not from_settings or target is not None):
            QTimer.singleShot(
                0,
                lambda checked=result, dialog=target: self._show_update_result(
                    checked,
                    dialog,
                ),
            )
        elif failure is not None and (not from_settings or target is not None):
            QTimer.singleShot(
                0,
                lambda reason=failure, dialog=target: self._show_update_failure(
                    reason,
                    dialog,
                ),
            )

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose a media folder")
        if folder:
            self._set_folder(folder)

    def _set_folder(self, folder: str) -> None:
        self.path_edit.setText(folder)

    def _scan_or_cancel(self) -> None:
        if self._scan_thread is not None and self._scan_thread.isRunning():
            self._scan_thread.requestInterruption()
            self.scan_button.setEnabled(False)
            self.scan_button.setText("Cancelling…")
            self.notice.setText("Stopping the read-only scan…")
            return
        self._start_scan()

    def _start_scan(self) -> None:
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
        self.table.setRowCount(0)
        self.apply_button.setEnabled(False)
        self.scan_button.setText("Cancel scan")
        self.notice.setText("Scanning locally… no files are being changed")

        thread = QThread(self)
        worker = ScanWorker(options)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.completed.connect(self._scan_completed)
        worker.failed.connect(self._scan_failed)
        worker.cancelled.connect(self._scan_cancelled)
        worker.completed.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._scan_thread_finished)
        thread.finished.connect(thread.deleteLater)
        self._scan_thread = thread
        self._scan_worker = worker
        thread.start()

    @Slot(object)
    def _scan_completed(self, report: api.ScanReport) -> None:
        self.current_report = report
        self._populate_report(report)
        self.notice.setText("✓ Preview complete — no files have been changed")

    @Slot(str)
    def _scan_failed(self, message: str) -> None:
        self.notice.setText("The scan could not be completed")
        QMessageBox.critical(self, "Scan failed", message)

    @Slot()
    def _scan_cancelled(self) -> None:
        self.notice.setText("Scan cancelled — no files were changed")

    @Slot()
    def _scan_thread_finished(self) -> None:
        self._scan_thread = None
        self._scan_worker = None
        self.scan_button.setEnabled(True)
        self.scan_button.setText("Preview changes")

    def _populate_report(self, report: api.ScanReport) -> None:
        self._loading_table = True
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
        for deletion in report.sidecars:
            self._add_row(
                status="Related",
                original=self._relative_name(deletion.path, report.options.folder),
                proposed="Permanent deletion",
                media_type=deletion.path.suffix.removeprefix(".").upper(),
                selected=False,
                category="review",
                kind="sidecar",
                source=deletion.path,
                detail="Optional related image/NFO. Always unchecked by default.",
            )
        self._loading_table = False
        self._apply_current_sort()
        self._refresh_counts()
        self._set_filter(self._active_filter)
        self._revalidate_table()

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
        row = self.table.rowCount()
        self.table.insertRow(row)
        include = QTableWidgetItem()
        include.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | (
                Qt.ItemFlag.ItemIsUserCheckable
                if kind in {"rename", "sidecar"}
                else Qt.ItemFlag.NoItemFlags
            )
        )
        include.setCheckState(Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked)
        status_item = QTableWidgetItem(status)
        status_item.setData(CATEGORY_ROLE, category)
        status_item.setData(KIND_ROLE, kind)
        status_item.setForeground(
            Qt.GlobalColor.green
            if status == "Ready"
            else Qt.GlobalColor.yellow
            if status in {"Review", "Related"}
            else Qt.GlobalColor.gray
        )
        original_item = QTableWidgetItem(original)
        original_item.setFlags(original_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        original_item.setData(SOURCE_ROLE, str(source) if source else "")
        proposed_item = QTableWidgetItem(proposed)
        proposed_item.setData(EDIT_BASE_ROLE, proposed)
        if kind != "rename":
            proposed_item.setFlags(proposed_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        type_item = QTableWidgetItem(media_type)
        type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        for column, item in enumerate(
            (include, status_item, original_item, proposed_item, type_item)
        ):
            item.setToolTip(detail)
            self.table.setItem(row, column, item)
        self.table.setRowHeight(row, 42)

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
        self.notice.setText("✓ Demo preview — no files can be changed")
        self.apply_button.setEnabled(False)

    def _show_empty_state(self) -> None:
        self._set_summary((("0", "ITEMS FOUND"), ("0", "READY"), ("0", "REVIEW"), ("0", "IGNORED")))
        self._refresh_filter_labels({"all": 0, "ready": 0, "review": 0, "ignored": 0})

    def _set_filter(self, category: str) -> None:
        """Show only rows in the clicked status category."""

        self._active_filter = category
        for key, button in self.filter_buttons.items():
            button.setProperty("active", key == category)
            button.style().unpolish(button)
            button.style().polish(button)
        for row in range(self.table.rowCount()):
            row_category = self.table.item(row, 1).data(CATEGORY_ROLE)
            self.table.setRowHidden(
                row,
                category != "all" and row_category != category,
            )

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
        counts = {"all": self.table.rowCount(), "ready": 0, "review": 0, "ignored": 0}
        for row in range(self.table.rowCount()):
            category = self.table.item(row, 1).data(CATEGORY_ROLE)
            if category in counts:
                counts[category] += 1
        self._refresh_filter_labels(counts)
        self._set_summary(
            (
                (str(counts["all"]), "ITEMS FOUND"),
                (str(counts["ready"]), "READY"),
                (str(counts["review"]), "REVIEW"),
                (str(counts["ignored"]), "IGNORED"),
            )
        )

    def _refresh_filter_labels(self, counts: dict[str, int]) -> None:
        for key, label in (
            ("all", "All"),
            ("ready", "Ready"),
            ("review", "Review"),
            ("ignored", "Ignored"),
        ):
            self.filter_buttons[key].setText(f"{label} {counts[key]}")

    def _set_summary(self, values: tuple[tuple[str, str], ...]) -> None:
        while self.summary_layout.count():
            item = self.summary_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for value, label in values:
            card = QFrame()
            card.setObjectName("summaryCard")
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 10, 14, 10)
            metric = QLabel(value)
            metric.setObjectName("metric")
            metric_label = QLabel(label)
            metric_label.setObjectName("metricLabel")
            card_layout.addWidget(metric)
            card_layout.addWidget(metric_label)
            self.summary_layout.addWidget(card)

    @Slot(QTableWidgetItem)
    def _table_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading_table or item.column() not in {0, 3}:
            return
        if item.column() == 3:
            previous = item.data(EDIT_BASE_ROLE)
            if isinstance(previous, str) and previous != item.text():
                self._offer_batch_edit(item.row(), previous, item.text())
                item.setData(EDIT_BASE_ROLE, item.text())
        self._revalidate_table()

    def _batch_episode_name(
        self,
        original_template: str,
        edited_template: str,
        candidate: str,
    ) -> str | None:
        """Apply a corrected title/season pattern while preserving episode numbers."""

        original_match = EPISODE_EDIT_RE.search(original_template)
        edited_match = EPISODE_EDIT_RE.search(edited_template)
        candidate_match = EPISODE_EDIT_RE.search(candidate)
        if not original_match or not edited_match or not candidate_match:
            return None

        original_prefix = original_template[: original_match.start()]
        edited_prefix = edited_template[: edited_match.start()]
        candidate_prefix = candidate[: candidate_match.start()]
        original_season = original_match.group("season")
        edited_season = edited_match.group("season")
        if (
            original_prefix.casefold() == edited_prefix.casefold()
            and (original_season or "").casefold() == (edited_season or "").casefold()
        ):
            return None
        if candidate_prefix.casefold() != original_prefix.casefold():
            return None

        episode = candidate_match.group("episode").upper()
        token = f"{edited_season.upper()} {episode}" if edited_season else episode
        return edited_prefix + token + candidate[candidate_match.end() :]

    def _batch_movie_sidecar_name(
        self,
        original_movie: str,
        edited_movie: str,
        candidate: str,
    ) -> str | None:
        """Apply a movie title edit to one related subtitle proposal.

        Only an exact proposed movie stem is replaced. Language and forced
        subtitle suffixes such as ``.fr`` or ``.forced`` remain unchanged.
        """

        original_path = Path(original_movie)
        edited_path = Path(edited_movie)
        candidate_path = Path(candidate)
        if original_path.suffix.casefold() not in core.VIDEO_EXTENSIONS:
            return None
        if candidate_path.suffix.casefold() not in core.SUBTITLE_EXTENSIONS:
            return None

        original_stem = original_path.stem
        prefix = f"{original_stem}."
        if not candidate.casefold().startswith(prefix.casefold()):
            return None
        return edited_path.stem + candidate[len(original_stem) :]

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
        dont_show_again.setToolTip(
            "You can restore this confirmation in Reelabel Settings."
        )
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
        selected: set[Path] = set()
        for row in range(self.table.rowCount()):
            if self.table.item(row, 1).data(KIND_ROLE) != "sidecar":
                continue
            if self.table.item(row, 0).checkState() == Qt.CheckState.Checked:
                selected.add(Path(self.table.item(row, 2).data(SOURCE_ROLE)))
        return selected

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
            status.setForeground(Qt.GlobalColor.yellow if messages else Qt.GlobalColor.green)
        self._loading_table = False
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
        if self.current_report is None:
            return
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
            "A History / Undo entry will be saved.",
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

        next_scan_folder = self.current_report.options.folder
        selected_root_name = edits.get(self.current_report.options.folder)
        if selected_root_name:
            next_scan_folder = self.current_report.options.folder.with_name(
                selected_root_name.strip()
            )
        self.apply_button.setEnabled(False)
        self.scan_button.setEnabled(False)
        self.notice.setText("Applying checked changes safely…")
        try:
            result = api.apply(
                self.current_report,
                edits,
                delete_sidecars=bool(sidecars),
                selected_sidecars=sidecars,
                history_dir=self._history_dir(),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Changes were not applied", str(exc))
            self.notice.setText("Apply failed — automatic restoration was attempted")
            self.scan_button.setEnabled(True)
            self._revalidate_table()
            return

        self.notice.setText(f"✓ Renamed {result.renamed} item(s); an Undo entry was saved")
        QMessageBox.information(
            self,
            "Changes applied",
            f"{result.renamed} item(s) renamed successfully.\n"
            f"History entry:\n{result.history_entry}",
        )
        self.path_edit.setText(str(next_scan_folder))
        self.scan_button.setEnabled(True)
        self._start_scan()

    def _show_history(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("History / Undo")
        dialog.resize(720, 420)
        layout = QVBoxLayout(dialog)
        explanation = QLabel(
            "Undo restores renamed files and folders only when doing so cannot "
            "overwrite an existing item."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        entries = QListWidget()
        layout.addWidget(entries, 1)

        for path in sorted(self._history_dir().glob("rename_undo_*.json"), reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            count = sum(item.get("status") == "renamed" for item in payload.get("operations", []))
            state = "Undone" if payload.get("undone_at") else "Available"
            item = QListWidgetItem(
                f"{payload.get('created_at', path.stem)} — {count} rename(s) — {state}"
            )
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            if state == "Undone":
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            entries.addItem(item)

        buttons = QHBoxLayout()
        close = QPushButton("Close")
        undo_button = QPushButton("Undo selected")
        undo_button.setObjectName("primary")
        undo_button.setEnabled(False)
        buttons.addStretch()
        buttons.addWidget(close)
        buttons.addWidget(undo_button)
        layout.addLayout(buttons)
        close.clicked.connect(dialog.reject)

        if entries.count() == 0:
            empty = QListWidgetItem("No rename history is available yet.")
            empty.setFlags(empty.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            entries.addItem(empty)

        def update_undo_button(current: QListWidgetItem | None) -> None:
            undo_button.setEnabled(
                current is not None
                and bool(current.flags() & Qt.ItemFlag.ItemIsEnabled)
                and bool(current.data(Qt.ItemDataRole.UserRole))
            )

        entries.currentItemChanged.connect(
            lambda current, previous: update_undo_button(current)
        )

        def restore_selected() -> None:
            item = entries.currentItem()
            if item is None or not item.flags() & Qt.ItemFlag.ItemIsEnabled:
                return
            if not self._confirm_action(
                "Undo this operation?",
                "Restore the original file and folder names?",
                "Nothing will be overwritten. Undo stops and restores the current "
                "state if any original destination is no longer safe.",
                "Restore original names",
            ):
                return
            history_path = Path(item.data(Qt.ItemDataRole.UserRole))
            try:
                history_payload = json.loads(history_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                history_payload = {}
            result = api.undo(
                history_path,
                trusted_history_dir=self._history_dir(),
            )
            if result.errors:
                QMessageBox.critical(dialog, "Undo could not run", "\n".join(result.errors))
                return
            QMessageBox.information(dialog, "Undo complete", f"{result.restored} item(s) restored.")
            current_folder = Path(self.path_edit.text()).expanduser()
            for operation in history_payload.get("operations", []):
                if operation.get("kind") != "directory":
                    continue
                new_folder = Path(operation["new_path"])
                try:
                    relative = current_folder.relative_to(new_folder)
                except ValueError:
                    continue
                self.path_edit.setText(str(Path(operation["old_path"]) / relative))
                break
            dialog.accept()
            if self.path_edit.text():
                self._start_scan()

        undo_button.clicked.connect(restore_selected)
        dialog.exec()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Finish active workers before Qt destroys their owning window."""

        if self._scan_thread is not None and self._scan_thread.isRunning():
            self._scan_thread.requestInterruption()
            self.notice.setText("Stopping the read-only scan before closing…")
            event.ignore()
            self._scan_thread.finished.connect(self.close)
            return
        if self._update_thread is not None and self._update_thread.isRunning():
            self._close_after_update = True
            self.hide()
            event.ignore()
            return
        super().closeEvent(event)
