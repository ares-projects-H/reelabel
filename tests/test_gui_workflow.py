"""Regression tests for preview ownership and real desktop workflows."""

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from reelabel import api, core
from reelabel.gui.history import HistoryDialog, read_history
from reelabel.gui.main_window import MainWindow
from reelabel.gui.settings import SettingsDialog


@pytest.fixture
def scanned_window(qtbot, tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    (media / "Velora.Observatory.S01E01.1080p-DEMO.mkv").touch()
    store = QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat)
    window = MainWindow(settings_store=store)
    qtbot.addWidget(window)
    window.path_edit.setText(str(media))
    window.scan_button.click()
    qtbot.waitUntil(lambda: window._scan_thread is None and window.current_report is not None)
    return window


@pytest.mark.parametrize("control", ["folder", "drop", "media", "recursive", "extras", "sidecars"])
def test_source_changes_invalidate_existing_preview(scanned_window, tmp_path, control):
    window = scanned_window
    assert window.apply_button.isEnabled()
    if control in {"folder", "drop"}:
        other = tmp_path / "other"
        other.mkdir()
        if control == "folder":
            window.path_edit.setText(str(other))
        else:
            window.drop_zone.folder_dropped.emit(str(other))
    elif control == "media":
        window.media_type.setCurrentIndex(1)
    else:
        widget = getattr(window, control)
        widget.setChecked(not widget.isChecked())
    assert not window.apply_button.isEnabled()
    assert window.current_report is None


def test_only_proposed_names_are_editable(scanned_window):
    for row in range(scanned_window.table.rowCount()):
        for column in (0, 1, 2, 4):
            assert not scanned_window.table.item(row, column).flags() & Qt.ItemFlag.ItemIsEditable


@pytest.mark.parametrize("mode", ["scan", "apply", "undo", "update", "scan_update"])
def test_application_exits_after_finishing_active_workers(mode):
    probe = Path(__file__).with_name("gui_lifecycle_probe.py")
    result = subprocess.run(
        [sys.executable, str(probe), mode],
        capture_output=True,
        text=True,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_edit_reapplies_sort_and_no_matches_is_explained(qtbot, tmp_path, monkeypatch):
    media = tmp_path / "Media"
    media.mkdir()
    for title in ("Aurora", "Zephyr"):
        (media / f"{title}.2024.1080p-DEMO.mkv").touch()
    window, _, _ = _window(qtbot, tmp_path, monkeypatch)
    _scan(qtbot, window, media)
    window._sort_table_by_column(3)
    source = window.table.item(0, 2).text()
    window.table.item(0, 3).setText("Zzz (2024).mkv")
    assert window.table.item(0, 3).text().startswith("Zephyr")
    assert window.table.item(1, 2).text() == source
    window.search.setText("no matching names")
    assert window.workspace.stack.currentWidget() is window.workspace.no_results_page
    window.workspace.clear_filters.click()
    assert window.workspace.stack.currentWidget() is window.table
    window.extras.toggle()
    assert window.table.rowCount() == 0
    assert "refresh" in window.workspace.summary.text()


def test_offline_start_settings_and_scan_never_use_network(qtbot, tmp_path, monkeypatch):
    import socket

    calls = []

    def no_network(*args, **kwargs):
        calls.append(args)
        raise AssertionError("Unexpected network access")

    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket.socket, "connect", no_network)
    window, _, _ = _window(qtbot, tmp_path, monkeypatch)
    media = tmp_path / "Media"
    media.mkdir()
    (media / "Velora.2024.1080p-DEMO.mkv").touch()

    def cancel_settings():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, SettingsDialog)
        dialog.reject()

    QTimer.singleShot(20, cancel_settings)
    window.settings_action.trigger()
    _scan(qtbot, window, media)
    assert not calls


def test_old_scan_result_is_discarded_after_source_change(scanned_window, tmp_path):
    old_report = scanned_window.current_report
    other = tmp_path / "other"
    other.mkdir()
    scanned_window.path_edit.setText(str(other))
    scanned_window._scan_completed(old_report)
    assert scanned_window.current_report is None
    assert not scanned_window.apply_button.isEnabled()


def _window(qtbot, tmp_path, monkeypatch):
    store = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow(settings_store=store)
    qtbot.addWidget(window)
    history = tmp_path / "history"
    monkeypatch.setattr(window, "_history_dir", lambda: history)
    monkeypatch.setattr(window, "_confirm_apply_changes", lambda *args: True)
    monkeypatch.setattr(window, "_confirm_action", lambda *args: True)
    monkeypatch.setattr(QMessageBox, "information", lambda *args: QMessageBox.StandardButton.Ok)
    errors = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: errors.append(args[-1]))
    return window, history, errors


def _scan(qtbot, window, media):
    window.path_edit.setText(str(media))
    window.scan_button.click()
    qtbot.waitUntil(lambda: window._scan_thread is None and window.current_report is not None)


