# PyInstaller specification shared by Windows, macOS, and Linux builds.

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).parent
PROJECT_DATA = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
VERSION = PROJECT_DATA["project"]["version"]
ASSETS = PROJECT_ROOT / "assets"

if sys.platform == "darwin":
    APP_ICON = ASSETS / "media-renamer-icon.icns"
elif sys.platform == "win32":
    APP_ICON = ASSETS / "media-renamer-icon.ico"
else:
    APP_ICON = ASSETS / "media-renamer-icon.png"

a = Analysis(
    [str(PROJECT_ROOT / "packaging" / "entrypoint.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=[
        (str(ASSETS / "media-renamer-icon.png"), "assets"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Media Renamer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(APP_ICON),
)

collection = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Media Renamer",
)

if sys.platform == "darwin":
    app = BUNDLE(
        collection,
        name="Media Renamer.app",
        icon=str(APP_ICON),
        bundle_identifier="com.aresprojectsh.mediarenamer",
        info_plist={
            "CFBundleDisplayName": "Media Renamer",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "LSMinimumSystemVersion": "11.0",
            "NSHighResolutionCapable": True,
        },
    )
