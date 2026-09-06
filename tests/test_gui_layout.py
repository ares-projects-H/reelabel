"""Geometry and keyboard checks, also run under simulated Qt display scales."""

from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QLineEdit

from reelabel.gui.main_window import MainWindow
from reelabel.gui.settings import SettingsDialog, SettingsValues


def test_compact_workspace_and_keyboard_editor(qtbot, tmp_path):
    window = MainWindow(
        demo=True, settings_store=QSettings(str(tmp_path / "test.ini"), QSettings.IniFormat)
    )
    qtbot.addWidget(window)
    window.resize(1024, 620)
    window.show()
    qtbot.wait(10)
    for control in (
        window.scan_button,
        window.workspace.browse_button,
        window.apply_button,
        window.edit_button,
        window.search,
    ):
        point = control.mapTo(window, QPoint(0, 0))
        assert point.x() >= 0 and point.y() >= 0
        assert point.x() + control.width() <= window.width()
        assert point.y() + control.height() <= window.height()
    assert window.table.height() >= 150
    window.table.setCurrentCell(0, 3)
    window.edit_button.click()
    qtbot.wait(10)
    assert isinstance(QApplication.focusWidget(), QLineEdit)
    qtbot.keyClick(QApplication.focusWidget(), Qt.Key.Key_Escape)


def test_settings_fit_and_system_changes_are_live(qtbot, tmp_path, monkeypatch):
    window = MainWindow(settings_store=QSettings(str(tmp_path / "test.ini"), QSettings.IniFormat))
    qtbot.addWidget(window)
    dialog = SettingsDialog(SettingsValues(), window)
    qtbot.addWidget(dialog)
    dialog.resize(550, 420)
    dialog.show()
    qtbot.wait(10)
    width = dialog.media_scope.width()
    assert dialog.scroll.verticalScrollBar().maximum() > 0
    buttons = dialog.findChild(QDialogButtonBox)
    assert buttons.mapTo(dialog, QPoint(0, buttons.height())).y() <= dialog.height()
    dialog.resize(1000, 850)
    qtbot.wait(10)
    assert dialog.media_scope.width() == width
    for index in range(dialog.media_scope.count()):
        assert (
            dialog.media_scope.fontMetrics().horizontalAdvance(dialog.media_scope.itemText(index))
            + 32
            < width
        )
    for dark in (True, False):
        monkeypatch.setattr(window.theme_controller, "system_is_dark", lambda: dark)
        window.theme_controller.set_appearance("system")
        window.theme_controller._system_changed(
            Qt.ColorScheme.Dark if dark else Qt.ColorScheme.Light
        )
        assert window.theme_controller.dark is dark
        assert window.table.dark is dark
    window.theme_controller.set_appearance("light")
    monkeypatch.setattr(window.theme_controller, "system_is_dark", lambda: True)
    window.theme_controller._system_changed(Qt.ColorScheme.Dark)
    assert not window.theme_controller.dark
