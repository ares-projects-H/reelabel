#!/bin/sh
# Build an unsigned DMG from the PyInstaller application bundle.

set -eu

VERSION="${1:-0.1.0}"
ARCHITECTURE="${2:-$(uname -m)}"
PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
STAGING_DIR="$PROJECT_ROOT/build/dmg-root"
OUTPUT_DIR="$PROJECT_ROOT/release"
OUTPUT="$OUTPUT_DIR/Media-Renamer-$VERSION-macOS-$ARCHITECTURE.dmg"

rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR" "$OUTPUT_DIR"
cp -R "$PROJECT_ROOT/dist/Media Renamer.app" "$STAGING_DIR/"
ln -s /Applications "$STAGING_DIR/Applications"
hdiutil create \
    -volname "Media Renamer" \
    -srcfolder "$STAGING_DIR" \
    -ov \
    -format UDZO \
    "$OUTPUT"

echo "$OUTPUT"
