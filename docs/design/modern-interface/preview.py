"""Validation-one native design study. All actions affect fictional in-memory data.

Run with the project's Python environment. No engine, filesystem scan, network,
user preference store, or history store is accessed. --capture renders the study.
This is a disposable prototype, not the implementation of the production UI.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QFontDatabase, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
ROLE = int(Qt.ItemDataRole.UserRole)

PALETTES = {
    "light": dict(
        bg="#F4F6F8",
        surface="#FFFFFF",
        inset="#F8FAFB",
        ink="#182733",
        muted="#536674",
        line="#D8E0E5",
        divider="#9DAEBB",
        accent="#08778B",
        on_accent="#FFFFFF",
        tint="#E7F3F6",
        positive="#18674E",
        warning="#855219",
        hover="#EEF3F6",
        danger="#B33540",
    ),
    "dark": dict(
        bg="#111720",
        surface="#19212C",
        inset="#151D27",
        ink="#EDF3F7",
        muted="#A1B1BF",
        line="#303F4F",
        divider="#617689",
        accent="#65D0E3",
        on_accent="#10232D",
        tint="#223D49",
        positive="#78D5AC",
        warning="#F0C27B",
        hover="#24303E",
        danger="#FF98A1",
    ),
}

PATHS = {
    "folder": '<path d="M3 7h7l2 2h9v11H3z"/><path d="M3 7V4h7l2 3h8v2"/>',
    "edit": '<path d="m5 15 10-10 4 4L9 19H5zM13 7l4 4M4 22h16"/>',
    "history": '<path d="M4 8a9 9 0 1 1-1 7M4 3v5h5M12 7v6l4 2"/>',
    "settings": '<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="9" cy="6" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="8" cy="18" r="2"/>',
    "arrow": '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    "check": '<path d="m5 12 4 4L19 6"/>',
    "shield": '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z"/><path d="m8 12 3 3 5-6"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-11v1"/>',
    "search": '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
    "refresh": '<path d="M20 7a9 9 0 0 0-15-1L3 9m0-6v6h6M4 17a9 9 0 0 0 15 1l2-3m0 6v-6h-6"/>',
}


def icon(name: str, color: str) -> QIcon:
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><g fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{PATHS[name]}</g></svg>'
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    QSvgRenderer(svg.encode()).render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)


def label(text: str, role: str = "", wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    widget.setObjectName(role)
    widget.setWordWrap(wrap)
    return widget


def button(text: str, callback=None, role: str = "") -> QPushButton:
    widget = QPushButton(text)
    widget.setObjectName(role)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if callback:
        widget.clicked.connect(callback)
    return widget


def row(*widgets, spacing=12) -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.setSpacing(spacing)
    for widget in widgets:
        if widget is None:
            layout.addStretch()
        else:
            layout.addWidget(widget)
    return layout


def rule() -> QFrame:
    widget = QFrame()
    widget.setObjectName("rule")
    widget.setFixedHeight(1)
    return widget


def card() -> tuple[QFrame, QVBoxLayout]:
    widget = QFrame()
    widget.setObjectName("card")
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(12)
    return widget, layout


def demo_rows() -> list[tuple[str, str, str, str]]:
    rows = [("Velora.Observatory.S01.1080p.x265-DEMO", "Velora Observatory S01", "Folder", "Ready")]
    for ep in range(1, 5):
        for suffix, kind in (("mkv", "Video"), ("en.srt", "Subtitle")):
            rows.append(
                (
                    f"Velora.Observatory.S01E{ep:02}.1080p-DEMO.{suffix}",
                    f"Velora Observatory S01 E{ep:02}.{suffix}",
                    kind,
                    "Ready",
                )
            )
    rows += [
        ("The.Copper.Comet.2025.1080p-DEMO.mkv", "The Copper Comet (2025).mkv", "Video", "Ready"),
        (
            "The.Copper.Comet.2025.1080p-DEMO.en.srt",
            "The Copper Comet (2025).en.srt",
            "Subtitle",
            "Ready",
        ),
        (
            "Velora.Observatory.S01E05.extra-copy.mkv",
            "Velora Observatory S01 E05.mkv",
            "Video",
            "Review",
        ),
        ("Velora.Observatory.trailer.mp4", "Excluded by your scan options", "Extra", "Ignored"),
    ]
    return rows


class DesignPreview(QMainWindow):
    """Interactive, explicitly simulated design without production side effects."""

    def __init__(self, theme="dark"):
        super().__init__()
        self.theme = theme
        self.show_confirmation = True
        self.busy = False
        self.preview_valid = True
        self.active_filter = "All"
        self.open_dialogs = []
        self.setWindowTitle("Reelabel — Design preview · fictional data")
        self.setWindowIcon(QIcon(str(PROJECT / "assets/reelabel-icon.png")))
        self.resize(1240, 820)
        self.setMinimumSize(900, 600)
        self.make_ui()
        self.set_theme(theme)
        self.load_demo()

    def resizeEvent(self, event):
        # Preserve useful table space on small displays; no action is removed.
        if hasattr(self, "review_heading"):
            self.review_heading.setVisible(self.height() >= 720)
        super().resizeEvent(event)

    def make_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        page = QVBoxLayout(root)
        page.setContentsMargins(24, 16, 24, 16)
        page.setSpacing(16)

        brand_icon = QLabel()
        brand_icon.setPixmap(
            QPixmap(str(PROJECT / "assets/reelabel-icon.png")).scaled(
                36,
                36,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.history_button = button("History / Undo", self.show_history, "quiet")
        self.settings_button = button("Settings", self.show_settings, "quiet")
        page.addLayout(
            row(
                brand_icon,
                label("Reelabel", "brand"),
                label("DESIGN PREVIEW", "tag"),
                None,
                self.history_button,
                self.settings_button,
            )
        )
        page.addWidget(rule())

        source, source_layout = card()
        source_top = QHBoxLayout()
        self.folder_icon = QLabel()
        self.folder_icon.setFixedSize(36, 36)
        source_top.addWidget(self.folder_icon)
        folder_text = QVBoxLayout()
        folder_text.setSpacing(3)
        self.folder_title = label("Demo library", "strong")
        self.folder_path = label("Fictional films, episodes and subtitles", "muted")
        folder_text.addWidget(self.folder_title)
        folder_text.addWidget(self.folder_path)
        source_top.addLayout(folder_text, 1)
        self.change_button = button("Change folder", self.show_empty)
        self.preview_button = button("Preview changes", self.simulate_scan)
        source_top.addWidget(self.change_button)
        source_top.addWidget(self.preview_button)
        source_layout.addLayout(source_top)
        self.media = QComboBox()
        self.media.addItems(["All media", "Movies only", "Series only"])
        self.media.setFixedWidth(168)
        self.media.setAccessibleName("Media type")
        self.recursive = QCheckBox("Include subfolders")
        self.recursive.setChecked(True)
        self.options_button = button("More options", self.toggle_options, "quiet")
        source_layout.addLayout(
            row(label("Media type", "muted"), self.media, self.recursive, None, self.options_button)
        )
        self.extra_panel = QWidget()
        extra_layout = QVBoxLayout(self.extra_panel)
        extra_layout.setContentsMargins(0, 4, 0, 0)
        self.extras = QCheckBox("Include extras, trailers and bonus files")
        self.sidecars = QCheckBox("Find related images and NFO files")
        extra_layout.addLayout(row(self.extras, self.sidecars, None))
        extra_layout.addWidget(
            label(
                "Related files will be listed separately, unchecked. Deletion always needs its own confirmation.",
                "muted",
                True,
            )
        )
        self.extra_panel.hide()
        source_layout.addWidget(self.extra_panel)
        page.addWidget(source)
        for control in (self.recursive, self.extras, self.sidecars):
            control.toggled.connect(self.mark_outdated)
        self.media.currentIndexChanged.connect(self.mark_outdated)

        self.review_heading = QWidget()
        heading = QVBoxLayout(self.review_heading)
        heading.setContentsMargins(0, 0, 0, 0)
        heading.setSpacing(5)
        heading.addWidget(label("Review your changes", "heading"))
        heading.addWidget(
            label("Compare names below. Nothing changes until you apply your selection.", "muted")
        )
        page.addWidget(self.review_heading)

        tools = QHBoxLayout()
        tools.setSpacing(6)
        self.filter_buttons = {}
        for name in ("All", "Ready", "Review", "Ignored"):
            b = button(name, lambda checked=False, f=name: self.filter_rows(f), "filter")
            b.setCheckable(True)
            tools.addWidget(b)
            self.filter_buttons[name] = b
        tools.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Find a filename…")
        self.search.setAccessibleName("Find a filename in this preview")
        self.search.setFixedWidth(210)
        self.search.textChanged.connect(lambda: self.filter_rows(self.active_filter))
        tools.addWidget(self.search)
        self.edit_button = button("Edit name", self.edit_selected)
        self.edit_button.setEnabled(False)
        tools.addWidget(self.edit_button)
        self.review_toolbar = QWidget()
        tools.setContentsMargins(0, 0, 0, 0)
        self.review_toolbar.setLayout(tools)
        page.addWidget(self.review_toolbar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("previewStack")
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Include", "Original name", "Proposed name", "Type", "Status"]
        )
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setMinimumSectionSize(65)
        self.table.horizontalHeader().setStretchLastSection(True)
        for index, size in enumerate([72, 388, 378, 100, 106]):
            self.table.setColumnWidth(index, size)
        self.table.itemSelectionChanged.connect(self.selection_changed)
        self.table.itemChanged.connect(self.edited)
        self.stack.addWidget(self.table)

        self.empty_page = QWidget()
        empty = QVBoxLayout(self.empty_page)
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.addWidget(
            label("Your next tidy library starts here.", "heading"), 0, Qt.AlignmentFlag.AlignCenter
        )
        empty.addWidget(
            label("Choose or drop a media folder to see proposed names.", "muted"),
            0,
            Qt.AlignmentFlag.AlignCenter,
        )
        empty.addSpacing(12)
        empty.addWidget(
            button("Use the fictional demo folder", self.simulate_scan, "primary"),
            0,
            Qt.AlignmentFlag.AlignCenter,
        )
        empty.addSpacing(8)
        empty.addWidget(
            label("Design preview: no folders are opened or modified.", "muted"),
            0,
            Qt.AlignmentFlag.AlignCenter,
        )
        self.stack.addWidget(self.empty_page)

        self.scan_page = QWidget()
        scan = QVBoxLayout(self.scan_page)
        scan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scan.addWidget(label("Preparing your preview", "heading"), 0, Qt.AlignmentFlag.AlignCenter)
        scan.addWidget(
            label("Reading filenames. Your files are unchanged.", "muted"),
            0,
            Qt.AlignmentFlag.AlignCenter,
        )
        progress = QProgressBar()
        progress.setRange(0, 0)
        progress.setFixedSize(320, 5)
        progress.setTextVisible(False)
        scan.addSpacing(15)
        scan.addWidget(progress, 0, Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.scan_page)
        page.addWidget(self.stack, 1)

        self.detail = label(
            "Double-click a proposed name to edit it, or select a row and choose Edit name.",
            "hint",
            True,
        )
        page.addWidget(self.detail)
        page.addWidget(rule())
        footer = QHBoxLayout()
        footer_text = QVBoxLayout()
        footer_text.setSpacing(4)
        self.summary = label("", "strong")
        self.notice = label("Preview only · Your media contents stay untouched", "muted")
        footer_text.addWidget(self.summary)
        footer_text.addWidget(self.notice)
        footer.addLayout(footer_text, 1)
        self.apply_button = button("Apply selected changes", self.confirm_apply, "primary")
        footer.addWidget(self.apply_button)
        page.addLayout(footer)

        file_menu = self.menuBar().addMenu("File")
        for text, callback in [
            ("Use demo folder", self.simulate_scan),
            ("History / Undo", self.show_history),
            ("Settings…", self.show_settings),
        ]:
            action = QAction(text, self)
            action.triggered.connect(lambda checked=False, call=callback: call())
            file_menu.addAction(action)
        help_menu = self.menuBar().addMenu("Help")
        update = QAction("Check for Updates… (simulated)", self)
        update.triggered.connect(lambda checked=False: self.show_update())
        help_menu.addAction(update)
        about = QAction("About Reelabel", self)
        about.triggered.connect(lambda checked=False: self.show_about())
        help_menu.addAction(about)

    def set_theme(self, name):
        self.theme = name
        c = PALETTES[name]
        QApplication.instance().setStyleSheet(f'''
            QWidget {{ color: {c["ink"]}; font-size: 13px; }}
            QMainWindow, QWidget#root, QDialog {{ background: {c["bg"]}; }}
            QLabel {{ background: transparent; }}
            QLabel#brand {{ font-size: 20px; font-weight: 700; }}
            QLabel#heading {{ font-size: 24px; font-weight: 650; }}
            QLabel#strong {{ font-size: 14px; font-weight: 600; }}
            QLabel#muted, QLabel#hint {{ color: {c["muted"]}; }}
            QLabel#hint {{ padding: 2px 0; }}
            QLabel#tag {{ color: {c["muted"]}; font-size: 10px; padding: 4px 8px; background: {c["hover"]}; border-radius: 5px; }}
            QFrame#card {{ background: {c["surface"]}; border: 1px solid {c["line"]}; border-radius: 12px; }}
            QFrame#rule {{ background: {c["line"]}; border: none; }}
            QPushButton {{ background: {c["surface"]}; border: 1px solid {c["line"]}; border-radius: 7px; padding: 8px 13px; min-height: 18px; font-weight: 550; }}
            QPushButton:hover {{ background: {c["hover"]}; border-color: {c["divider"]}; }}
            QPushButton:pressed {{ background: {c["tint"]}; }}
            QPushButton:focus {{ border: 2px solid {c["accent"]}; padding: 7px 12px; }}
            QPushButton#primary {{ background: {c["accent"]}; border-color: {c["accent"]}; color: {c["on_accent"]}; font-weight: 650; }}
            QPushButton#primary:hover {{ border-color: {c["ink"]}; }}
            QPushButton:disabled {{ color: {c["muted"]}; background: {c["hover"]}; border-color: {c["line"]}; }}
            QPushButton#primary:disabled {{ color: {c["muted"]}; background: {c["hover"]}; border-color: {c["line"]}; }}
            QPushButton#quiet {{ border-color: transparent; background: transparent; }}
            QPushButton#quiet:hover {{ background: {c["hover"]}; }}
            QPushButton#filter {{ border-color: transparent; background: transparent; color: {c["muted"]}; }}
            QPushButton#filter:checked {{ background: {c["tint"]}; color: {c["ink"]}; border-color: {c["line"]}; }}
            QPushButton#segment:checked {{ background: {c["tint"]}; border-color: {c["accent"]}; }}
            QLineEdit, QComboBox {{ background: {c["surface"]}; border: 1px solid {c["line"]}; border-radius: 7px; padding: 8px 11px; min-height: 18px; selection-background-color: {c["accent"]}; selection-color: {c["on_accent"]}; }}
            QLineEdit:focus, QComboBox:focus {{ border-color: {c["accent"]}; }}
            QComboBox::drop-down {{ width: 26px; border: none; }}
            QComboBox::down-arrow {{ image: url("{(HERE / f"chevron-{name}.svg").as_posix()}"); width: 16px; height: 16px; }}
            QComboBox QAbstractItemView {{ background: {c["surface"]}; color: {c["ink"]}; selection-background-color: {c["tint"]}; selection-color: {c["ink"]}; border: 1px solid {c["divider"]}; padding: 6px; outline: 0; }}
            QComboBox QAbstractItemView::item {{ min-height: 30px; padding: 4px 8px; }}
            QCheckBox {{ spacing: 8px; background: transparent; }}
            QCheckBox:focus {{ outline: 1px solid {c["accent"]}; }}
            QCheckBox::indicator, QAbstractItemView::indicator {{ width: 16px; height: 16px; border: 1px solid {c["divider"]}; border-radius: 3px; background: {c["surface"]}; }}
            QCheckBox::indicator:checked, QAbstractItemView::indicator:checked {{ background: {c["accent"]}; border-color: {c["accent"]}; image: url("{(HERE / f"check-{name}.svg").as_posix()}"); }}
            QCheckBox::indicator:hover {{ border-color: {c["accent"]}; }}
            QTableWidget {{ background: {c["surface"]}; border: 1px solid {c["line"]}; border-radius: 9px; selection-background-color: {c["tint"]}; selection-color: {c["ink"]}; gridline-color: {c["line"]}; }}
            QTableWidget::item {{ border-bottom: 1px solid {c["line"]}; padding: 7px 10px; }}
            QTableWidget::item:selected {{ background: {c["tint"]}; }}
            QHeaderView::section {{ background: {c["inset"]}; color: {c["muted"]}; border: none; border-right: 1px solid {c["divider"]}; border-bottom: 1px solid {c["line"]}; padding: 11px 10px; font-weight: 600; font-size: 12px; text-align: left; }}
            QScrollBar:vertical {{ background: {c["inset"]}; width: 10px; margin: 0; }}
            QScrollBar:horizontal {{ background: {c["inset"]}; height: 10px; margin: 0; }}
            QScrollBar::handle {{ background: {c["divider"]}; border-radius: 4px; min-height: 24px; min-width: 24px; }}
            QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
            QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
            QScrollArea {{ border: none; background: transparent; }}
            QScrollArea > QWidget > QWidget {{ background: {c["bg"]}; }}
            QProgressBar {{ border: none; background: {c["line"]}; border-radius: 2px; }}
            QProgressBar::chunk {{ background: {c["accent"]}; }}
            QMenuBar, QMenu {{ background: {c["surface"]}; color: {c["ink"]}; }}
            QMenu {{ border: 1px solid {c["line"]}; padding: 5px; }}
            QMenu::item {{ padding: 8px 18px; }}
            QMenu::item:selected {{ background: {c["tint"]}; }}
            QToolTip {{ color: {c["ink"]}; background: {c["surface"]}; border: 1px solid {c["divider"]}; padding: 6px; }}
        ''')
        self.folder_icon.setPixmap(icon("folder", c["accent"]).pixmap(30, 30))
        for widget, name in [
            (self.history_button, "history"),
            (self.settings_button, "settings"),
            (self.edit_button, "edit"),
            (self.preview_button, "refresh"),
        ]:
            widget.setIcon(icon(name, c["ink"]))
            widget.setIconSize(QSize(17, 17))
        self.paint_rows()

    def paint_rows(self):
        c = PALETTES[self.theme]
        self.table.blockSignals(True)
        for i in range(self.table.rowCount()):
            status = self.table.item(i, 4)
            status.setForeground(
                QColor(
                    c[
                        {"Ready": "positive", "Review": "warning", "Ignored": "muted"}[
                            status.data(ROLE)
                        ]
                    ]
                )
            )
            self.table.item(i, 1).setForeground(QColor(c["muted"]))
            self.table.item(i, 3).setForeground(QColor(c["muted"]))
        self.table.blockSignals(False)

    def load_demo(self):
        self.busy = False
        self.preview_valid = True
        self.table.blockSignals(True)
        self.table.setSortingEnabled(False)
        data = demo_rows()
        self.table.setRowCount(len(data))
        for i, (original, proposed, kind, status) in enumerate(data):
            for col, value in enumerate(
                [
                    "",
                    original,
                    proposed,
                    kind,
                    {"Ready": "✓  Ready", "Review": "!  Review", "Ignored": "—  Ignored"}[status],
                ]
            ):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                if col == 0 and status == "Ready":
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(Qt.CheckState.Checked)
                if col == 2 and status == "Ready":
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                if col == 4:
                    item.setData(ROLE, status)
                item.setToolTip(value)
                self.table.setItem(i, col, item)
        self.table.setSortingEnabled(True)
        self.table.sortItems(1, Qt.SortOrder.AscendingOrder)
        self.table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.table.blockSignals(False)
        self.stack.setCurrentWidget(self.table)
        self.review_toolbar.show()
        self.detail.show()
        self.folder_title.setText("Demo library")
        self.preview_button.setText("Refresh preview")
        self.change_button.setEnabled(True)
        self.notice.setText("Design preview · Fictional files only; no changes on disk")
        self.paint_rows()
        self.filter_rows("All")
        self.update_selection()

    def filter_rows(self, category):
        self.active_filter = category
        query = self.search.text().casefold()
        for name, b in self.filter_buttons.items():
            count = sum(
                name == "All" or self.table.item(i, 4).data(ROLE) == name
                for i in range(self.table.rowCount())
            )
            b.setText(f"{name}  {count}")
            b.setChecked(name == category)
        for i in range(self.table.rowCount()):
            matches = category == "All" or self.table.item(i, 4).data(ROLE) == category
            haystack = self.table.item(i, 1).text() + self.table.item(i, 2).text()
            self.table.setRowHidden(i, not matches or query not in haystack.casefold())

    def selection_changed(self):
        i = self.table.currentRow()
        ready = i >= 0 and self.table.item(i, 4).data(ROLE) == "Ready"
        self.edit_button.setEnabled(ready and self.preview_valid and not self.busy)
        if i >= 0 and not ready:
            if self.table.item(i, 4).data(ROLE) == "Review":
                self.detail.setText(
                    "Needs review: the proposed name already exists. This item is excluded. Resolve the conflict and refresh the preview."
                )
            else:
                self.detail.setText(
                    "Ignored: this trailer is excluded because Include extras is off. Change scan options and refresh to include it."
                )
        else:
            self.detail.setText(
                "Double-click a proposed name to edit it, or select a row and choose Edit name."
            )

    def edited(self, item):
        self.update_selection()
        if item.column() == 2:
            self.detail.setText(
                "Demo proposal edited in memory. In the app, related-file changes will be offered for your review."
            )

    def update_selection(self):
        count = sum(
            self.table.item(i, 0).checkState() == Qt.CheckState.Checked
            for i in range(self.table.rowCount())
        )
        self.summary.setText(f"{count} changes selected · 1 item needs review")
        self.apply_button.setEnabled(bool(count) and self.preview_valid and not self.busy)
        self.selection_changed()

    def edit_selected(self):
        i = self.table.currentRow()
        if i >= 0 and self.table.item(i, 4).data(ROLE) == "Ready":
            self.table.setCurrentCell(i, 2)
            self.table.editItem(self.table.item(i, 2))

    def mark_outdated(self):
        self.preview_valid = False
        self.apply_button.setEnabled(False)
        self.edit_button.setEnabled(False)
        self.notice.setText("Options changed — refresh the preview before applying changes.")
        self.preview_button.setText("Refresh preview")

    def toggle_options(self):
        self.extra_panel.setVisible(not self.extra_panel.isVisible())
        self.options_button.setText(
            "Fewer options" if self.extra_panel.isVisible() else "More options"
        )

    def show_empty(self):
        self.preview_valid = False
        self.table.setRowCount(0)
        self.review_toolbar.hide()
        self.detail.hide()
        self.stack.setCurrentWidget(self.empty_page)
        self.folder_title.setText("Choose a media folder")
        self.summary.setText("No folder selected")
        self.notice.setText("Choose a folder to prepare a read-only preview.")
        self.apply_button.setEnabled(False)
        self.edit_button.setEnabled(False)
        self.preview_button.setText("Preview changes")

    def simulate_scan(self):
        if self.busy:
            self.busy = False
            self.show_empty()
            self.notice.setText("Scan cancelled · No files were changed (simulation)")
            self.change_button.setEnabled(True)
            return
        self.busy = True
        self.stack.setCurrentWidget(self.scan_page)
        self.preview_button.setText("Cancel scan")
        self.change_button.setEnabled(False)
        self.apply_button.setEnabled(False)
        self.edit_button.setEnabled(False)
        self.summary.setText("Preparing preview…")
        self.notice.setText("Simulated scan · No folders are being read")
        QTimer.singleShot(1100, lambda: self.load_demo() if self.busy else None)

    def dialog(self, title, subtitle, width=620):
        d = QDialog(self)
        d.setWindowTitle(f"{title} — Design preview")
        d.resize(width, 280)
        layout = QVBoxLayout(d)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)
        layout.addWidget(label(title, "heading"))
        layout.addWidget(label(subtitle, "muted", True))
        self.open_dialogs.append(d)
        return d, layout

    def show_settings(self):
        d, page = self.dialog(
            "Settings", "Make Reelabel feel at home. Preferences stay on this computer.", 680
        )
        d.resize(680, 800)
        d.setMinimumSize(550, 450)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        groups = QVBoxLayout(body)
        groups.setContentsMargins(0, 0, 0, 0)
        groups.setSpacing(14)
        appearance, layout = card()
        layout.addWidget(label("Appearance", "strong"))
        layout.addWidget(label("Choose how Reelabel looks.", "muted"))
        choices = QHBoxLayout()
        choices.setSpacing(8)
        appearance_buttons = []

        def choose(name):
            if name == "System":
                dark = QApplication.instance().styleHints().colorScheme() == Qt.ColorScheme.Dark
                self.set_theme("dark" if dark else "light")
            else:
                self.set_theme(name.lower())
            for b in appearance_buttons:
                b.setChecked(b.text() == name)

        for name in ("System", "Light", "Dark"):
            b = button(name, lambda checked=False, n=name: choose(n), "segment")
            b.setCheckable(True)
            b.setChecked(name.lower() == self.theme)
            choices.addWidget(b, 1)
            appearance_buttons.append(b)
        layout.addLayout(choices)
        groups.addWidget(appearance)
        defaults, layout = card()
        layout.addWidget(label("Scan defaults", "strong"))
        combo = QComboBox()
        combo.setAccessibleName("Default media type")
        combo.addItems(["All media", "Movies only", "Series only"])
        combo.setFixedWidth(182)
        combo.view().setMinimumWidth(210)
        layout.addLayout(row(label("Media type"), None, combo))
        recursive = QCheckBox("Include subfolders")
        recursive.setChecked(True)
        layout.addWidget(recursive)
        layout.addWidget(QCheckBox("Include extras, trailers and bonus files"))
        groups.addWidget(defaults)
        safety, layout = card()
        layout.addWidget(label("Before applying changes", "strong"))
        confirmation = QCheckBox("Show a confirmation before renaming")
        confirmation.setChecked(self.show_confirmation)
        confirmation.toggled.connect(lambda checked: setattr(self, "show_confirmation", checked))
        layout.addWidget(confirmation)
        layout.addWidget(
            label(
                "Destination checks and History / Undo always stay active.\nDeleting images or NFO files always needs a separate confirmation.",
                "muted",
                True,
            )
        )
        groups.addWidget(safety)
        updates_card, layout = card()
        layout.addLayout(
            row(label("Updates", "strong"), None, label("Installed version 0.2.0", "muted"))
        )
        layout.addWidget(
            label(
                "Reelabel connects to GitHub only when you click this button.\nNo automatic downloads or installations.",
                "muted",
                True,
            )
        )
        check = button("Check for updates", lambda: self.show_update(d))
        layout.addLayout(row(check, None))
        groups.addWidget(updates_card)
        groups.addStretch()
        scroll.setWidget(body)
        page.addWidget(scroll, 1)
        page.addLayout(
            row(
                label("Preview settings are temporary.", "muted"),
                None,
                button("Done", d.accept, "primary"),
            )
        )
        d.show()
        return d

    def show_history(self):
        d, page = self.dialog(
            "History / Undo", "Restore original file and folder names from a previous rename.", 720
        )
        d.resize(720, 460)
        entry, layout = card()
        layout.addLayout(
            row(label("Velora Observatory", "strong"), None, label("Available to undo", "muted"))
        )
        layout.addWidget(label("Today at 14:32 · 10 files and 1 folder renamed", "muted"))
        layout.addWidget(label("Demo library / Velora Observatory S01", "muted"))
        layout.addLayout(row(None, button("Restore original names", lambda: self.show_undo(d))))
        page.addWidget(entry)
        page.addWidget(
            label(
                "This is a fictional history entry. Your real history is not accessed.",
                "muted",
                True,
            )
        )
        page.addStretch()
        page.addLayout(row(None, button("Close", d.accept)))
        d.show()
        return d

    def show_undo(self, parent):
        d, page = self.dialog(
            "Restore original names?",
            "Reelabel checks that the original names are available. Nothing will be overwritten.",
        )
        page.addWidget(label("Design preview: this button only closes the example.", "muted", True))
        page.addLayout(
            row(None, button("Cancel", d.reject), button("Restore names", d.accept, "primary"))
        )
        d.show()

    def confirm_apply(self):
        if not self.show_confirmation:
            self.simulate_apply()
            return
        count = sum(
            self.table.item(i, 0).checkState() == Qt.CheckState.Checked
            for i in range(self.table.rowCount())
        )
        d, page = self.dialog(
            f"Apply {count} selected changes?",
            "Reelabel checks every destination before renaming. If a rename fails, completed changes are restored.",
        )
        detail, body = card()
        body.addLayout(
            row(label("Demo library", "strong"), None, label(f"{count} changes", "muted"))
        )
        body.addWidget(label("Original names can be restored in History / Undo.", "muted", True))
        page.addWidget(detail)
        dont_show = QCheckBox("Don't show again")
        page.addWidget(dont_show)
        page.addWidget(label("You can turn this confirmation back on in Settings.", "muted"))

        def accept():
            self.show_confirmation = not dont_show.isChecked()
            d.accept()
            self.simulate_apply()

        page.addLayout(
            row(None, button("Cancel", d.reject), button("Apply changes", accept, "primary"))
        )
        page.addWidget(label("Simulated action — no files will be renamed.", "muted"))
        d.show()
        return d

    def simulate_apply(self):
        self.notice.setText(
            "Demo complete · No files were renamed. History / Undo shows an example."
        )
        self.summary.setText("Your selection is ready")

    def show_update(self, parent=None):
        d, page = self.dialog(
            "Checking for updates…",
            "Simulated check · No connection to GitHub is made in this preview.",
        )
        status = label("Looking for a newer official release…", "strong")
        page.addWidget(status)
        close = button("Close", d.accept)
        page.addLayout(row(None, close))
        QTimer.singleShot(
            900, lambda: status.setText("Reelabel 0.2.0 is up to date. (Example result)")
        )
        d.show()
        return d

    def show_about(self):
        d, page = self.dialog("Reelabel", "A little order for your media library.")
        page.addWidget(label("Version 0.2.0 · MIT License", "strong"))
        page.addWidget(
            label(
                "No telemetry. No background connections.\nCheck for Updates connects to GitHub only when requested.",
                "muted",
                True,
            )
        )
        page.addLayout(row(None, button("Close", d.accept)))
        d.show()
        return d


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", choices=("light", "dark"), default="dark")
    parser.add_argument("--capture", action="store_true")
    args = parser.parse_args()
    app = QApplication([])
    app.setApplicationName("Reelabel Design Preview")
    app.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(str(PROJECT / "assets/reelabel-icon.png")))
    window = DesignPreview(args.theme)
    window.show()
    if args.capture:

        def save(widget, name):
            QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            app.processEvents()
            assert widget.grab().save(str(HERE / f"{name}.png"))

        for theme in ("dark", "light"):
            window.set_theme(theme)
            window.load_demo()
            save(window, f"preview-{theme}")
            settings = window.show_settings()
            save(settings, f"settings-{theme}")
            settings.close()
            confirmation = window.confirm_apply()
            save(confirmation, f"confirmation-{theme}")
            confirmation.close()
            history = window.show_history()
            save(history, f"history-{theme}")
            history.close()
        window.show_empty()
        save(window, "empty-light")
        window.set_theme("dark")
        window.resize(960, 640)
        window.load_demo()
        save(window, "compact-dark")
        print(f"Captures saved in {HERE}")
        window.close()
        return 0
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
