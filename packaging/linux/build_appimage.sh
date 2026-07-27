#!/bin/sh
# Assemble the PyInstaller directory into an x86_64 AppImage.

set -eu

VERSION="${1:-0.1.0}"
APPIMAGETOOL="${2:-appimagetool-x86_64.AppImage}"
PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
APPDIR="$PROJECT_ROOT/build/MediaRenamer.AppDir"
OUTPUT_DIR="$PROJECT_ROOT/release"
OUTPUT="$OUTPUT_DIR/Media-Renamer-$VERSION-Linux-x86_64.AppImage"

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$OUTPUT_DIR"
cp -R "$PROJECT_ROOT/dist/Media Renamer/." "$APPDIR/usr/bin/"
ln -s "Media Renamer" "$APPDIR/usr/bin/media-renamer"
cp "$PROJECT_ROOT/packaging/linux/AppRun" "$APPDIR/AppRun"
cp "$PROJECT_ROOT/packaging/linux/media-renamer.desktop" "$APPDIR/media-renamer.desktop"
cp "$PROJECT_ROOT/assets/media-renamer-icon.png" "$APPDIR/media-renamer.png"
chmod +x "$APPDIR/AppRun"
ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$OUTPUT"
chmod +x "$OUTPUT"

echo "$OUTPUT"
