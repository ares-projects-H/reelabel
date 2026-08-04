# PyInstaller specification shared by Windows, macOS, and Linux builds.

from __future__ import annotations

import sys
import runpy
from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).parent
VERSION = runpy.run_path(PROJECT_ROOT / "src" / "reelabel" / "_version.py")[
    "__version__"
]
ASSETS = PROJECT_ROOT / "assets"

if sys.platform == "darwin":
    APP_ICON = ASSETS / "reelabel-icon.icns"
elif sys.platform == "win32":
    APP_ICON = ASSETS / "reelabel-icon.ico"
else:
    APP_ICON = ASSETS / "reelabel-icon.png"

a = Analysis(
    [str(PROJECT_ROOT / "packaging" / "entrypoint.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=[
        (str(ASSETS / "reelabel-icon.png"), "assets"),
        # Ship the complete MIT text with every packaged application.
        (str(PROJECT_ROOT / "LICENSE"), "."),
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
    name="Reelabel",
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
    name="Reelabel",
)

if sys.platform == "darwin":
    app = BUNDLE(
        collection,
        name="Reelabel.app",
        icon=str(APP_ICON),
        bundle_identifier="com.aresprojectsh.reelabel",
        info_plist={
            "CFBundleDisplayName": "Reelabel",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "LSMinimumSystemVersion": "11.0",
            "NSHighResolutionCapable": True,
        },
    )
