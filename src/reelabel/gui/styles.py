"""Shared color, spacing and component styles for all Reelabel windows."""

from __future__ import annotations

from .assets import project_asset

PALETTES = {
    "light": dict(
        bg="#F4F6F8",
        surface="#FFFFFF",
        inset="#F8FAFB",
        ink="#182733",
        muted="#536674",
        line="#D8E0E5",
        divider="#9DAEBB",
        accent="#08778B",
        on_accent="#FFFFFF",
        tint="#E7F3F6",
        positive="#18674E",
        warning="#855219",
        hover="#EEF3F6",
        danger="#B33540",
    ),
    "dark": dict(
        bg="#111720",
        surface="#19212C",
        inset="#151D27",
        ink="#EDF3F7",
        muted="#A1B1BF",
        line="#303F4F",
        divider="#617689",
        accent="#65D0E3",
        on_accent="#10232D",
        tint="#223D49",
        positive="#78D5AC",
        warning="#F0C27B",
        hover="#24303E",
        danger="#FF98A1",
    ),
}

SPACING = (4, 8, 12, 16, 24)
ROW_HEIGHT = 40
CONTROL_HEIGHT = 36


def colors(dark: bool = True) -> dict[str, str]:
    """Return semantic colors; callers must not hard-code status colors."""
    return PALETTES["dark" if dark else "light"].copy()


