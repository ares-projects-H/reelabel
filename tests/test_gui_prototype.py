"""Smoke tests for the validation-one read-only interface."""

import importlib.util
import os
import unittest

PYSIDE_AVAILABLE = importlib.util.find_spec("PySide6") is not None

if PYSIDE_AVAILABLE:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from media_renamer.gui.main_window import DEMO_ROWS, MainWindow


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


if __name__ == "__main__":
    unittest.main()
