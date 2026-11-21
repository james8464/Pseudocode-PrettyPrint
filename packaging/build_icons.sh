#!/bin/bash
# Regenerate the macOS .icns and Windows .ico from the Swift-drawn PNG.
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p packaging/icons
swift packaging/make_icon.swift packaging/icons/app-1024.png

iconset="build/app.iconset"
rm -rf "$iconset"
mkdir -p "$iconset"
for size in 16 32 128 256 512; do
    sips -z "$size" "$size" packaging/icons/app-1024.png \
        --out "$iconset/icon_${size}x${size}.png" >/dev/null
    double=$((size * 2))
    sips -z "$double" "$double" packaging/icons/app-1024.png \
        --out "$iconset/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$iconset" -o packaging/icons/app.icns
rm -rf "$iconset"

sips -z 256 256 packaging/icons/app-1024.png --out packaging/icons/app-256.png >/dev/null
sips -s format ico packaging/icons/app-256.png \
    --out packaging/icons/app.ico >/dev/null
rm -f packaging/icons/app-256.png

echo "Wrote packaging/icons/app.icns and packaging/icons/app.ico"
