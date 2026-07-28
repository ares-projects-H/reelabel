#!/bin/sh
# Assemble the PyInstaller directory into an x86_64 AppImage.

set -eu

VERSION="${1:-0.1.0}"
APPIMAGETOOL="${2:-appimagetool-x86_64.AppImage}"
PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
APPDIR="$PROJECT_ROOT/build/Reelabel.AppDir"
OUTPUT_DIR="$PROJECT_ROOT/release"
OUTPUT="$OUTPUT_DIR/Reelabel-$VERSION-Linux-x86_64.AppImage"

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$OUTPUT_DIR"
cp -R "$PROJECT_ROOT/dist/Reelabel/." "$APPDIR/usr/bin/"
ln -s "Reelabel" "$APPDIR/usr/bin/reelabel"
cp "$PROJECT_ROOT/packaging/linux/AppRun" "$APPDIR/AppRun"
cp "$PROJECT_ROOT/packaging/linux/reelabel.desktop" "$APPDIR/reelabel.desktop"
cp "$PROJECT_ROOT/assets/reelabel-icon.png" "$APPDIR/reelabel.png"
chmod +x "$APPDIR/AppRun"
ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$OUTPUT"
chmod +x "$OUTPUT"

echo "$OUTPUT"
