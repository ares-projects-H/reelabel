"""Smoke tests for the desktop interface."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

PYSIDE_AVAILABLE = importlib.util.find_spec("PySide6") is not None

if PYSIDE_AVAILABLE:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QSettings, Qt, QTimer
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QApplication, QHeaderView, QLabel, QMessageBox

    from reelabel import __version__, api, updates
    from reelabel.gui.main_window import DEMO_ROWS, KIND_ROLE, MainWindow
    from reelabel.gui.settings import (
        SettingsDialog,
        SettingsValues,
        load_settings,
        save_settings,
    )
    from reelabel.gui.styles import stylesheet


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
class GuiPrototypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_prototype_loads_demo_rows(self) -> None:
        window = MainWindow(demo=True)
        self.assertEqual(window.windowTitle(), "Reelabel")
        self.assertEqual(window.table.rowCount(), len(DEMO_ROWS))
        self.assertFalse(window.apply_button.isEnabled())
        self.assertFalse(window.sidecars.isChecked())
        window.close()

    def test_proposed_names_are_editable(self) -> None:
        window = MainWindow(demo=True)
        item = window.table.item(0, 3)
        self.assertTrue(item.flags() & Qt.ItemFlag.ItemIsEditable)
        window.close()

    def test_every_preview_column_can_be_resized(self) -> None:
        window = MainWindow(demo=True)
        header = window.table.horizontalHeader()
        for column in range(window.table.columnCount()):
            self.assertEqual(
                header.sectionResizeMode(column),
                QHeaderView.ResizeMode.Interactive,
            )
        window.close()

    def test_filter_buttons_show_the_selected_category(self) -> None:
        window = MainWindow(demo=True)
        window.filter_buttons["review"].click()
        visible = [
            row for row in range(window.table.rowCount()) if not window.table.isRowHidden(row)
        ]
        self.assertEqual(len(visible), 1)
        self.assertEqual(window.table.item(visible[0], 1).text(), "Review")

        window.filter_buttons["all"].click()
        self.assertFalse(
            any(window.table.isRowHidden(row) for row in range(window.table.rowCount()))
        )
        window.close()

    def test_theme_uses_the_platform_font(self) -> None:
        self.assertNotIn("Inter", stylesheet())

    def test_header_dividers_are_visible_in_both_themes(self) -> None:
        self.assertIn("border-right: 1px solid #435476;", stylesheet(dark=True))
        self.assertIn("border-right: 1px solid #b6c3d6;", stylesheet(dark=False))

    def test_popup_controls_have_explicit_colors_in_both_themes(self) -> None:
        for dark in (False, True):
            theme = stylesheet(dark=dark)
            self.assertIn("QComboBox QAbstractItemView {", theme)
            self.assertIn("selection-color: #07101d;", theme)
            self.assertIn("QToolTip {", theme)
            self.assertIn("QScrollBar:vertical, QScrollBar:horizontal {", theme)
            self.assertIn("QListWidget {", theme)
            self.assertIn("QListWidget::item:disabled {", theme)

    def test_settings_dropdowns_fit_their_complete_labels(self) -> None:
        dialog = SettingsDialog(SettingsValues())
        self.assertGreaterEqual(dialog.minimumWidth(), 560)
        self.assertGreaterEqual(dialog.minimumHeight(), 680)
        for combo in (dialog.appearance, dialog.media_scope):
            widest_label = max(
                combo.fontMetrics().horizontalAdvance(combo.itemText(index))
                for index in range(combo.count())
            )
            control_width = max(160, widest_label + 48)
            popup_width = max(200, widest_label + 64)
            self.assertGreaterEqual(combo.minimumWidth(), control_width)
            self.assertGreaterEqual(combo.view().minimumWidth(), popup_width)
        dialog.close()

    def test_selected_theme_is_applied_application_wide(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = QSettings(
                str(Path(directory) / "reelabel-theme-test.ini"),
                QSettings.Format.IniFormat,
            )
            save_settings(store, SettingsValues(appearance="light"))
            window = MainWindow(demo=False, settings_store=store)
            self.assertEqual(
                QApplication.instance().styleSheet(),
                stylesheet(dark=False),
            )
            window.close()

    def test_native_application_menu_roles_exist(self) -> None:
        window = MainWindow(demo=False)
        self.assertEqual(
            window.settings_action.menuRole(),
            QAction.MenuRole.PreferencesRole,
        )
        self.assertEqual(window.about_action.menuRole(), QAction.MenuRole.AboutRole)
        self.assertEqual(window.quit_action.menuRole(), QAction.MenuRole.QuitRole)
        # On Windows and Linux these actions stay in the visible File and Help
        # menus. macOS relocates them using the native roles checked above.
        self.assertIn(window.settings_action, window.file_menu.actions())
        self.assertIn(window.quit_action, window.file_menu.actions())
        self.assertIn(window.about_action, window.help_menu.actions())
        self.assertIn(window.user_guide_action, window.help_menu.actions())
        self.assertIn(window.check_updates_action, window.help_menu.actions())
        window.close()

    def test_settings_explain_the_manual_update_connection(self) -> None:
        dialog = SettingsDialog(SettingsValues())
        self.assertEqual(dialog.current_version.text(), f"Installed version: {__version__}")
        self.assertEqual(dialog.check_updates_button.text(), "Check for updates")
        labels = " ".join(label.text() for label in dialog.findChildren(QLabel))
        self.assertIn("connects to GitHub only when you click", labels)
        self.assertIn("never downloads or installs", labels)
        dialog.close()

    def test_batch_edit_preserves_episode_numbers(self) -> None:
        window = MainWindow(demo=False)
        self.assertEqual(
            window._batch_episode_name(
                "Lumen Harbr S04 E01.mkv",
                "Lumen Harbor S04 E01.mkv",
                "Lumen Harbr S04 E09.ass",
            ),
            "Lumen Harbor S04 E09.ass",
        )
        self.assertEqual(
            window._batch_episode_name(
                "Obsidian S01 E01.mkv",
                "Obsidian E01.mkv",
                "Obsidian S01 E10.fr.srt",
            ),
            "Obsidian E10.fr.srt",
        )
        window.close()

    def test_movie_edit_preserves_subtitle_suffixes(self) -> None:
        window = MainWindow(demo=False)
        self.assertEqual(
            window._batch_movie_sidecar_name(
                "Paper Moons (2018).mkv",
                "Paper Moon (2018).mkv",
                "Paper Moons (2018).fr.forced.srt",
            ),
            "Paper Moon (2018).fr.forced.srt",
        )
        self.assertIsNone(
            window._batch_movie_sidecar_name(
                "Paper Moons (2018).mkv",
                "Paper Moon (2018).mkv",
                "Another Movie (2018).srt",
            )
        )
        window.close()

    def test_permanent_deletion_confirmation_defaults_to_cancel(self) -> None:
        window = MainWindow(demo=False)
        message, accept = window._confirmation_dialog(
            "Permanently delete related files?",
            "Delete one selected image?",
            "This deletion cannot be undone.",
            "Delete permanently",
            accept_is_default=False,
        )
        self.assertIsNot(message.defaultButton(), accept)
        self.assertIs(
            message.defaultButton(),
            message.button(QMessageBox.StandardButton.Cancel),
        )
        message.close()
        window.close()


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
def test_real_scan_runs_in_worker_and_enables_safe_apply(qtbot, tmp_path: Path) -> None:
    (tmp_path / "Glass Meridian.2007.DVDRip.XviD.AC3.mkv").touch()
    window = MainWindow(demo=False)
    qtbot.addWidget(window)
    window.path_edit.setText(str(tmp_path))

    window.scan_button.click()

    qtbot.waitUntil(
        lambda: window.current_report is not None and window._scan_thread is None,
        timeout=3000,
    )
    assert window.table.rowCount() >= 1
    assert window.apply_button.isEnabled()


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
def test_startup_settings_and_scan_do_not_check_for_updates(qtbot, tmp_path: Path) -> None:
    calls: list[bool] = []

    def unexpected_update_check():
        calls.append(True)
        raise AssertionError("Update checks must require an explicit click")

    (tmp_path / "Glass Meridian.2007.DVDRip.XviD.AC3.mkv").touch()
    window = MainWindow(demo=False, update_checker=unexpected_update_check)
    qtbot.addWidget(window)
    dialog = SettingsDialog(SettingsValues(), window)
    dialog.show()
    dialog.close()
    window.path_edit.setText(str(tmp_path))
    window.scan_button.click()
    qtbot.waitUntil(lambda: window._scan_thread is None, timeout=3000)

    assert calls == []


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
def test_manual_update_button_runs_worker_and_reports_result(qtbot, monkeypatch) -> None:
    calls: list[bool] = []
    result = updates.UpdateCheckResult(
        current_version="0.1.0",
        latest_version="0.2.0",
        update_available=True,
        release_url="https://github.com/ares-projects-H/reelabel/releases/tag/v0.2.0",
    )

    def check_now():
        calls.append(True)
        return result

    window = MainWindow(demo=False, update_checker=check_now)
    qtbot.addWidget(window)
    shown: list[tuple[updates.UpdateCheckResult, object]] = []
    dialog = SettingsDialog(SettingsValues(), window)
    qtbot.addWidget(dialog)
    dialog.check_updates_requested.connect(lambda: window._start_update_check(dialog))
    dialog.show()

    def record_result(update_result, parent=None):
        # Progress controls must be restored before any modal result appears.
        assert dialog.check_updates_button.isEnabled()
        assert window.check_updates_action.isEnabled()
        shown.append((update_result, parent))

    monkeypatch.setattr(window, "_show_update_result", record_result)

    assert calls == []
    dialog.check_updates_button.click()
    qtbot.waitUntil(
        lambda: window._update_thread is None and bool(shown),
        timeout=3000,
    )

    assert calls == [True]
    assert shown == [(result, dialog)]
    assert dialog.check_updates_button.isEnabled()
    assert dialog.update_status.text() == "Reelabel 0.2.0 is available."


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
def test_failed_update_check_restores_button_and_shows_error(qtbot, monkeypatch) -> None:
    def fail_check():
        raise updates.UpdateNetworkError("offline")

    window = MainWindow(demo=False, update_checker=fail_check)
    qtbot.addWidget(window)
    dialog = SettingsDialog(SettingsValues(), window)
    qtbot.addWidget(dialog)
    dialog.check_updates_requested.connect(lambda: window._start_update_check(dialog))
    dialog.show()
    shown: list[tuple[str, object]] = []

    def record_failure(reason: str, parent=None):
        assert dialog.check_updates_button.isEnabled()
        assert window.check_updates_action.isEnabled()
        shown.append((reason, parent))

    monkeypatch.setattr(window, "_show_update_failure", record_failure)
    dialog.check_updates_button.click()
    qtbot.waitUntil(
        lambda: window._update_thread is None and bool(shown),
        timeout=3000,
    )

    assert shown == [("network", dialog)]
    assert dialog.check_updates_button.text() == "Check for updates"
    assert dialog.update_status.text().startswith("Reelabel could not reach GitHub.")


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
def test_update_result_messages_cover_current_and_newer_builds(qtbot, monkeypatch) -> None:
    window = MainWindow(demo=False)
    qtbot.addWidget(window)
    messages: list[tuple[str, str]] = []
    monkeypatch.setattr(
        window,
        "_show_update_information",
        lambda parent, title, text: messages.append((title, text)),
    )

    window._show_update_result(
        updates.UpdateCheckResult(
            current_version="0.2.0",
            latest_version="0.2.0",
            update_available=False,
            release_url="https://github.com/ares-projects-H/reelabel/releases/tag/v0.2.0",
        )
    )
    window._show_update_result(
        updates.UpdateCheckResult(
            current_version="0.2.0",
            latest_version="0.1.0",
            update_available=False,
            release_url="https://github.com/ares-projects-H/reelabel/releases/tag/v0.1.0",
            current_is_newer=True,
        )
    )

    assert messages == [
        (
            "Reelabel is up to date",
            "You are using the latest published version (0.2.0).",
        ),
        (
            "No update available",
            "This Reelabel 0.2.0 build is newer than the latest published release "
            "(0.1.0).",
        ),
    ]


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
def test_editing_one_episode_can_update_its_folder_group(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    release = tmp_path / "Lumen Harbr.S04.1080p.x265-ZMNT"
    release.mkdir()
    for episode in (1, 2):
        (release / f"Lumen Harbr.S04E{episode:02d}.1080p.x265-ZMNT.mkv").touch()
    report = api.scan(api.ScanOptions(tmp_path))
    window = MainWindow(demo=False)
    qtbot.addWidget(window)
    window.current_report = report
    window._populate_report(report)
    monkeypatch.setattr(window, "_confirm_action", lambda *args: True)

    edited = next(
        window.table.item(row, 3)
        for row in range(window.table.rowCount())
        if "E01.mkv" in window.table.item(row, 3).text()
    )
    edited.setText(edited.text().replace("Lumen Harbr", "Lumen Harbor"))

    proposals = [
        window.table.item(row, 3).text()
        for row in range(window.table.rowCount())
        if window.table.item(row, 4).text() == "MKV"
    ]
    assert "Lumen Harbor S04 E01.mkv" in proposals
    assert "Lumen Harbor S04 E02.mkv" in proposals


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
def test_preview_without_a_folder_shows_a_clear_error(qtbot, monkeypatch) -> None:
    window = MainWindow(demo=False)
    qtbot.addWidget(window)
    warnings: list[tuple[str, str]] = []

    def record_warning(parent, title: str, message: str):
        warnings.append((title, message))
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "warning", record_warning)
    window.path_edit.clear()
    window.scan_button.click()

    assert warnings == [("Choose a folder", "Choose a media folder before previewing changes.")]
    assert window.current_report is None


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
def test_clicking_a_preview_header_toggles_sort_order(qtbot) -> None:
    window = MainWindow(demo=True)
    qtbot.addWidget(window)
    header = window.table.horizontalHeader()

    header.sectionClicked.emit(2)
    ascending = [window.table.item(row, 2).text() for row in range(window.table.rowCount())]

    header.sectionClicked.emit(2)
    descending = [window.table.item(row, 2).text() for row in range(window.table.rowCount())]
    assert descending == list(reversed(ascending))
    assert header.sortIndicatorOrder() == Qt.SortOrder.DescendingOrder


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
def test_editing_a_movie_can_update_related_subtitles(qtbot, tmp_path: Path, monkeypatch) -> None:
    for suffix in (".mkv", ".srt", ".fr.forced.ass"):
        (tmp_path / f"Paper.Moons.2018.1080p-DEMO{suffix}").touch()
    report = api.scan(api.ScanOptions(tmp_path))
    window = MainWindow(demo=False)
    qtbot.addWidget(window)
    window.current_report = report
    window._populate_report(report)
    monkeypatch.setattr(window, "_confirm_action", lambda *args: True)

    original_subtitles = {
        window.table.item(row, 3).text()
        for row in range(window.table.rowCount())
        if window.table.item(row, 4).text() in {"SRT", "ASS"}
    }
    edited = next(
        window.table.item(row, 3)
        for row in range(window.table.rowCount())
        if window.table.item(row, 4).text() == "MKV"
    )
    original_movie = edited.text()
    edited.setText(edited.text().replace("Paper Moons", "Paper Moon"))

    proposals = {window.table.item(row, 3).text() for row in range(window.table.rowCount())}
    edited_movie = original_movie.replace("Paper Moons", "Paper Moon")
    assert edited_movie in proposals
    for subtitle in original_subtitles:
        assert (Path(edited_movie).stem + subtitle[len(Path(original_movie).stem) :]) in proposals


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
def test_settings_persist_and_apply_safe_defaults(qtbot, tmp_path: Path) -> None:
    store = QSettings(str(tmp_path / "reelabel-test.ini"), QSettings.Format.IniFormat)
    expected = SettingsValues(
        appearance="light",
        media_scope="series",
        recursive=False,
        include_extras=True,
        show_apply_confirmation=False,
    )
    save_settings(store, expected)

    assert load_settings(store) == expected
    window = MainWindow(demo=False, settings_store=store)
    qtbot.addWidget(window)
    assert window.media_type.currentText() == "Series only"
    assert not window.recursive.isChecked()
    assert window.extras.isChecked()
    assert not window.sidecars.isChecked()
    assert not window._preferences.show_apply_confirmation


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
def test_apply_confirmation_opt_out_can_be_restored(
    qtbot,
    tmp_path: Path,
) -> None:
    store = QSettings(str(tmp_path / "confirmation-test.ini"), QSettings.Format.IniFormat)
    window = MainWindow(demo=False, settings_store=store)
    qtbot.addWidget(window)

    def accept_and_hide() -> None:
        message = QApplication.activeModalWidget()
        assert isinstance(message, QMessageBox)
        checkbox = message.checkBox()
        assert checkbox is not None
        assert checkbox.text() == "Don't show again"
        checkbox.setChecked(True)
        accept = next(
            button
            for button in message.buttons()
            if message.buttonRole(button) == QMessageBox.ButtonRole.AcceptRole
        )
        accept.click()

    QTimer.singleShot(0, accept_and_hide)
    assert window._confirm_apply_changes(
        "Rename 2 files?",
        "Every destination will be checked again.",
    )
    assert not window._preferences.show_apply_confirmation
    assert not load_settings(store).show_apply_confirmation

    restored = SettingsDialog(load_settings(store), window)
    restored.apply_confirmation.setChecked(True)
    save_settings(store, restored.values())
    assert load_settings(store).show_apply_confirmation


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
def test_hiding_apply_reminder_does_not_hide_sidecar_warning(
    qtbot,
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "Aurora.Archive.2026.mkv").touch()
    poster = tmp_path / "poster.jpg"
    poster.touch()
    store = QSettings(str(tmp_path / "sidecar-test.ini"), QSettings.Format.IniFormat)
    save_settings(store, SettingsValues(show_apply_confirmation=False))
    report = api.scan(api.ScanOptions(tmp_path, include_sidecars=True))
    window = MainWindow(demo=False, settings_store=store)
    qtbot.addWidget(window)
    window.current_report = report
    window._populate_report(report)

    for row in range(window.table.rowCount()):
        if window.table.item(row, 1).data(KIND_ROLE) == "sidecar":
            window.table.item(row, 0).setCheckState(Qt.CheckState.Checked)

    confirmations: list[tuple[str, str, str, str]] = []
    monkeypatch.setattr(
        window,
        "_confirm_action",
        lambda *args: confirmations.append(args) or False,
    )
    window._apply_selected()

    assert confirmations
    assert confirmations[0][0] == "Permanently delete related files?"
    assert confirmations[0][4] is True
    assert poster.exists()
