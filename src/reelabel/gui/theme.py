"""System-aware appearance without remote fonts or persistent palette overrides."""

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from .styles import stylesheet


class ThemeController(QObject):
    """Own application-wide popup styling and react to OS appearance changes."""

    changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.appearance = "system"
        self.dark = False
        app = QApplication.instance()
        self._fallback_dark = app.palette().window().color().lightness() < 145
        app.setStyle("Fusion")
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
        available = set(QFontDatabase.families())
        if font.family() not in available:
            for family in (
                ".AppleSystemUIFont",
                "Segoe UI",
                "Noto Sans",
                "Ubuntu",
                "DejaVu Sans",
                "Arial",
            ):
                if family in available:
                    font = QFont(family)
                    break
        app.setFont(font)
        app.styleHints().colorSchemeChanged.connect(self._system_changed)

    def system_is_dark(self) -> bool:
        scheme = QApplication.instance().styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Unknown:
            return self._fallback_dark
        return scheme == Qt.ColorScheme.Dark

    def set_appearance(self, appearance: str) -> None:
        if appearance not in {"system", "light", "dark"}:
            raise ValueError("Unknown appearance preference")
        self.appearance = appearance
        self.dark = self.system_is_dark() if appearance == "system" else appearance == "dark"
        QApplication.instance().setStyleSheet(stylesheet(self.dark))
        self.changed.emit(self.dark)

    def _system_changed(self, scheme) -> None:
        if self.appearance == "system":
            self.set_appearance("system")
