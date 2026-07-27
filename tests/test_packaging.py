"""Checks that release metadata and native application assets stay aligned."""

from __future__ import annotations

from pathlib import Path

import tomllib

import media_renamer

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_public_version_is_consistent() -> None:
    project = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert project["project"]["version"] == "0.1.0"
    assert media_renamer.__version__ == "0.1.0"
    assert '#define MyAppVersion "0.1.0"' in (
        PROJECT_ROOT / "packaging" / "windows" / "MediaRenamer.iss"
    ).read_text(encoding="utf-8")


def test_native_icons_have_expected_headers() -> None:
    windows_icon = (
        PROJECT_ROOT / "assets" / "media-renamer-icon.ico"
    ).read_bytes()
    macos_icon = (
        PROJECT_ROOT / "assets" / "media-renamer-icon.icns"
    ).read_bytes()
    assert windows_icon[:4] == b"\x00\x00\x01\x00"
    assert macos_icon[:4] == b"icns"


def test_release_workflow_covers_every_public_package() -> None:
    workflow = (
        PROJECT_ROOT / ".github" / "workflows" / "release.yml"
    ).read_text(encoding="utf-8")
    for expected in (
        "Windows 10/11 x64 EXE",
        "macOS ${{ matrix.architecture }} DMG",
        "Linux x86_64 AppImage",
        "SHA-256 checksums",
    ):
        assert expected in workflow
