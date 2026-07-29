#!/bin/sh
# Build an unsigned, drag-to-Applications DMG from the PyInstaller app bundle.

set -eu

VERSION="${1:-0.1.0}"
ARCHITECTURE="${2:-$(uname -m)}"
PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
STAGING_DIR="$PROJECT_ROOT/build/dmg-root"
OUTPUT_DIR="$PROJECT_ROOT/release"
OUTPUT="$OUTPUT_DIR/Reelabel-$VERSION-macOS-$ARCHITECTURE.dmg"

if ! command -v create-dmg >/dev/null 2>&1; then
    echo "create-dmg is required. Install it with: brew install create-dmg" >&2
    exit 1
fi

rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR" "$OUTPUT_DIR"
cp -R "$PROJECT_ROOT/dist/Reelabel.app" "$STAGING_DIR/"
rm -f "$OUTPUT"

# The arranged icons make installation explicit: drag Reelabel onto the
# Applications folder, wait for the copy, then eject the disk image.
create-dmg \
    --volname "Reelabel" \
    --volicon "$PROJECT_ROOT/assets/reelabel-icon.icns" \
    --window-pos 200 120 \
    --window-size 660 400 \
    --text-size 14 \
    --icon-size 128 \
    --icon "Reelabel.app" 170 190 \
    --hide-extension "Reelabel.app" \
    --app-drop-link 490 190 \
    --format UDZO \
    "$OUTPUT" \
    "$STAGING_DIR"

echo "$OUTPUT"
