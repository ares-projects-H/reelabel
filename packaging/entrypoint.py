"""PyInstaller entry point for the graphical application."""

from __future__ import annotations

from media_renamer.gui.app import main

if __name__ == "__main__":
    raise SystemExit(main())
