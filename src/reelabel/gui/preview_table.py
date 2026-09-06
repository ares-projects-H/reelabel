"""Preview presentation; source identities never depend on row order or filtering."""

from pathlib import Path

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem

from .assets import icon
from .styles import ROW_HEIGHT, colors

SOURCE_ROLE = int(Qt.ItemDataRole.UserRole)
CATEGORY_ROLE = SOURCE_ROLE + 1
KIND_ROLE = SOURCE_ROLE + 2
EDIT_BASE_ROLE = SOURCE_ROLE + 3
DETAIL_ROLE = SOURCE_ROLE + 4


class PreviewTable(QTableWidget):
    """Editable proposals with explicit read-only metadata and theme-aware states."""

    def __init__(self, parent=None):
        super().__init__(0, 5, parent)
        self.dark = True
        self.setHorizontalHeaderLabels(
            ("Include", "Status", "Original name", "Proposed name", "Type")
        )
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.setAccessibleName("Rename preview; double-click Proposed name or use Edit name")
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setMinimumSectionSize(65)
        header.setSectionsClickable(True)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        for column, width in enumerate((72, 116, 370, 370, 82)):
            header.resizeSection(column, width)
        # Keep stable logical columns for source identity, while presenting the
        # two names next to one another and metadata at the right edge.
        header.moveSection(1, 4)
        header.setStretchLastSection(False)
        self._auto_widths = True
        self._adjusting_columns = False
        header.sectionResized.connect(self._column_resized)

    def _column_resized(self, index, old_size, new_size) -> None:
        if not self._adjusting_columns:
            self._auto_widths = False

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if getattr(self, "_auto_widths", False):
            self._adjusting_columns = True
            room = self.viewport().width() - sum(self.columnWidth(i) for i in (0, 1, 4))
            self.setColumnWidth(2, max(260, room // 2))
            self.setColumnWidth(3, max(260, room - room // 2))
            self._adjusting_columns = False

    def add_proposal(
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
        index = self.rowCount()
        self.insertRow(index)
        for column, text in enumerate(("", status, original, proposed, media_type)):
            item = QTableWidgetItem(text)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            if column == 0 and kind in {"rename", "sidecar"}:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked)
            elif column == 1:
                item.setData(CATEGORY_ROLE, category)
                item.setData(KIND_ROLE, kind)
                item.setData(DETAIL_ROLE, detail)
            elif column == 2:
                item.setData(SOURCE_ROLE, str(source) if source else "")
            elif column == 3:
                item.setData(EDIT_BASE_ROLE, proposed)
                if kind == "rename":
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            item.setToolTip("\n".join(part for part in (text, detail) if part))
            self.setItem(index, column, item)
        self.paint_row(index)

    def paint_row(self, row: int) -> None:
        c = colors(self.dark)
        status = self.item(row, 1)
        category = status.data(CATEGORY_ROLE)
        tone = {"ready": "positive", "review": "warning"}.get(category, "muted")
        status.setForeground(QColor(c[tone]))
        status.setIcon(icon("check" if category == "ready" else "info", c[tone]))
        self.item(row, 2).setForeground(QColor(c["muted"]))
        self.item(row, 4).setForeground(QColor(c["muted"]))

    def set_theme(self, dark: bool) -> None:
        self.dark = dark
        with QSignalBlocker(self):
            for row in range(self.rowCount()):
                self.paint_row(row)

    def filter_rows(self, category: str, query: str = "") -> None:
        query = query.casefold().strip()
        for row in range(self.rowCount()):
            status = self.item(row, 1).data(CATEGORY_ROLE)
            text = (self.item(row, 2).text() + " " + self.item(row, 3).text()).casefold()
            self.setRowHidden(row, (category != "all" and status != category) or query not in text)

    def counts(self) -> dict[str, int]:
        counts = {"all": self.rowCount(), "ready": 0, "review": 0, "ignored": 0}
        for row in range(self.rowCount()):
            category = self.item(row, 1).data(CATEGORY_ROLE)
            if category in counts:
                counts[category] += 1
        return counts
