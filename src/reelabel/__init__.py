"""Safe, local-only media filename normalization."""

from ._version import __version__
from .api import (
    ApplyResult,
    InvalidEdits,
    MediaScope,
    ScanOptions,
    ScanReport,
    UndoResult,
    ValidationIssue,
    apply,
    scan,
    undo,
    validate_edits,
)

__all__ = [
    "ApplyResult",
    "InvalidEdits",
    "MediaScope",
    "ScanOptions",
    "ScanReport",
    "UndoResult",
    "ValidationIssue",
    "apply",
    "scan",
    "undo",
    "validate_edits",
    "__version__",
]
