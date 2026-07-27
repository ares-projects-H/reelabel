"""Main window for the Media Renamer desktop application."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QStandardPaths, Qt, QThread, Signal, Slot
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QPixmap
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

from media_renamer import api, core

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
        "Gotham.S04.1080p.x265-ZMNT",
        "Gotham S04",
        "FOLDER",
    ),
    DemoRow(
        "Ready",
        "[MagicStar] Jikou Keisatsu 2019 Fukkatsu SP WEB-DL.mkv",
        "Jikou Keisatsu 2019 Fukkatsu SP.mkv",
        "MKV",
    ),
    DemoRow(
        "Ready",
        "Always.Sunset.on.Third.Street.2005.1080p.BluRay.x264.mkv",
        "Always Sunset on Third Street (2005).mkv",
        "MKV",
    ),
    DemoRow(
        "Ready",
        "Campaign.2007.DVDRip.XviD.AC3.Glaeken.CG.avi",
        "Campaign (2007).avi",
        "AVI",
    ),
    DemoRow(
        "Ready",
        "Campaign.2007.DVDRip.XviD.AC3.Glaeken.CG.idx",
        "Campaign (2007).idx",
        "IDX",
    ),
    DemoRow(
        "Ready",
        "Campaign.2007.DVDRip.XviD.AC3.Glaeken.CG.sub",
        "Campaign (2007).sub",
        "SUB",
    ),
    DemoRow(
        "Ready",
        "Toumei.na.Yurikago.EP01.1080p.NF.WEB-DL.DDP2.0.H.264-MagicStar.mkv",
        "Toumei na Yurikago S01 E01.mkv",
        "MKV",
    ),
    DemoRow(
        "Ready",
        "Toumei.na.Yurikago.EP01.1080p.NF.WEB-DL.DDP2.0.H.264-MagicStar.ass",
        "Toumei na Yurikago S01 E01.ass",
        "ASS",
    ),
    DemoRow(
        "Review",
        "Again - English subtitles [ATK][8680D185].mkv",
        "Again - English Subtitles.mkv",
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
        if len(urls) == 1 and urls[0].isLocalFile() and Path(
            urls[0].toLocalFile()
        ).is_dir():
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


class MainWindow(QMainWindow):
    """Modern interface for previewing and safely applying media renames."""

    def __init__(self, demo: bool = False) -> None:
        super().__init__()
        self.setWindowTitle("Media Renamer")
        self.setMinimumSize(1040, 700)
        self.resize(1280, 820)
        icon_path = project_asset("media-renamer-icon.png")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        app = QApplication.instance()
        dark = True
        if app is not None:
            dark = app.palette().window().color().lightness() < 145
        self.setStyleSheet(stylesheet(dark=dark))

        self.current_report: api.ScanReport | None = None
        self._scan_thread: QThread | None = None
        self._scan_worker: ScanWorker | None = None
        self._loading_table = False
        self._active_filter = "all"
        self.filter_buttons: dict[str, QPushButton] = {}
        self._build_ui()
        if demo:
            self._load_demo()
        else:
            self._show_empty_state()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        page = QVBoxLayout(root)
        page.setContentsMargins(28, 22, 28, 18)
        page.setSpacing(16)

        page.addLayout(self._header())

        intro = QVBoxLayout()
        eyebrow = QLabel("SAFE · LOCAL · OFFLINE")
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
            button.clicked.connect(
                lambda checked=False, selected=key: self._set_filter(selected)
            )
            self.filter_buttons[key] = button
            filter_row.addWidget(button)
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
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setToolTip(
            "Edit a proposed episode name to optionally update the same pattern "
            "for other files in its folder."
        )
        self.table.verticalHeader().setVisible(False)
        self.table.itemChanged.connect(self._table_item_changed)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
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

    def _header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        icon_label = QLabel()
        icon = QPixmap(str(project_asset("media-renamer-icon.png")))
        if not icon.isNull():
            icon_label.setPixmap(
                icon.scaled(
                    42,
                    42,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        brand = QLabel("Media Renamer")
        brand.setObjectName("brand")
        history = QPushButton("History / Undo")
        history.clicked.connect(self._show_history)
        version = QLabel("FUNCTIONAL ALPHA")
        version.setObjectName("muted")
        header.addWidget(icon_label)
        header.addWidget(brand)
        header.addStretch()
        header.addWidget(history)
        header.addWidget(version)
        return header

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
        folder = Path(self.path_edit.text().strip()).expanduser()
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
        include.setCheckState(
            Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked
        )
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
        original_item.setFlags(
            original_item.flags() & ~Qt.ItemFlag.ItemIsEditable
        )
        original_item.setData(SOURCE_ROLE, str(source) if source else "")
        proposed_item = QTableWidgetItem(proposed)
        proposed_item.setData(EDIT_BASE_ROLE, proposed)
        if kind != "rename":
            proposed_item.setFlags(
                proposed_item.flags() & ~Qt.ItemFlag.ItemIsEditable
            )
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
        self._refresh_counts()
        self._set_filter("all")
        self.notice.setText("✓ Demo preview — no files can be changed")
        self.apply_button.setEnabled(False)

    def _show_empty_state(self) -> None:
        self._set_summary(
            (("0", "ITEMS FOUND"), ("0", "READY"), ("0", "REVIEW"), ("0", "IGNORED"))
        )
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
            card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
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
            and (original_season or "").casefold()
            == (edited_season or "").casefold()
        ):
            return None
        if candidate_prefix.casefold() != original_prefix.casefold():
            return None

        episode = candidate_match.group("episode").upper()
        token = (
            f"{edited_season.upper()} {episode}"
            if edited_season
            else episode
        )
        return (
            edited_prefix
            + token
            + candidate[candidate_match.end() :]
        )

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

        changes: list[tuple[int, str]] = []
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
                changes.append((row, updated))
        if not changes:
            return

        if not self._confirm_action(
            "Update this folder's proposals?",
            f"Apply the same title and season pattern to {len(changes)} other item(s)?",
            "Episode numbers and subtitle suffixes will be preserved. "
            "You can still review, edit, or uncheck every result before applying.",
            "Update proposals",
        ):
            return

        self._loading_table = True
        for row, updated in changes:
            proposed_item = self.table.item(row, 3)
            proposed_item.setText(updated)
            proposed_item.setData(EDIT_BASE_ROLE, updated)
        self._loading_table = False

    def _confirm_action(
        self,
        title: str,
        text: str,
        details: str,
        accept_label: str,
    ) -> bool:
        """Show a high-contrast confirmation using the application logo."""

        message = QMessageBox(self)
        message.setWindowTitle(title)
        logo = QPixmap(str(project_asset("media-renamer-icon.png")))
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
        message.setDefaultButton(accept)
        message.exec()
        return message.clickedButton() is accept

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
            status.setForeground(
                Qt.GlobalColor.yellow if messages else Qt.GlobalColor.green
            )
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
        location = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
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
            parts.append(
                f"{file_count} {'file' if file_count == 1 else 'files'}"
            )
        if folder_count:
            parts.append(
                f"{folder_count} {'folder' if folder_count == 1 else 'folders'}"
            )
        if not self._confirm_action(
            "Apply selected changes?",
            f"Rename {' and '.join(parts)}?",
            "Media Renamer will check every destination again before making changes. "
            "If any rename fails, completed changes are automatically restored. "
            "A History / Undo entry will be saved.",
            "Rename selected items",
        ):
            return
        if sidecars:
            if not self._confirm_action(
                "Permanently delete related files?",
                f"Delete {len(sidecars)} selected image/NFO file(s)?",
                "This deletion is permanent and cannot be restored from History / Undo. "
                "Cancel now if you want to keep these files.",
                "Delete permanently",
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

        self.notice.setText(
            f"✓ Renamed {result.renamed} item(s); an Undo entry was saved"
        )
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

        for path in sorted(
            self._history_dir().glob("rename_undo_*.json"), reverse=True
        ):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            count = sum(
                item.get("status") == "renamed"
                for item in payload.get("operations", [])
            )
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
        buttons.addStretch()
        buttons.addWidget(close)
        buttons.addWidget(undo_button)
        layout.addLayout(buttons)
        close.clicked.connect(dialog.reject)

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
                history_payload = json.loads(
                    history_path.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                history_payload = {}
            result = api.undo(
                history_path,
                trusted_history_dir=self._history_dir(),
            )
            if result.errors:
                QMessageBox.critical(dialog, "Undo could not run", "\n".join(result.errors))
                return
            QMessageBox.information(
                dialog, "Undo complete", f"{result.restored} item(s) restored."
            )
            current_folder = Path(self.path_edit.text()).expanduser()
            for operation in history_payload.get("operations", []):
                if operation.get("kind") != "directory":
                    continue
                new_folder = Path(operation["new_path"])
                try:
                    relative = current_folder.relative_to(new_folder)
                except ValueError:
                    continue
                self.path_edit.setText(
                    str(Path(operation["old_path"]) / relative)
                )
                break
            dialog.accept()
            if self.path_edit.text():
                self._start_scan()

        undo_button.clicked.connect(restore_selected)
        dialog.exec()

    def closeEvent(self, event) -> None:  # noqa: N802, ANN001
        if self._scan_thread is not None and self._scan_thread.isRunning():
            self._scan_thread.requestInterruption()
            self.notice.setText("Stopping the read-only scan before closing…")
            event.ignore()
            self._scan_thread.finished.connect(self.close)
            return
        super().closeEvent(event)
