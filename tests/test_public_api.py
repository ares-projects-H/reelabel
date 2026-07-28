"""Safety tests for the public API used by both interfaces."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from reelabel import api, core


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
    restored = api.undo(
        result.history_entry,
        trusted_history_dir=history,
    )
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


def test_scan_proposes_clean_leaf_folder_name(tmp_path: Path) -> None:
    release = tmp_path / "Gotham.S04.1080p.x265-ZMNT"
    release.mkdir()
    (release / "Gotham.S04E01.1080p.x265-ZMNT.mkv").touch()

    report = api.scan(api.ScanOptions(tmp_path))

    folder = next(
        rename
        for rename in report.renames
        if rename.kind == "directory"
    )
    assert folder.source == release
    assert folder.destination.name == "Gotham S04"


def test_file_and_containing_folder_apply_and_undo_together(
    tmp_path: Path,
) -> None:
    release = tmp_path / "Gotham.S04.1080p.x265-ZMNT"
    release.mkdir()
    original_file = release / "Gotham.S04E01.1080p.x265-ZMNT.mkv"
    original_file.touch()
    report = api.scan(api.ScanOptions(tmp_path))
    selected = {
        rename.source: rename.destination.name
        for rename in report.renames
        if rename.status == "proposed"
    }

    result = api.apply(
        report,
        selected,
        history_dir=tmp_path / ".application-history",
    )

    clean_folder = tmp_path / "Gotham S04"
    assert clean_folder.is_dir()
    assert (clean_folder / "Gotham S04 E01.mkv").exists()
    restored = api.undo(
        result.history_entry,
        trusted_history_dir=result.history_entry.parent,
    )
    assert not restored.errors
    assert restored.restored == 2
    assert release.is_dir()
    assert original_file.exists()


def test_folder_move_failure_restores_file_and_folder_names(
    tmp_path: Path,
) -> None:
    release = tmp_path / "Gotham.S04.1080p.x265-ZMNT"
    release.mkdir()
    original_file = release / "Gotham.S04E01.1080p.x265-ZMNT.mkv"
    original_file.touch()
    report = api.scan(api.ScanOptions(tmp_path))
    selected = {
        rename.source: rename.destination.name
        for rename in report.renames
        if rename.status == "proposed"
    }
    clean_folder = tmp_path / "Gotham S04"
    real_replace = os.replace
    failed_once = False

    def fail_folder_destination(current: Path, destination: Path) -> None:
        nonlocal failed_once
        if Path(destination) == clean_folder and not failed_once:
            failed_once = True
            raise OSError("simulated folder move failure")
        real_replace(current, destination)

    with (
        patch.object(core.os, "replace", side_effect=fail_folder_destination),
        pytest.raises(OSError, match="simulated folder move failure"),
    ):
        api.apply(
            report,
            selected,
            history_dir=tmp_path / ".application-history",
        )

    assert release.is_dir()
    assert original_file.exists()
    assert not clean_folder.exists()


def test_manual_folder_name_does_not_require_original_suffix(
    tmp_path: Path,
) -> None:
    release = tmp_path / "Gotham.S04.1080p.x265-ZMNT"
    release.mkdir()
    (release / "Gotham.S04E01.1080p.x265-ZMNT.mkv").touch()
    report = api.scan(api.ScanOptions(tmp_path))
    folder = next(
        rename for rename in report.renames if rename.kind == "directory"
    )

    issues = api.validate_edits(report, {folder.source: "Gotham Season 4"})

    assert not issues


def test_selected_release_folder_can_rename_with_local_cli_history(
    tmp_path: Path,
) -> None:
    release = tmp_path / "Gotham.S04.1080p.x265-ZMNT"
    release.mkdir()
    original_file = release / "Gotham.S04E01.1080p.x265-ZMNT.mkv"
    original_file.touch()
    report = api.scan(api.ScanOptions(release))
    selected = {
        rename.source: rename.destination.name
        for rename in report.renames
        if rename.status == "proposed"
    }

    result = api.apply(report, selected)

    clean_folder = tmp_path / "Gotham S04"
    assert clean_folder.is_dir()
    assert result.history_entry.parent == clean_folder
    restored = api.undo(
        result.history_entry,
        expected_scope=release,
    )
    assert not restored.errors
    assert release.is_dir()
    assert original_file.exists()
    assert (release / result.history_entry.name).exists()


def test_explicit_sidecar_deletion_follows_renamed_folder(
    tmp_path: Path,
) -> None:
    release = tmp_path / "Gotham.S04.1080p.x265-ZMNT"
    release.mkdir()
    (release / "Gotham.S04E01.1080p.x265-ZMNT.mkv").touch()
    poster = release / "poster.jpg"
    poster.touch()
    report = api.scan(
        api.ScanOptions(tmp_path, include_sidecars=True)
    )
    selected = {
        rename.source: rename.destination.name
        for rename in report.renames
        if rename.status == "proposed"
    }

    result = api.apply(
        report,
        selected,
        delete_sidecars=True,
        selected_sidecars={poster},
        history_dir=tmp_path / ".application-history",
    )

    clean_folder = tmp_path / "Gotham S04"
    assert clean_folder.is_dir()
    assert not (clean_folder / "poster.jpg").exists()
    restored = api.undo(
        result.history_entry,
        trusted_history_dir=result.history_entry.parent,
    )
    assert not restored.errors
    assert release.is_dir()
    assert not poster.exists()


def test_scan_ignores_media_file_symlink_outside_selected_folder(
    tmp_path: Path,
) -> None:
    selected = tmp_path / "selected"
    outside = tmp_path / "outside"
    selected.mkdir()
    outside.mkdir()
    target = _movie(outside, "External.Movie.2020.1080p.mkv")
    link = selected / target.name
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Symbolic links are not available on this platform.")

    report = api.scan(api.ScanOptions(selected))

    assert not report.renames
    assert target.exists()


def test_apply_rejects_source_replaced_by_external_symlink(
    tmp_path: Path,
) -> None:
    selected = tmp_path / "selected"
    outside = tmp_path / "outside"
    selected.mkdir()
    outside.mkdir()
    source = _movie(selected)
    external = _movie(outside, "External.Movie.2020.1080p.mkv")
    report = api.scan(api.ScanOptions(selected))
    target_name = next(rename.destination.name for rename in report.renames)
    source.unlink()
    try:
        source.symlink_to(external)
    except OSError:
        pytest.skip("Symbolic links are not available on this platform.")

    with pytest.raises(api.InvalidEdits, match="symbolic link"):
        api.apply(
            report,
            {source: target_name},
            history_dir=tmp_path / ".application-history",
        )

    assert external.exists()


def test_undo_requires_trusted_history_or_explicit_scope(tmp_path: Path) -> None:
    record = tmp_path / "rename_undo_untrusted.json"
    record.write_text(
        '{"operations": [], "scope": "/"}',
        encoding="utf-8",
    )

    result = api.undo(record)

    assert result.restored == 0
    assert any("trusted history" in error for error in result.errors)


def test_undo_rejects_paths_outside_expected_scope(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    external = outside / "external.mkv"
    external.touch()
    record = tmp_path / "rename_undo_forged.json"
    record.write_text(
        json.dumps(
            {
                "operations": [
                    {
                        "status": "renamed",
                        "kind": "file",
                        "new_path": str(external),
                        "old_path": str(allowed / "captured.mkv"),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = api.undo(record, expected_scope=allowed)

    assert result.restored == 0
    assert any("hors du dossier" in error for error in result.errors)
    assert external.exists()
