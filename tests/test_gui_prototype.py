"""Smoke tests for the desktop interface."""

import importlib.util
import os
import unittest
from pathlib import Path

PYSIDE_AVAILABLE = importlib.util.find_spec("PySide6") is not None

if PYSIDE_AVAILABLE:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QSettings, Qt
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QApplication, QHeaderView, QMessageBox

    from reelabel import api
    from reelabel.gui.main_window import DEMO_ROWS, MainWindow
    from reelabel.gui.settings import SettingsValues, load_settings, save_settings
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
        window.close()

    def test_batch_edit_preserves_episode_numbers(self) -> None:
        window = MainWindow(demo=False)
        self.assertEqual(
            window._batch_episode_name(
                "Gothan S04 E01.mkv",
                "Gotham S04 E01.mkv",
                "Gothan S04 E09.ass",
            ),
            "Gotham S04 E09.ass",
        )
        self.assertEqual(
            window._batch_episode_name(
                "Black S01 E01.mkv",
                "Black E01.mkv",
                "Black S01 E10.fr.srt",
            ),
            "Black E10.fr.srt",
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


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
def test_real_scan_runs_in_worker_and_enables_safe_apply(qtbot, tmp_path: Path) -> None:
    (tmp_path / "Campaign.2007.DVDRip.XviD.AC3.mkv").touch()
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
def test_editing_one_episode_can_update_its_folder_group(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    release = tmp_path / "Gothan.S04.1080p.x265-ZMNT"
    release.mkdir()
    for episode in (1, 2):
        (release / f"Gothan.S04E{episode:02d}.1080p.x265-ZMNT.mkv").touch()
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
    edited.setText(edited.text().replace("Gothan", "Gotham"))

    proposals = [
        window.table.item(row, 3).text()
        for row in range(window.table.rowCount())
        if window.table.item(row, 4).text() == "MKV"
    ]
    assert "Gotham S04 E01.mkv" in proposals
    assert "Gotham S04 E02.mkv" in proposals


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
    )
    save_settings(store, expected)

    assert load_settings(store) == expected
    window = MainWindow(demo=False, settings_store=store)
    qtbot.addWidget(window)
    assert window.media_type.currentText() == "Series only"
    assert not window.recursive.isChecked()
    assert window.extras.isChecked()
    assert not window.sidecars.isChecked()
