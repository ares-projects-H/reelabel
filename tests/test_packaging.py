"""Checks that release metadata and native application assets stay aligned."""

from __future__ import annotations

from pathlib import Path

import tomllib

import reelabel

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_public_version_is_consistent() -> None:
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == "0.1.0"
    assert project["project"]["name"] == "reelabel"
    assert project["project"]["license"] == "MIT"
    assert "reelabel" in project["project"]["scripts"]
    assert "reelabel-gui" in project["project"]["scripts"]
    assert reelabel.__version__ == "0.1.0"
    assert '#define MyAppVersion "0.1.0"' in (
        PROJECT_ROOT / "packaging" / "windows" / "Reelabel.iss"
    ).read_text(encoding="utf-8")


def test_native_icons_have_expected_headers() -> None:
    windows_icon = (PROJECT_ROOT / "assets" / "reelabel-icon.ico").read_bytes()
    macos_icon = (PROJECT_ROOT / "assets" / "reelabel-icon.icns").read_bytes()
    assert windows_icon[:4] == b"\x00\x00\x01\x00"
    assert macos_icon[:4] == b"icns"


def test_macos_dmg_requires_dragging_to_applications() -> None:
    build_script = (PROJECT_ROOT / "packaging" / "macos" / "build_dmg.sh").read_text(
        encoding="utf-8"
    )
    for expected in (
        "command -v create-dmg",
        '--icon "Reelabel.app" 170 190',
        "--app-drop-link 490 190",
        '--volicon "$PROJECT_ROOT/assets/reelabel-icon.icns"',
    ):
        assert expected in build_script


def test_release_workflow_covers_every_public_package() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    for expected in (
        "Windows 10/11 x64 EXE",
        "macOS ${{ matrix.architecture }} DMG",
        "Linux x86_64 AppImage and DEB",
        "SHA-256 checksums",
        "Read version from pyproject.toml",
        'test "$GITHUB_REF_NAME" = "v${{ steps.project.outputs.version }}"',
        "Reelabel-${{ env.VERSION }}-Windows-x64-Setup.exe",
        "Reelabel-${{ env.VERSION }}-macOS-${{ matrix.architecture }}.dmg",
        "Reelabel-${{ env.VERSION }}-Linux-x86_64.AppImage",
        "Reelabel-${{ env.VERSION }}-Ubuntu-24.04-x86_64.deb",
        '"/DMyAppVersion=$env:VERSION"',
        "REELABEL_SMOKE_TEST_SETTINGS",
        "QT_QPA_PLATFORM=offscreen /usr/bin/reelabel",
        "brew install create-dmg",
    ):
        assert expected in workflow


def test_ubuntu_package_contains_desktop_integration_and_license() -> None:
    build_script = (PROJECT_ROOT / "packaging" / "linux" / "build_deb.sh").read_text(
        encoding="utf-8"
    )
    for expected in (
        "/opt/reelabel/Reelabel",
        "/usr/bin/reelabel",
        "/usr/share/applications/reelabel.desktop",
        "/usr/share/icons/hicolor/256x256/apps/reelabel.png",
        "/usr/share/doc/reelabel/copyright",
    ):
        assert expected in build_script


def test_bundled_codex_skill_uses_the_same_engine_and_public_api() -> None:
    bundled = PROJECT_ROOT / "reelabel-skill" / "reelabel"
    assert (bundled / "scripts" / "reelabel" / "core.py").read_bytes() == (
        PROJECT_ROOT / "src" / "reelabel" / "core.py"
    ).read_bytes()
    assert (bundled / "scripts" / "reelabel" / "api.py").read_bytes() == (
        PROJECT_ROOT / "src" / "reelabel" / "api.py"
    ).read_bytes()
    instructions = (bundled / "SKILL.md").read_text(encoding="utf-8")
    assert '--undo-scope "<original-media-folder>"' in instructions
