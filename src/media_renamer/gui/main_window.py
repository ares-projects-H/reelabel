"""Main window for the first Media Renamer interface validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .styles import stylesheet


@dataclass(frozen=True)
class DemoRow:
    """One representative row shown before the engine is connected."""

    status: str
    original: str
    proposed: str
    media_type: str
    selected: bool = True


DEMO_ROWS = (
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
    """Resolve an asset while running from the source checkout."""
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


class MainWindow(QMainWindow):
    """Modern, read-only prototype for validation checkpoint one."""

    def __init__(self, demo: bool = True) -> None:
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
        self._build_ui()
        if demo:
            self._load_demo()

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
        self.scan_button.clicked.connect(self._load_demo)
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
        for index, text in enumerate(("All 42", "Ready 34", "Review 2", "Ignored 6")):
            button = QPushButton(text)
            button.setObjectName("filter")
            button.setProperty("active", index == 0)
            filter_row.addWidget(button)
        filter_row.addStretch()
        self.sidecars = QCheckBox("Include related images / NFO")
        self.sidecars.setChecked(False)
        self.sidecars.setToolTip("Off by default. A second confirmation is always required.")
        filter_row.addWidget(self.sidecars)
        page.addLayout(filter_row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ("Include", "Status", "Original name", "Proposed name", "Type")
        )
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        page.addWidget(self.table, 1)

        footer = QHBoxLayout()
        notice = QLabel("✓ Prototype mode — no files can be changed")
        notice.setObjectName("safeNotice")
        footer.addWidget(notice)
        footer.addStretch()
        self.apply_button = QPushButton("Apply selected changes")
        self.apply_button.setObjectName("primary")
        self.apply_button.setEnabled(False)
        self.apply_button.setToolTip("Enabled only after the functional alpha is approved.")
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
        version = QLabel("INTERFACE PREVIEW")
        version.setObjectName("muted")
        header.addWidget(icon_label)
        header.addWidget(brand)
        header.addStretch()
        header.addWidget(version)
        return header

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose a media folder")
        if folder:
            self._set_folder(folder)

    def _set_folder(self, folder: str) -> None:
        self.path_edit.setText(folder)

    def _load_demo(self) -> None:
        """Populate the preview with screenshot-derived, non-destructive examples."""
        if not self.path_edit.text():
            self.path_edit.setText("/Media/Library")
        self._set_summary(
            (("42", "FILES FOUND"), ("34", "READY"), ("2", "REVIEW"), ("6", "IGNORED"))
        )
        self.table.setRowCount(len(DEMO_ROWS))
        for row_index, row in enumerate(DEMO_ROWS):
            include = QTableWidgetItem()
            include.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            include.setCheckState(
                Qt.CheckState.Checked if row.selected else Qt.CheckState.Unchecked
            )
            status = QTableWidgetItem(row.status)
            status.setForeground(
                Qt.GlobalColor.green if row.status == "Ready" else Qt.GlobalColor.yellow
            )
            original = QTableWidgetItem(row.original)
            original.setFlags(original.flags() & ~Qt.ItemFlag.ItemIsEditable)
            proposed = QTableWidgetItem(row.proposed)
            media_type = QTableWidgetItem(row.media_type)
            media_type.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            for column, item in enumerate((include, status, original, proposed, media_type)):
                self.table.setItem(row_index, column, item)
            self.table.setRowHeight(row_index, 42)

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

