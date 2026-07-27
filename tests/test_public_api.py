"""Safety tests for the public API used by both interfaces."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from media_renamer import api, core


def _movie(root: Path, name: str = "Campaign.2007.DVDRip.XviD.AC3.mkv") -> Path:
    path = root / name
    path.touch()
    return path


def test_scan_can_be_cancelled(tmp_path: Path) -> None:
    _movie(tmp_path)
    with pytest.raises(core.ScanCancelled):
        api.scan(api.ScanOptions(tmp_path), cancelled=lambda: True)


def test_windows_reserved_name_is_rejected_on_every_platform(tmp_path: Path) -> None:
    source = _movie(tmp_path)
    report = api.scan(api.ScanOptions(tmp_path))
    issues = api.validate_edits(report, {source: "CON.mkv"})
    assert any("reserved by Windows" in issue.message for issue in issues)


def test_duplicate_destination_is_rejected_case_insensitively(tmp_path: Path) -> None:
    first = _movie(tmp_path, "Campaign.2007.DVDRip.mkv")
    second = _movie(tmp_path, "Another.Movie.2008.DVDRip.mkv")
    report = api.scan(api.ScanOptions(tmp_path))
    issues = api.validate_edits(
        report,
        {first: "Shared.mkv", second: "shared.MKV"},
    )
    assert sum("More than one" in issue.message for issue in issues) == 2


def test_apply_selected_item_and_undo(tmp_path: Path) -> None:
    first = _movie(tmp_path)
    second = _movie(tmp_path, "Another.Movie.2008.DVDRip.mkv")
    report = api.scan(api.ScanOptions(tmp_path))
    target = next(
        rename.destination.name for rename in report.renames if rename.source == first
    )
    history = tmp_path / ".application-history"

    result = api.apply(report, {first: target}, history_dir=history)

    assert result.renamed == 1
    assert (tmp_path / target).exists()
    assert second.exists()
    assert result.history_entry.parent == history
    restored = api.undo(result.history_entry)
    assert restored.restored == 1
    assert not restored.errors
    assert first.exists()
    assert second.exists()


def test_failed_apply_restores_original_source(tmp_path: Path) -> None:
    source = _movie(tmp_path)
    report = api.scan(api.ScanOptions(tmp_path))
    target = next(rename.destination.name for rename in report.renames)
    real_replace = os.replace
    failed_once = False

    def fail_at_destination(current: Path, destination: Path) -> None:
        nonlocal failed_once
        if Path(destination).name == target and not failed_once:
            failed_once = True
            raise OSError("simulated final move failure")
        real_replace(current, destination)

    with (
        patch.object(core.os, "replace", side_effect=fail_at_destination),
        pytest.raises(OSError, match="simulated final move failure"),
    ):
        api.apply(
            report,
            {source: target},
            history_dir=tmp_path / ".application-history",
        )

    assert source.exists()
    assert not (tmp_path / target).exists()


def test_related_file_requires_explicit_selection_and_flag(tmp_path: Path) -> None:
    source = _movie(tmp_path)
    poster = tmp_path / "poster.jpg"
    poster.touch()
    report = api.scan(api.ScanOptions(tmp_path, include_sidecars=True))
    target = next(rename.destination.name for rename in report.renames)

    api.apply(
        report,
        {source: target},
        delete_sidecars=False,
        selected_sidecars={poster},
        history_dir=tmp_path / ".application-history",
    )

    assert poster.exists()
