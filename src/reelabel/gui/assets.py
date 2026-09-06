"""Bundled assets and scalable local-only interface icons."""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


def project_asset(name: str) -> Path:
    """Resolve assets independently of the working directory in source and frozen builds."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
    return root / "assets" / name


PATHS = {
    "folder": '<path d="M3 7h7l2 2h9v11H3z"/><path d="M3 7V4h7l2 3h8v2"/>',
    "edit": '<path d="m5 15 10-10 4 4L9 19H5zM13 7l4 4M4 22h16"/>',
    "history": '<path d="M4 8a9 9 0 1 1-1 7M4 3v5h5M12 7v6l4 2"/>',
    "settings": '<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="9" cy="6" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="8" cy="18" r="2"/>',
    "arrow": '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    "check": '<path d="m5 12 4 4L19 6"/>',
    "shield": '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z"/><path d="m8 12 3 3 5-6"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-11v1"/>',
    "search": '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
    "refresh": '<path d="M20 7a9 9 0 0 0-15-1L3 9m0-6v6h6M4 17a9 9 0 0 0 15 1l2-3m0 6v-6h-6"/>',
}


@lru_cache(maxsize=64)
def icon(name: str, color: str) -> QIcon:
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><g fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{PATHS[name]}</g></svg>'
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    QSvgRenderer(svg.encode()).render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)
