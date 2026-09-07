"""Readable local history; only the public undo API can authorize restoration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QDialog, QListWidget, QListWidgetItem, QVBoxLayout

from .components import button, label, row


@dataclass(frozen=True)
class HistoryEntry:
    path: Path
    scope: Path
    created: str
    files: int
    folders: int
    undone: bool
    directory_moves: tuple[tuple[Path, Path], ...]

    @property
    def available(self) -> bool:
        return bool(self.files + self.folders) and not self.undone

    def restored_folder(self, current: Path) -> Path:
        """Follow the folder move after successful Undo, without changing history."""
        for old, new in self.directory_moves:
            if current.is_relative_to(new):
                return old / current.relative_to(new)
        return current


def read_history(path: Path) -> HistoryEntry:
    """Validate display data; malformed or disappearing records stay non-actionable."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("operations"), list):
        raise ValueError("This history entry has an invalid format.")
    scope = data.get("scope")
    if not isinstance(scope, str) or not Path(scope).is_absolute():
        raise ValueError("This history entry has no valid media folder.")
    files, folders, moves = 0, 0, []
    for operation in data["operations"]:
        if not isinstance(operation, dict):
            raise ValueError("This history entry contains an invalid operation.")
        if operation.get("status") != "renamed":
            continue
        for key in ("old_path", "new_path"):
            if not isinstance(operation.get(key), str) or not Path(operation[key]).is_absolute():
                raise ValueError("This history entry contains an invalid path.")
        kind = operation.get("kind", "file")
        if kind == "directory":
            folders += 1
            moves.append((Path(operation["old_path"]), Path(operation["new_path"])))
        elif kind == "file":
            files += 1
        else:
            raise ValueError("This history entry contains an unknown item type.")
    created = data.get("created_at", path.stem)
    if not isinstance(created, str):
        created = path.stem
    try:
        created = (
            datetime.fromisoformat(created.replace("Z", "+00:00"))
            .astimezone()
            .strftime("%b %d, %Y at %H:%M")
        )
    except ValueError:
        pass
    return HistoryEntry(
        path, Path(scope), created, files, folders, bool(data.get("undone_at")), tuple(moves)
    )


class HistoryDialog(QDialog):
    """History selection stays separate from serialized filesystem operations."""

    undo_requested = Signal(object)

    def __init__(self, directory: Path, parent=None):
        super().__init__(parent)
        self.directory = directory
        self.busy = False
        self.setWindowTitle("History / Undo")
        self.resize(720, 480)
        self.setMinimumSize(540, 340)
        page = QVBoxLayout(self)
        page.setContentsMargins(24, 24, 24, 20)
        page.setSpacing(16)
        page.addWidget(label("History / Undo", "heading"))
        page.addWidget(
            label(
                "Restore original file and folder names. Existing files will never be overwritten.",
                "muted",
                True,
            )
        )
        self.entries = QListWidget()
        self.entries.setAccessibleName("Rename history entries")
        page.addWidget(self.entries, 1)
        self.status = label(
            "Select a completed operation to restore its original names.", "muted", True
        )
        page.addWidget(self.status)
        self.close_button = button("Close")
        self.undo_button = button("Restore original names", "primary")
        self.undo_button.setEnabled(False)
        self.close_button.clicked.connect(self.reject)
        self.undo_button.clicked.connect(self._request_undo)
        self.entries.currentItemChanged.connect(self._selection_changed)
        page.addLayout(row(None, self.close_button, self.undo_button))
        self.reload()

    def reload(self) -> None:
        self.entries.clear()
        try:
            paths = sorted(self.directory.glob("rename_undo_*.json"), reverse=True)
        except OSError as exc:
            paths = []
            self.status.setText(f"History is unavailable: {exc}")
        for path in paths:
            try:
                entry = read_history(path)
            except (OSError, UnicodeError, ValueError, TypeError) as exc:
                item = QListWidgetItem(f"Unavailable history entry\n{path.name}")
                item.setToolTip(str(exc))
                item.setFlags(Qt.ItemFlag.NoItemFlags)
            else:
                state = (
                    "Undone"
                    if entry.undone
                    else "Available to undo"
                    if entry.available
                    else "No completed renames"
                )
                item = QListWidgetItem(
                    f"{entry.scope.name}\n{entry.created} · {entry.files} files and {entry.folders} folders · {state}"
                )
                item.setToolTip(str(entry.scope))
                item.setData(Qt.ItemDataRole.UserRole, entry)
                if not entry.available:
                    item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.entries.addItem(item)
            # Reserve both lines even when the platform paints a focused item.
            item.setSizeHint(QSize(0, self.entries.fontMetrics().lineSpacing() * 2 + 24))
        if not paths:
            item = QListWidgetItem(
                "No rename history yet.\nYour completed renames will appear here."
            )
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.entries.addItem(item)
        self._selection_changed()

    def _selection_changed(self, *args) -> None:
        item = self.entries.currentItem()
        entry = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.undo_button.setEnabled(
            not self.busy and isinstance(entry, HistoryEntry) and entry.available
        )

    def _request_undo(self) -> None:
        if self.undo_button.isEnabled():
            self.undo_requested.emit(self.entries.currentItem().data(Qt.ItemDataRole.UserRole))

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.entries.setEnabled(not busy)
        self.close_button.setEnabled(not busy)
        self._selection_changed()
        if busy:
            self.status.setText("Restoring names… Please keep Reelabel open until this finishes.")

    def reject(self) -> None:
        if not self.busy:
            super().reject()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.busy:
            event.ignore()
        else:
            super().closeEvent(event)