def test_sorted_filtered_partial_apply_and_history_undo(qtbot, tmp_path, monkeypatch):
    media = tmp_path / "Media"
    media.mkdir()
    filenames = [
        "The.Copper.Comet.2025.1080p-DEMO.mkv",
        "The.Copper.Comet.2025.1080p-DEMO.en.srt",
        "Velora.Observatory.S01E01.1080p-DEMO.mkv",
    ]
    for i, name in enumerate(filenames):
        (media / name).write_bytes(f"unchanged content {i}".encode())
    before = {p.name: p.read_bytes() for p in media.iterdir()}
    window, history, errors = _window(qtbot, tmp_path, monkeypatch)
    _scan(qtbot, window, media)
    window._sort_table_by_column(2)
    window._sort_table_by_column(2)
    for row in range(window.table.rowCount()):
        if "Copper" not in window.table.item(row, 2).text():
            window.table.item(row, 0).setCheckState(Qt.CheckState.Unchecked)
    window.search.setText("Copper")
    movie = next(
        window.table.item(row, 3)
        for row in range(window.table.rowCount())
        if "Copper" in window.table.item(row, 2).text()
        and window.table.item(row, 4).text() == "MKV"
    )
    movie.setText(movie.text().replace("Copper", "Silver"))
    edits = window._selected_edits()
    assert len(edits) == 2
    assert all("Silver" in target for target in edits.values())
    window.apply_button.click()
    qtbot.waitUntil(
        lambda: (
            not window.operations.busy
            and window._scan_thread is None
            and window.current_report is not None
        )
    )
    assert not errors
    for source, name in edits.items():
        assert (media / name).read_bytes() == before[source.name]
    assert (media / filenames[-1]).read_bytes() == before[filenames[-1]]
    dialog = HistoryDialog(history, window)
    qtbot.addWidget(dialog)
    dialog.undo_requested.connect(lambda entry: window._undo_entry(entry, dialog))
    dialog.entries.setCurrentRow(0)
    dialog.undo_button.click()
    qtbot.waitUntil(
        lambda: (
            not window.operations.busy
            and window._scan_thread is None
            and all((media / name).exists() for name in before)
        )
    )
    assert {p.name: p.read_bytes() for p in media.iterdir()} == before
    assert read_history(next(history.glob("rename_undo_*.json"))).undone
    assert not errors


def test_root_folder_apply_and_undo_follow_displayed_path(qtbot, tmp_path, monkeypatch):
    media = tmp_path / "Velora.Observatory.S01.1080p-DEMO"
    media.mkdir()
    original = media / "Velora.Observatory.S01E01.1080p-DEMO.mkv"
    original.write_bytes(b"media unchanged")
    window, history, errors = _window(qtbot, tmp_path, monkeypatch)
    _scan(qtbot, window, media)
    folder_name = window._selected_edits()[media]
    renamed = media.with_name(folder_name)
    window.apply_button.click()
    qtbot.waitUntil(
        lambda: not window.operations.busy and window._scan_thread is None and renamed.is_dir()
    )
    assert Path(window.path_edit.text()) == renamed
    dialog = HistoryDialog(history, window)
    qtbot.addWidget(dialog)
    entry = read_history(next(history.glob("rename_undo_*.json")))
    window._undo_entry(entry, dialog)
    qtbot.waitUntil(
        lambda: not window.operations.busy and window._scan_thread is None and original.exists()
    )
    assert Path(window.path_edit.text()) == media
    assert original.read_bytes() == b"media unchanged"
    assert not errors


def test_failed_apply_rolls_back_and_requires_new_preview(qtbot, tmp_path, monkeypatch):
    media = tmp_path / "Media"
    media.mkdir()
    source = media / "The.Copper.Comet.2025.1080p-DEMO.mkv"
    source.write_bytes(b"preserved")
    window, history, errors = _window(qtbot, tmp_path, monkeypatch)
    _scan(qtbot, window, media)
    destination = source.with_name(window._selected_edits()[source])
    original_replace = core.os.replace
    failed = False

    def fail_once(current, target):
        nonlocal failed
        if Path(target) == destination and not failed:
            failed = True
            raise OSError("Simulated destination failure")
        return original_replace(current, target)

    monkeypatch.setattr(core.os, "replace", fail_once)
    window.apply_button.click()
    qtbot.waitUntil(lambda: not window.operations.busy and bool(errors))
    assert source.read_bytes() == b"preserved"
    assert not destination.exists()
    assert window.current_report is None
    assert not window.apply_button.isEnabled()
    assert window.scan_button.isEnabled()


@pytest.mark.parametrize(
    "payload", [[], {"operations": [None]}, {"scope": "/Media", "operations": ["bad"]}]
)
def test_malformed_history_is_non_actionable(qtbot, tmp_path, payload):
    (tmp_path / "rename_undo_invalid.json").write_text(json.dumps(payload))
    dialog = HistoryDialog(tmp_path)
    qtbot.addWidget(dialog)
    dialog.entries.setCurrentRow(0)
    assert not dialog.undo_button.isEnabled()


def test_settings_cancel_restores_theme_without_persisting(scanned_window):
    window = scanned_window
    saved = window._preferences
    old_report = window.current_report

    def edit_and_cancel():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, SettingsDialog)
        dialog.appearance_buttons["dark" if not window._dark else "light"].click()
        dialog.reject()

    QTimer.singleShot(0, edit_and_cancel)
    window._show_settings()
    assert window.theme_controller.appearance == saved.appearance
    assert window._preferences == saved
    assert window.current_report is old_report


def test_scan_cancel_and_close_wait_for_worker(qtbot, tmp_path, monkeypatch):
    window, history, errors = _window(qtbot, tmp_path, monkeypatch)
    entered, release = threading.Event(), threading.Event()

    def controlled_scan(options, cancelled):
        entered.set()
        release.wait(3)
        if cancelled():
            raise core.ScanCancelled()
        return api.ScanReport(options, core.Report())

    monkeypatch.setattr(api, "scan", controlled_scan)
    window.path_edit.setText(str(tmp_path))
    window.show()
    window.scan_button.click()
    qtbot.waitUntil(entered.is_set)
    window.scan_button.click()
    window.close()
    release.set()
    qtbot.waitUntil(lambda: window._scan_thread is None and not window.isVisible())
    assert not errors
