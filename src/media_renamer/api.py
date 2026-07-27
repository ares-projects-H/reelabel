"""Stable public API shared by the desktop interface and command-line tools.

The functions in this module deliberately separate read-only planning from
filesystem changes. A scan can be cancelled safely; applying a validated plan
is transactional and therefore intentionally cannot be interrupted halfway.
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from . import core


class MediaScope(str, Enum):
    """Kinds of media included in a scan."""

    ALL = "all"
    MOVIES = "movies"
    SERIES = "series"


@dataclass(frozen=True)
class ScanOptions:
    """Options for a read-only media-folder scan."""

    folder: Path
    recursive: bool = True
    media_type: MediaScope = MediaScope.ALL
    include_extras: bool = False
    include_sidecars: bool = False


@dataclass(frozen=True)
class ScanReport:
    """A scan result plus the exact options that produced it."""

    options: ScanOptions
    engine_report: core.Report

    @property
    def renames(self) -> list[core.Rename]:
        return self.engine_report.renames

    @property
    def conflicts(self) -> list[tuple[Path, str]]:
        return self.engine_report.conflicts

    @property
    def ignored(self) -> list[tuple[Path, str]]:
        return self.engine_report.ignored

    @property
    def missing_subtitles(self) -> list[tuple[Path, str]]:
        return self.engine_report.missing_subtitles

    @property
    def sidecars(self) -> list[core.Deletion]:
        return self.engine_report.deletions


@dataclass(frozen=True)
class ValidationIssue:
    """One unsafe or invalid manual edit."""

    source: Path
    message: str


@dataclass(frozen=True)
class ApplyResult:
    """Audit paths and counts produced by a successful apply operation."""

    log_path: Path
    history_entry: Path
    renamed: int
    deleted_sidecars: int


@dataclass(frozen=True)
class UndoResult:
    """Result of restoring one history entry."""

    restored: int
    errors: tuple[str, ...]


class InvalidEdits(ValueError):
    """Raised when apply receives edits that did not pass validation."""

    def __init__(self, issues: Iterable[ValidationIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__("; ".join(issue.message for issue in self.issues))


WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
WINDOWS_INVALID_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def scan(
    options: ScanOptions,
    cancelled: Callable[[], bool] | None = None,
) -> ScanReport:
    """Analyze a folder without modifying any file."""

    folder = options.folder.expanduser().resolve()
    if not folder.is_dir():
        raise NotADirectoryError(f"Folder does not exist: {folder}")
    normalized = ScanOptions(
        folder=folder,
        recursive=options.recursive,
        media_type=MediaScope(options.media_type),
        include_extras=options.include_extras,
        include_sidecars=options.include_sidecars,
    )
    only = None if normalized.media_type is MediaScope.ALL else normalized.media_type.value
    report = core.build_report(
        folder,
        recursive=normalized.recursive,
        only=only,
        include_extras=normalized.include_extras,
        include_sidecars=normalized.include_sidecars,
        cancelled=cancelled,
    )
    return ScanReport(normalized, report)


def validate_edits(
    report: ScanReport,
    edits: Mapping[Path, str],
) -> list[ValidationIssue]:
    """Validate selected destination filenames without touching the filesystem.

    Each value is a filename, not a path. Keeping edits in the source file's
    directory prevents accidental moves outside the folder selected by the
    user.
    """

    proposed = {
        rename.source.resolve(): rename
        for rename in report.renames
        if rename.status == "proposed"
    }
    selected_sources = {Path(source).resolve() for source in edits}
    issues: list[ValidationIssue] = []
    destinations: dict[str, list[Path]] = defaultdict(list)

    for raw_source, raw_name in edits.items():
        source = Path(raw_source).resolve()
        name = raw_name.strip()
        rename = proposed.get(source)
        if rename is None:
            issues.append(ValidationIssue(source, "This item is not a safe proposed rename."))
            continue
        if not source.exists():
            issues.append(ValidationIssue(source, "The source file disappeared after the scan."))
        if not name or name in {".", ".."}:
            issues.append(ValidationIssue(source, "The proposed filename is empty or invalid."))
            continue
        if Path(name).name != name or WINDOWS_INVALID_RE.search(name):
            issues.append(
                ValidationIssue(source, "The filename contains a path or an unsupported character.")
            )
        if name.endswith((" ", ".")):
            issues.append(
                ValidationIssue(source, "Windows filenames cannot end with a space or period.")
            )
        if len(name) > 255:
            issues.append(ValidationIssue(source, "The filename is longer than 255 characters."))
        if Path(name).suffix.casefold() != source.suffix.casefold():
            issues.append(ValidationIssue(source, "The original file extension must be preserved."))
        if Path(name).stem.rstrip(" .").upper() in WINDOWS_RESERVED:
            issues.append(ValidationIssue(source, "This filename is reserved by Windows."))

        destination = source.with_name(name)
        key = os.path.normcase(str(destination.resolve())).casefold()
        destinations[key].append(source)

        if destination.exists() and destination.resolve() not in selected_sources:
            issues.append(ValidationIssue(source, "A file already exists at the destination."))
        else:
            try:
                sibling_collision = any(
                    sibling.name.casefold() == name.casefold()
                    and sibling.resolve() not in selected_sources
                    for sibling in source.parent.iterdir()
                )
            except OSError as exc:
                issues.append(ValidationIssue(source, f"The folder cannot be checked: {exc}"))
            else:
                if sibling_collision:
                    issues.append(
                        ValidationIssue(source, "Another file differs only by letter case.")
                    )

    for sources in destinations.values():
        if len(sources) > 1:
            for source in sources:
                issues.append(
                    ValidationIssue(source, "More than one selected item has this destination.")
                )
    return issues


def apply(
    report: ScanReport,
    selected_items: Mapping[Path, str],
    delete_sidecars: bool = False,
    selected_sidecars: Iterable[Path] = (),
    history_dir: Path | None = None,
) -> ApplyResult:
    """Apply selected renames transactionally after repeating all safety checks."""

    issues = validate_edits(report, selected_items)
    if issues:
        raise InvalidEdits(issues)
    approved_sidecars = {Path(path).resolve() for path in selected_sidecars}
    available_sidecars = {
        deletion.path.resolve(): deletion for deletion in report.sidecars
    }
    unknown_sidecars = approved_sidecars - set(available_sidecars)
    if unknown_sidecars:
        raise ValueError("A selected related file is not part of this scan.")

    operation = core.Report(
        videos_found=report.engine_report.videos_found,
        subtitles_found=report.engine_report.subtitles_found,
    )
    for source, filename in selected_items.items():
        resolved = Path(source).resolve()
        operation.renames.append(
            core.Rename(
                source=resolved,
                destination=resolved.with_name(filename.strip()),
                reason="user-approved desktop rename",
            )
        )
    if delete_sidecars:
        operation.deletions = [
            core.Deletion(path=available_sidecars[path].path)
            for path in sorted(approved_sidecars)
        ]

    log_path, undo_path = core.execute(
        operation,
        report.options.folder,
        history_dir=history_dir,
    )
    return ApplyResult(
        log_path=log_path,
        history_entry=undo_path,
        renamed=sum(rename.status == "renamed" for rename in operation.renames),
        deleted_sidecars=sum(
            deletion.status == "deleted" for deletion in operation.deletions
        ),
    )


def undo(history_entry: Path) -> UndoResult:
    """Restore a completed history entry without overwriting existing files."""

    history_entry = Path(history_entry)
    data = json.loads(history_entry.read_text(encoding="utf-8"))
    if data.get("undone_at"):
        return UndoResult(0, ("This history entry has already been undone.",))
    restored, errors = core.undo(history_entry)
    if not errors:
        from datetime import datetime, timezone

        data["undone_at"] = datetime.now(timezone.utc).isoformat()
        temporary = history_entry.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, history_entry)
    return UndoResult(restored, tuple(errors))

