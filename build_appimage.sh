#!/usr/bin/env bash
#
# Build a portable Beer AppImage (V1.2).
#
# Usage:
#   bash build_appimage.sh                 # build dist/Beer-V1.2-x86_64.AppImage
#   VERSION=1.2 ARCH=x86_64 bash build_appimage.sh
#   APPIMAGE_EXTRACT_AND_RUN=1 bash build_appimage.sh   # systems without FUSE
#
set -euo pipefail

cd "$(dirname "$0")"

VERSION="${VERSION:-1.2}"
ARCH="${ARCH:-x86_64}"
OUTPUT="dist/Beer-V${VERSION}-${ARCH}.AppImage"
APPDIR="build/AppDir"
TOOLS_DIR="tools"

echo "==> Building Beer V${VERSION} for ${ARCH}"

if [[ ! -x dist/Beer ]]; then
    echo "==> Running PyInstaller build"
    python3 build.py
fi

if [[ ! -x dist/Beer ]]; then
    echo "ERROR: dist/Beer was not created." >&2
    exit 1
fi

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" \
         "$APPDIR/usr/share/icons/hicolor/256x256/apps"

install -m 755 dist/Beer "$APPDIR/usr/bin/Beer"
install -m 755 packaging/AppRun "$APPDIR/AppRun"
install -m 644 packaging/beer.desktop "$APPDIR/usr/share/applications/beer.desktop"

# Prefer the emoji icon rendered by the application itself.  When Qt cannot
# run in this environment, fall back to the bundled SVG beer mug.
ICON_PATH=""
if QT_QPA_PLATFORM=offscreen python3 -c "
import sys
sys.path.insert(0, '.')
from PyQt6.QtWidgets import QApplication
app = QApplication([])
from core.app_icon import get_icon_path
path = get_icon_path(256)
print(path)
" >/tmp/beer_icon_path 2>/dev/null; then
    ICON_PATH="$(cat /tmp/beer_icon_path)"
fi
rm -f /tmp/beer_icon_path

if [[ -n "$ICON_PATH" && -f "$ICON_PATH" ]]; then
    install -m 644 "$ICON_PATH" "$APPDIR/beer.png"
    install -m 644 "$ICON_PATH" "$APPDIR/usr/share/icons/hicolor/256x256/apps/beer.png"
    ln -sf beer.png "$APPDIR/.DirIcon"
    ICON_NAME="beer.png"
else
    install -m 644 assets/beer.svg "$APPDIR/beer.svg"
    install -m 644 assets/beer.svg "$APPDIR/usr/share/icons/hicolor/scalable/apps/beer.svg"
    ln -sf beer.svg "$APPDIR/.DirIcon"
    ICON_NAME="beer.svg"
fi

# AppImage tools expect the icon to be reachable at the AppDir root.
sed -i "s|Icon=beer$|Icon=${ICON_NAME%.*}|" "$APPDIR/usr/share/applications/beer.desktop" 2>/dev/null || true
cp "$APPDIR/usr/share/applications/beer.desktop" "$APPDIR/beer.desktop"

APPIMAGETOOL="${APPIMAGETOOL:-}"
if [[ -z "$APPIMAGETOOL" ]]; then
    if command -v appimagetool >/dev/null 2>&1; then
        APPIMAGETOOL="$(command -v appimagetool)"
    elif [[ -x "$TOOLS_DIR/appimagetool.AppImage" ]]; then
        APPIMAGETOOL="$TOOLS_DIR/appimagetool.AppImage"
    else
        echo "==> Downloading appimagetool"
        mkdir -p "$TOOLS_DIR"
        URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
        if ! curl -fL --retry 3 -o "$TOOLS_DIR/appimagetool.AppImage" "$URL"; then
            echo "ERROR: Could not download appimagetool. Install it manually or set APPIMAGETOOL." >&2
            exit 1
        fi
        chmod +x "$TOOLS_DIR/appimagetool.AppImage"
        APPIMAGETOOL="$TOOLS_DIR/appimagetool.AppImage"
    fi
fi

echo "==> Packaging AppImage"
mkdir -p dist
ARCH="$ARCH" "$APPIMAGETOOL" "$APPDIR" "$OUTPUT"

echo "==> Created: $OUTPUT"
ls -lh "$OUTPUT"
