"""Small native widgets shared by the workspace and dialogs."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


def label(text: str, role: str = "", wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setObjectName(role)
    widget.setWordWrap(wrap)
    return widget


def button(text: str, role: str = "") -> QPushButton:
    widget = QPushButton(text)
    widget.setObjectName(role)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    return widget


def row(*widgets, spacing: int = 12) -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.setSpacing(spacing)
    for widget in widgets:
        if widget is None:
            layout.addStretch()
        else:
            layout.addWidget(widget)
    return layout


def card() -> tuple[QFrame, QVBoxLayout]:
    widget = QFrame()
    widget.setObjectName("card")
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(12)
    return widget, layout


def rule() -> QFrame:
    widget = QFrame()
    widget.setObjectName("rule")
    widget.setFixedHeight(1)
    return widget


def fit_combo(combo: QComboBox) -> None:
    """Keep choices bounded, using the final platform font rather than construction-time metrics."""
    combo.ensurePolished()
    fitter = _ComboFitter(combo)
    combo.installEventFilter(fitter)
    combo._label_fitter = fitter
    fitter.fit()


class _ComboFitter(QObject):
    def __init__(self, combo):
        super().__init__(combo)
        self.combo = combo
        self.fitting = False

    def fit(self):
        if self.fitting or not self.combo.count():
            return
        self.fitting = True
        try:
            combo = self.combo
            widest = max(
                combo.fontMetrics().horizontalAdvance(combo.itemText(i))
                for i in range(combo.count())
            )
            combo.setFixedWidth(max(168, widest + 48, combo.minimumSizeHint().width()))
            combo.view().setMinimumWidth(max(200, widest + 64))
        finally:
            self.fitting = False

    def eventFilter(self, watched, event):  # noqa: N802
        if event.type() in {
            QEvent.Type.Show,
            QEvent.Type.FontChange,
            QEvent.Type.StyleChange,
            QEvent.Type.PolishRequest,
        }:
            self.fit()
        return False


class DropZone(QFrame):
    """A compact source panel that accepts exactly one local directory."""

    folder_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setAccessibleName("Media folder; drop one local folder here")

    def _folder(self, event) -> str | None:
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile():
            folder = urls[0].toLocalFile()
            if Path(folder).is_dir():
                return folder
        return None

    def _highlight(self, active: bool) -> None:
        self.setProperty("dragging", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if self.isEnabled() and self._folder(event):
            self._highlight(True)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self._highlight(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        self._highlight(False)
        folder = self._folder(event)
        # Recheck at drop time, not only during dragEnter: the folder may vanish.
        if self.isEnabled() and folder:
            self.folder_dropped.emit(folder)
            event.acceptProposedAction()


class ElidedLabel(QLabel):
    """Show a compact folder label with its full value available to accessibility."""

    def set_full_text(self, text: str) -> None:
        self._full_text = text
        self.setAccessibleName(text)
        self.setToolTip(text)
        self._update_text()

    def _update_text(self):
        self.setText(
            self.fontMetrics().elidedText(
                getattr(self, "_full_text", ""), Qt.TextElideMode.ElideMiddle, self.width()
            )
        )

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._update_text()
        super().resizeEvent(event)
