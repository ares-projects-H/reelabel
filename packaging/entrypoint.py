"""PyInstaller entry point for the graphical application."""

from __future__ import annotations

from reelabel.gui.app import main

if __name__ == "__main__":
    raise SystemExit(main())
