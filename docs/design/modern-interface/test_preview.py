"""Checks for the disposable design study, not production acceptance tests."""

import socket

import pytest
from preview import DesignPreview
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QPushButton, QScrollArea


@pytest.fixture
def window(monkeypatch):
    def forbid_network(*args, **kwargs):
        raise AssertionError("The design study must not make a network connection")

    monkeypatch.setattr(socket.socket, "connect", forbid_network)
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    subject = DesignPreview()
    subject.show()
    app.processEvents()
    yield subject
    for dialog in subject.open_dialogs:
        dialog.close()
    subject.close()
    app.processEvents()


def test_filters_search_and_readonly_columns(window):
    window.filter_buttons["Review"].click()
    visible = [i for i in range(window.table.rowCount()) if not window.table.isRowHidden(i)]
    assert len(visible) == 1
    window.table.selectRow(visible[0])
    assert not window.edit_button.isEnabled()
    window.filter_buttons["Ready"].click()
    window.search.setText("copper")
    visible = [i for i in range(window.table.rowCount()) if not window.table.isRowHidden(i)]
    assert len(visible) == 2
    window.table.selectRow(visible[0])
    assert window.edit_button.isEnabled()
    for col in (0, 1, 3, 4):
        assert not window.table.item(visible[0], col).flags() & Qt.ItemFlag.ItemIsEditable
    window.table.item(visible[0], 2).setText("A fictional correction.mkv")
    assert "in memory" in window.detail.text()


def test_options_invalidate_preview_and_empty_state_clears_counts(window):
    assert window.apply_button.isEnabled()
    window.media.setCurrentIndex(1)
    assert not window.apply_button.isEnabled()
    assert "refresh" in window.notice.text()
    window.show_empty()
    assert window.table.rowCount() == 0
    assert not window.review_toolbar.isVisible()
    assert not window.apply_button.isEnabled()
    window.simulate_scan()
    assert window.busy
    window.simulate_scan()
    QTest.qWait(1200)
    assert not window.busy
    assert window.table.rowCount() == 0
    assert "cancelled" in window.notice.text()


def test_settings_theme_choices_and_bounded_combo(window):
    dialog = window.show_settings()
    for theme in ("Light", "Dark", "System"):
        next(b for b in dialog.findChildren(QPushButton) if b.text() == theme).click()
        if theme != "System":
            assert window.theme == theme.lower()
    combo = dialog.findChild(QComboBox)
    width = combo.width()
    for size in ((900, 850), (550, 450)):
        dialog.resize(*size)
        QApplication.processEvents()
        assert combo.width() == width
        for i in range(combo.count()):
            assert combo.fontMetrics().horizontalAdvance(combo.itemText(i)) + 42 <= width
    scroll = dialog.findChild(QScrollArea)
    assert scroll.verticalScrollBar().maximum() > 0
    scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
    QApplication.processEvents()
    check = next(b for b in dialog.findChildren(QPushButton) if b.text() == "Check for updates")
    assert scroll.viewport().rect().contains(check.mapTo(scroll.viewport(), check.rect().center()))


def test_simulated_dialogs_and_update_result(window):
    for open_dialog in (window.confirm_apply, window.show_history, window.show_about):
        dialog = open_dialog()
        assert dialog.isVisible()
        dialog.close()
    update = window.show_update()
    QTest.qWait(1000)
    assert any("up to date" in label.text() for label in update.findChildren(QLabel))


def test_compact_window_keeps_actions_accessible(window):
    window.resize(900, 600)
    QApplication.processEvents()
    for control in (
        window.preview_button,
        window.settings_button,
        window.edit_button,
        window.apply_button,
    ):
        assert window.rect().contains(control.mapTo(window, control.rect().topLeft()))
        assert window.rect().contains(control.mapTo(window, control.rect().bottomRight()))
    assert window.table.viewport().height() >= 70
