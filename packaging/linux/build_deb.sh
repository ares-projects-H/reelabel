#!/bin/sh
# Build an Ubuntu 24.04 x86_64 package from the PyInstaller directory.

set -eu

VERSION="${1:-0.1.0}"
PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
PACKAGE_ROOT="$PROJECT_ROOT/build/reelabel-deb"
OUTPUT_DIR="$PROJECT_ROOT/release"
OUTPUT="$OUTPUT_DIR/Reelabel-$VERSION-Ubuntu-24.04-x86_64.deb"

rm -rf "$PACKAGE_ROOT"
mkdir -p \
  "$PACKAGE_ROOT/DEBIAN" \
  "$PACKAGE_ROOT/opt/reelabel" \
  "$PACKAGE_ROOT/usr/bin" \
  "$PACKAGE_ROOT/usr/share/applications" \
  "$PACKAGE_ROOT/usr/share/doc/reelabel" \
  "$PACKAGE_ROOT/usr/share/icons/hicolor/256x256/apps" \
  "$OUTPUT_DIR"

cp -R "$PROJECT_ROOT/dist/Reelabel/." "$PACKAGE_ROOT/opt/reelabel/"
ln -s "/opt/reelabel/Reelabel" "$PACKAGE_ROOT/usr/bin/reelabel"
cp \
  "$PROJECT_ROOT/packaging/linux/reelabel.desktop" \
  "$PACKAGE_ROOT/usr/share/applications/reelabel.desktop"
cp \
  "$PROJECT_ROOT/assets/reelabel-icon.png" \
  "$PACKAGE_ROOT/usr/share/icons/hicolor/256x256/apps/reelabel.png"
cp "$PROJECT_ROOT/LICENSE" "$PACKAGE_ROOT/usr/share/doc/reelabel/copyright"
sed "s/@VERSION@/$VERSION/g" \
  "$PROJECT_ROOT/packaging/linux/debian/control.in" \
  > "$PACKAGE_ROOT/DEBIAN/control"

chmod 0755 "$PACKAGE_ROOT/DEBIAN" "$PACKAGE_ROOT/opt/reelabel/Reelabel"
chmod 0644 \
  "$PACKAGE_ROOT/DEBIAN/control" \
  "$PACKAGE_ROOT/usr/share/applications/reelabel.desktop" \
  "$PACKAGE_ROOT/usr/share/doc/reelabel/copyright" \
  "$PACKAGE_ROOT/usr/share/icons/hicolor/256x256/apps/reelabel.png"

dpkg-deb --build --root-owner-group "$PACKAGE_ROOT" "$OUTPUT"

echo "$OUTPUT"
