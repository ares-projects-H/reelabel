"""Generate native application icons from the editable high-resolution PNG."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT_ROOT / "assets" / "media-renamer-icon.png"
WINDOWS_ICON = PROJECT_ROOT / "assets" / "media-renamer-icon.ico"
MACOS_ICON = PROJECT_ROOT / "assets" / "media-renamer-icon.icns"


def _square_source() -> Image.Image:
    """Return the source icon as a square RGBA image."""

    image = Image.open(SOURCE).convert("RGBA")
    if image.width != image.height:
        raise ValueError("The source icon must be square.")
    return image


def _build_windows_icon(image: Image.Image) -> None:
    """Write a multi-resolution ICO used by the EXE and Windows installer."""

    image.save(
        WINDOWS_ICON,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


def _build_macos_icon(image: Image.Image) -> None:
    """Write a multi-resolution ICNS used by the macOS application bundle."""

    image.save(
        MACOS_ICON,
        format="ICNS",
        sizes=[
            (16, 16),
            (32, 32),
            (64, 64),
            (128, 128),
            (256, 256),
            (512, 512),
            (1024, 1024),
        ],
    )


def main() -> int:
    """Generate every platform icon and print their locations."""

    image = _square_source()
    _build_windows_icon(image)
    _build_macos_icon(image)
    print(WINDOWS_ICON)
    print(MACOS_ICON)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
