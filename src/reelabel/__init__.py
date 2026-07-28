"""Safe, local-only media filename normalization."""

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

__version__ = "0.1.0"

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
]
