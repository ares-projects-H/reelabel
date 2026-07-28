"""Application-wide visual tokens and Qt styles."""

from __future__ import annotations


def stylesheet(dark: bool = True) -> str:
    """Return the prototype theme.

    Colors are centralized here so a contributor can adjust the visual system
    without hunting through widget construction code.
    """
    if dark:
        colors = {
            "window": "#0b1020",
            "surface": "#11182b",
            "surface_2": "#17213a",
            "border": "#263553",
            "header_divider": "#435476",
            "text": "#f5f7ff",
            "muted": "#9aa8c7",
            "accent": "#2bc7f2",
            "accent_hover": "#5ed8f7",
            "positive": "#41d39a",
            "warning": "#ffbe55",
            "danger": "#ff7185",
        }
    else:
        colors = {
            "window": "#f4f7fb",
            "surface": "#ffffff",
            "surface_2": "#edf3fa",
            "border": "#d5deeb",
            "header_divider": "#b6c3d6",
            "text": "#16213a",
            "muted": "#64728f",
            "accent": "#087ea4",
            "accent_hover": "#056985",
            "positive": "#117a59",
            "warning": "#9a6100",
            "danger": "#b4233c",
        }

    return f"""
    * {{
        font-size: 13px;
        color: {colors["text"]};
    }}
    QMainWindow, QWidget#root, QDialog, QMessageBox {{
        background: {colors["window"]};
    }}
    QMenuBar {{
        background: {colors["window"]};
        color: {colors["text"]};
    }}
    QMenuBar::item:selected {{
        background: {colors["surface_2"]};
        border-radius: 5px;
    }}
    QMenu {{
        background: {colors["surface"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
        padding: 5px;
    }}
    QMenu::item {{
        padding: 7px 28px 7px 12px;
        border-radius: 5px;
    }}
    QMenu::item:selected {{
        background: {colors["surface_2"]};
    }}
    QMenu::separator {{
        height: 1px;
        background: {colors["border"]};
        margin: 5px 8px;
    }}
    QMessageBox QLabel#qt_msgbox_label,
    QMessageBox QLabel#qt_msgbox_informativelabel {{
        min-width: 420px;
    }}
    QFrame#card, QFrame#dropZone, QFrame#summaryCard {{
        background: {colors["surface"]};
        border: 1px solid {colors["border"]};
        border-radius: 14px;
    }}
    QFrame#dropZone:hover {{
        border: 1px solid {colors["accent"]};
        background: {colors["surface_2"]};
    }}
    QLabel#brand {{
        font-size: 20px;
        font-weight: 700;
    }}
    QLabel#eyebrow {{
        color: {colors["accent"]};
        font-size: 11px;
        font-weight: 700;
    }}
    QLabel#title {{
        font-size: 28px;
        font-weight: 750;
    }}
    QLabel#dialogTitle {{
        font-size: 22px;
        font-weight: 750;
    }}
    QLabel#subtitle, QLabel#muted, QLabel#pathHint {{
        color: {colors["muted"]};
    }}
    QLabel#metric {{
        font-size: 22px;
        font-weight: 750;
    }}
    QLabel#metricLabel {{
        color: {colors["muted"]};
        font-size: 11px;
    }}
    QLabel#safeNotice {{
        background: rgba(65, 211, 154, 0.12);
        color: {colors["positive"]};
        border: 1px solid rgba(65, 211, 154, 0.35);
        border-radius: 8px;
        padding: 8px 12px;
        font-weight: 600;
    }}
    QLineEdit, QComboBox {{
        background: {colors["surface_2"]};
        border: 1px solid {colors["border"]};
        border-radius: 8px;
        padding: 8px 10px;
        min-height: 20px;
        selection-background-color: {colors["accent"]};
    }}
    QLineEdit:focus, QComboBox:focus {{
        border-color: {colors["accent"]};
    }}
    QCheckBox {{
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 17px;
        height: 17px;
        border: 1px solid {colors["border"]};
        border-radius: 5px;
        background: {colors["surface_2"]};
    }}
    QCheckBox::indicator:checked {{
        background: {colors["accent"]};
        border-color: {colors["accent"]};
    }}
    QPushButton {{
        border: 0;
        border-radius: 8px;
        padding: 9px 14px;
        background: {colors["surface_2"]};
        font-weight: 650;
    }}
    QPushButton:hover {{
        background: {colors["border"]};
    }}
    QPushButton#primary {{
        background: {colors["accent"]};
        color: #07101d;
    }}
    QPushButton#primary:hover {{
        background: {colors["accent_hover"]};
    }}
    QPushButton#primary:disabled {{
        background: {colors["border"]};
        color: {colors["muted"]};
    }}
    QPushButton#filter {{
        color: {colors["muted"]};
        padding: 7px 11px;
    }}
    QPushButton#filter[active="true"] {{
        color: {colors["text"]};
        background: {colors["surface_2"]};
    }}
    QTableWidget {{
        background: {colors["surface"]};
        alternate-background-color: {colors["surface_2"]};
        border: 1px solid {colors["border"]};
        border-radius: 12px;
        gridline-color: transparent;
        selection-background-color: rgba(43, 199, 242, 0.16);
        outline: none;
    }}
    QHeaderView::section {{
        background: {colors["surface"]};
        color: {colors["muted"]};
        border: 0;
        border-bottom: 1px solid {colors["border"]};
        /* This visible divider also marks the draggable column resize handle. */
        border-right: 1px solid {colors["header_divider"]};
        padding: 10px 8px;
        font-size: 11px;
        font-weight: 700;
    }}
    QTableWidget::item {{
        border-bottom: 1px solid {colors["border"]};
        padding: 7px;
    }}
    QStatusBar {{
        background: {colors["surface"]};
        color: {colors["muted"]};
        border-top: 1px solid {colors["border"]};
    }}
    """