def stylesheet(dark: bool = True) -> str:
    """Style popups application-wide without depending on the OS palette."""
    name = "dark" if dark else "light"
    c = colors(dark)
    return f"""QWidget {{ color: {c["ink"]}; font-size: 13px; }}
            QMainWindow, QWidget#root, QDialog {{ background: {c["bg"]}; }}
            QLabel {{ background: transparent; }}
            QLabel#brand {{ font-size: 20px; font-weight: 700; }}
            QLabel#heading {{ font-size: 24px; font-weight: 650; }}
            QLabel#strong {{ font-size: 14px; font-weight: 600; }}
            QLabel#muted, QLabel#hint {{ color: {c["muted"]}; }}
            QLabel#hint {{ padding: 2px 0; }}
            QLabel#tag {{ color: {c["muted"]}; font-size: 10px; padding: 4px 8px; background: {c["hover"]}; border-radius: 5px; }}
            QFrame#card {{ background: {c["surface"]}; border: 1px solid {c["line"]}; border-radius: 12px; }}
            QFrame#rule {{ background: {c["line"]}; border: none; }}
            QPushButton {{ background: {c["surface"]}; border: 1px solid {c["line"]}; border-radius: 7px; padding: 8px 13px; min-height: 18px; font-weight: 550; }}
            QPushButton:hover {{ background: {c["hover"]}; border-color: {c["divider"]}; }}
            QPushButton:pressed {{ background: {c["tint"]}; }}
            QPushButton:focus {{ border: 2px solid {c["accent"]}; padding: 7px 12px; }}
            QPushButton#primary {{ background: {c["accent"]}; border-color: {c["accent"]}; color: {c["on_accent"]}; font-weight: 650; }}
            QPushButton#primary:hover {{ border-color: {c["ink"]}; }}
            QPushButton:disabled {{ color: {c["muted"]}; background: {c["hover"]}; border-color: {c["line"]}; }}
            QPushButton#primary:disabled {{ color: {c["muted"]}; background: {c["hover"]}; border-color: {c["line"]}; }}
            QPushButton#quiet {{ border-color: transparent; background: transparent; }}
            QPushButton#quiet:hover {{ background: {c["hover"]}; }}
            QPushButton#filter {{ border-color: transparent; background: transparent; color: {c["muted"]}; }}
            QPushButton#filter:checked {{ background: {c["tint"]}; color: {c["ink"]}; border-color: {c["line"]}; }}
            QPushButton#segment:checked {{ background: {c["tint"]}; border-color: {c["accent"]}; }}
            QLineEdit, QComboBox {{ background: {c["surface"]}; border: 1px solid {c["line"]}; border-radius: 7px; padding: 8px 11px; min-height: 18px; selection-background-color: {c["accent"]}; selection-color: {c["on_accent"]}; }}
            QLineEdit:focus, QComboBox:focus {{ border-color: {c["accent"]}; }}
            QComboBox::drop-down {{ width: 26px; border: none; }}
            QComboBox::down-arrow {{ image: url("{(project_asset(f"ui/chevron-{name}.svg")).as_posix()}"); width: 16px; height: 16px; }}
            QComboBox QAbstractItemView {{ background: {c["surface"]}; color: {c["ink"]}; selection-background-color: {c["tint"]}; selection-color: {c["ink"]}; border: 1px solid {c["divider"]}; padding: 6px; outline: 0; }}
            QComboBox QAbstractItemView::item {{ min-height: 30px; padding: 4px 8px; }}
            QCheckBox {{ spacing: 8px; background: transparent; }}
            QCheckBox:focus {{ outline: 1px solid {c["accent"]}; }}
            QCheckBox::indicator, QAbstractItemView::indicator {{ width: 16px; height: 16px; border: 1px solid {c["divider"]}; border-radius: 3px; background: {c["surface"]}; }}
            QCheckBox::indicator:checked, QAbstractItemView::indicator:checked {{ background: {c["accent"]}; border-color: {c["accent"]}; image: url("{(project_asset(f"ui/check-{name}.svg")).as_posix()}"); }}
            QCheckBox::indicator:hover {{ border-color: {c["accent"]}; }}
            QTableWidget {{ background: {c["surface"]}; border: 1px solid {c["line"]}; border-radius: 9px; selection-background-color: {c["tint"]}; selection-color: {c["ink"]}; gridline-color: {c["line"]}; }}
            QTableWidget::item {{ border-bottom: 1px solid {c["line"]}; padding: 7px 10px; }}
            QTableWidget::item:selected {{ background: {c["tint"]}; }}
            QHeaderView::section {{ background: {c["inset"]}; color: {c["muted"]}; border: none; border-right: 1px solid {c["divider"]}; border-bottom: 1px solid {c["line"]}; padding: 11px 10px; font-weight: 600; font-size: 12px; text-align: left; }}
            QScrollBar:vertical {{ background: {c["inset"]}; width: 10px; margin: 0; }}
            QScrollBar:horizontal {{ background: {c["inset"]}; height: 10px; margin: 0; }}
            QScrollBar::handle {{ background: {c["divider"]}; border-radius: 4px; min-height: 24px; min-width: 24px; }}
            QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
            QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
            QScrollArea {{ border: none; background: transparent; }}
            QScrollArea > QWidget > QWidget {{ background: {c["bg"]}; }}
            QProgressBar {{ border: none; background: {c["line"]}; border-radius: 2px; }}
            QProgressBar::chunk {{ background: {c["accent"]}; }}
            QMenuBar, QMenu {{ background: {c["surface"]}; color: {c["ink"]}; }}
            QMenu {{ border: 1px solid {c["line"]}; padding: 5px; }}
            QMenu::item {{ padding: 8px 18px; }}
            QMenu::item:selected {{ background: {c["tint"]}; }}
            QToolTip {{ color: {c["ink"]}; background: {c["surface"]}; border: 1px solid {c["divider"]}; padding: 6px; }}
    QLabel#title, QLabel#dialogTitle {{ font-size: 24px; font-weight: 650; }}
    QLabel#sectionTitle {{ font-size: 14px; font-weight: 600; }}
    QLabel#subtitle, QLabel#pathHint, QLabel#safeNotice {{ color: {c["muted"]}; }}
    QLabel#safeNotice {{ background: transparent; padding: 2px 0; }}
    QLineEdit#pathInput {{ background: transparent; border-color: transparent; color: {c["muted"]}; padding: 2px 0; min-height: 18px; }}
    QLineEdit#pathInput:focus {{ border-bottom: 1px solid {c["accent"]}; }}
    QFrame#dropZone {{ background: {c["surface"]}; border: 1px solid {c["line"]}; border-radius: 12px; }}
    QFrame#dropZone[dragging="true"] {{ border: 2px solid {c["accent"]}; }}
    QPushButton#filter[active="true"] {{ background: {c["tint"]}; color: {c["ink"]}; border-color: {c["line"]}; }}
    QPushButton#danger {{ background: {c["danger"]}; color: {c["bg"]}; }}
    QMenu::item:disabled {{ color: {c["muted"]}; }}
    QListWidget {{ background: {c["surface"]}; color: {c["ink"]}; selection-background-color: {c["tint"]}; selection-color: {c["ink"]}; border: 1px solid {c["line"]}; border-radius: 8px; padding: 4px; }}
    QListWidget::item {{ padding: 10px; border-bottom: 1px solid {c["line"]}; }}
    QListWidget::item:selected {{ background: {c["tint"]}; color: {c["ink"]}; }}
    QListWidget::item:disabled {{ color: {c["muted"]}; }}
    QTableWidget:focus, QListWidget:focus {{ border: 1px solid {c["accent"]}; }}
    QCheckBox:disabled, QLineEdit:disabled, QComboBox:disabled {{ color: {c["muted"]}; }}
    QLabel#updateActivity {{ color: {c["accent"]}; }}
"""
