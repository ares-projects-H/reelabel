"""Folder drops use the actual advertised widgets, not a manually emitted signal."""

import pytest
from PySide6.QtCore import QMimeData, QPoint, QPointF, QSettings, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QApplication

from reelabel.gui.main_window import MainWindow


@pytest.fixture
def window(qtbot, tmp_path):
    widget = MainWindow(
        settings_store=QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    )
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)
    return widget


def mime_for(*paths):
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path)) for path in paths])
    return mime


def enter(target, mime, point=None, actions=Qt.DropAction.CopyAction):
    event = QDragEnterEvent(
        point or target.rect().center(),
        actions,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(target, event)
    return event


def drop(target, mime, point=None):
    event = QDropEvent(
        QPointF(point or target.rect().center()),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(target, event)
    return event


@pytest.mark.parametrize("target_name", ["panel", "center", "title", "hint", "button", "edge"])
def test_every_advertised_drop_area_selects_without_scanning(window, tmp_path, target_name):
    folder = tmp_path / "Fictional Media é"
    folder.mkdir()
    media = folder / "Velora.Observatory.S01E01.mkv"
    media.write_bytes(b"unchanged")
    welcome = window.workspace.empty_page
    targets = {
        "panel": window.drop_zone,
        "center": welcome,
        "title": window.workspace.empty_title,
        "hint": window.workspace.empty_hint,
        "button": window.workspace.empty_browse,
        "edge": welcome,
    }
    target = targets[target_name]
    point = QPoint(12, 12) if target_name == "edge" else target.rect().center()
    mime = mime_for(folder)
    event = enter(target, mime, point)
    assert event.isAccepted()
    zone = window.drop_zone if target_name == "panel" else welcome
    assert zone.property("dragging") is True
    event = drop(target, mime, point)
    assert event.isAccepted()
    assert event.dropAction() == Qt.DropAction.CopyAction
    assert window.path_edit.text() == str(folder)
    assert zone.property("dragging") is False
    assert window._scan_thread is None
    assert window.current_report is None
    assert not window.apply_button.isEnabled()
    assert media.read_bytes() == b"unchanged"


@pytest.mark.parametrize("payload", ["file", "multiple", "remote", "text", "missing", "move_only"])
def test_invalid_drops_do_not_select_or_highlight(window, tmp_path, payload):
    folder = tmp_path / "Folder"
    folder.mkdir()
    media = tmp_path / "Video.mkv"
    media.touch()
    mime = mime_for(folder)
    actions = Qt.DropAction.CopyAction
    if payload == "file":
        mime = mime_for(media)
    elif payload == "multiple":
        mime = mime_for(folder, tmp_path)
    elif payload == "remote":
        mime.setUrls([QUrl("https://example.invalid/folder")])
    elif payload == "text":
        mime = QMimeData()
        mime.setText(str(folder))
    elif payload == "missing":
        mime = mime_for(tmp_path / "missing")
    else:
        actions = Qt.DropAction.MoveAction
    for zone in (window.drop_zone, window.workspace.empty_page):
        assert not enter(zone, mime, actions=actions).isAccepted()
        assert not zone.property("dragging")
    assert not window.path_edit.text()


def test_drag_move_leave_and_busy_lockout(window, tmp_path):
    mime = mime_for(tmp_path)
    for zone in (window.drop_zone, window.workspace.empty_page):
        assert enter(zone, mime).isAccepted()
        move = QDragMoveEvent(
            QPoint(15, 15),
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(zone, move)
        assert move.isAccepted()
        QApplication.sendEvent(zone, QDragLeaveEvent())
        assert zone.property("dragging") is False
        assert enter(zone, mime).isAccepted()
        window._set_scan_controls(False)
        assert zone.property("dragging") is False
        assert not enter(zone, mime).isAccepted()
        assert not window.workspace.empty_browse.isEnabled()
        window._set_scan_controls(True)
        assert enter(zone, mime).isAccepted()
        assert drop(zone, mime).isAccepted()


def test_folder_disappearing_during_drag_is_rejected(window, tmp_path):
    folder = tmp_path / "vanishing"
    folder.mkdir()
    mime = mime_for(folder)
    zone = window.workspace.empty_page
    assert enter(zone, mime).isAccepted()
    folder.rmdir()
    assert not drop(zone, mime).isAccepted()
    assert zone.property("dragging") is False
    assert not window.path_edit.text()


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_welcome_drop_area_is_visible_at_compact_size(window, qtbot, mode):
    window.theme_controller.set_appearance(mode)
    window.resize(1024, 620)
    qtbot.wait(10)
    zone = window.workspace.empty_page
    assert zone.isVisible() and zone.acceptDrops()
    assert zone.property("welcome") is True
    assert zone.height() >= 200
    for control in (
        window.workspace.empty_title,
        window.workspace.empty_hint,
        window.workspace.empty_browse,
    ):
        point = control.mapTo(zone, QPoint(0, 0))
        assert zone.rect().contains(point)
        assert zone.rect().contains(point + QPoint(control.width() - 1, control.height() - 1))
