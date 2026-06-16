#!/usr/bin/env bash
# Build MarkItDown GUI for macOS using flet pack.
# Produces dist/MarkItDown.app

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

if [ ! -f "assets/icon.icns" ]; then
    echo "[ERROR] assets/icon.icns not found. Create one with iconutil before building."
    echo "        Hint: prepare assets/AppIcon.iconset, then: iconutil -c icns assets/AppIcon.iconset -o assets/icon.icns"
    exit 1
fi

echo "[build] Cleaning previous build artifacts..."
rm -rf build dist

echo "[build] Running flet pack..."
flet pack \
  --name "MarkItDown" \
  --product-name "MarkItDown" \
  --product-version "0.1.0" \
  --file-description "Convert files to Markdown" \
  --copyright "MIT License" \
  --icon "assets/icon.icns" \
  --add-data "assets:assets" \
  --hidden-import "magika" \
  --hidden-import "magika._config" \
  src/markitdown_gui/__main__.py

echo
echo "[build] Done. Open dist/MarkItDown.app to test, or copy to /Applications."
