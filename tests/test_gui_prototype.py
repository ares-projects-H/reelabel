"""Smoke tests for the desktop interface."""

import importlib.util
import os
import unittest
from pathlib import Path

PYSIDE_AVAILABLE = importlib.util.find_spec("PySide6") is not None

if PYSIDE_AVAILABLE:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from media_renamer import api
    from media_renamer.gui.main_window import DEMO_ROWS, MainWindow
    from media_renamer.gui.styles import stylesheet


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
class GuiPrototypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_prototype_loads_demo_rows(self) -> None:
        window = MainWindow(demo=True)
        self.assertEqual(window.windowTitle(), "Media Renamer")
        self.assertEqual(window.table.rowCount(), len(DEMO_ROWS))
        self.assertFalse(window.apply_button.isEnabled())
        self.assertFalse(window.sidecars.isChecked())
        window.close()

    def test_proposed_names_are_editable(self) -> None:
        window = MainWindow(demo=True)
        item = window.table.item(0, 3)
        self.assertTrue(item.flags() & Qt.ItemFlag.ItemIsEditable)
        window.close()

    def test_filter_buttons_show_the_selected_category(self) -> None:
        window = MainWindow(demo=True)
        window.filter_buttons["review"].click()
        visible = [
            row
            for row in range(window.table.rowCount())
            if not window.table.isRowHidden(row)
        ]
        self.assertEqual(len(visible), 1)
        self.assertEqual(window.table.item(visible[0], 1).text(), "Review")

        window.filter_buttons["all"].click()
        self.assertFalse(
            any(
                window.table.isRowHidden(row)
                for row in range(window.table.rowCount())
            )
        )
        window.close()

    def test_theme_uses_the_platform_font(self) -> None:
        self.assertNotIn("Inter", stylesheet())

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


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
def test_real_scan_runs_in_worker_and_enables_safe_apply(
    qtbot, tmp_path: Path
) -> None:
    (tmp_path / "Campaign.2007.DVDRip.XviD.AC3.mkv").touch()
    window = MainWindow(demo=False)
    qtbot.addWidget(window)
    window.path_edit.setText(str(tmp_path))

    window.scan_button.click()

    qtbot.waitUntil(
        lambda: window.current_report is not None
        and window._scan_thread is None,
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
