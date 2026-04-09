#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p dist_release

TAR="dist_release/TalkieType-linux.tar.gz"
rm -f "$TAR"
tar -czf "$TAR" -C dist TalkieType

APPIMAGETOOL_BIN="appimagetool"
if ! command -v appimagetool >/dev/null 2>&1; then
  mkdir -p build
  if command -v curl >/dev/null 2>&1; then
    curl -L -o build/appimagetool https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage || true
  elif command -v wget >/dev/null 2>&1; then
    wget -O build/appimagetool https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage || true
  fi
  if [ -f build/appimagetool ]; then
    chmod +x build/appimagetool
    APPIMAGETOOL_BIN="./build/appimagetool"
  fi
fi

if command -v "$APPIMAGETOOL_BIN" >/dev/null 2>&1 || [ -x "$APPIMAGETOOL_BIN" ]; then
  APPDIR="build/AppDir"
  rm -rf "$APPDIR"
  mkdir -p "$APPDIR/usr/bin"
  cp -r dist/TalkieType/* "$APPDIR/usr/bin/"

  mkdir -p "$APPDIR/usr/share/applications"
  cat > "$APPDIR/usr/share/applications/TalkieType.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Talkie Type
Exec=TalkieType
Icon=TalkieType
Categories=Utility;
EOF

  mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
  python - <<'PY'
from PIL import Image, ImageDraw
size = 256
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.rounded_rectangle((16, 16, size - 16, size - 16), radius=48, fill=(18, 18, 18, 255))
draw.ellipse((88, 48, 168, 128), fill=(120, 200, 255, 255))
draw.rounded_rectangle((112, 128, 144, 192), radius=12, fill=(240, 240, 240, 255))
draw.rounded_rectangle((72, 112, 184, 208), radius=48, outline=(240, 240, 240, 255), width=12)
draw.rectangle((120, 200, 136, 228), fill=(240, 240, 240, 255))
img.save("build/AppDir/usr/share/icons/hicolor/256x256/apps/TalkieType.png")
PY
  ln -sf "usr/share/icons/hicolor/256x256/apps/TalkieType.png" "$APPDIR/TalkieType.png"
  ln -sf "usr/share/applications/TalkieType.desktop" "$APPDIR/TalkieType.desktop"
  "$APPIMAGETOOL_BIN" "$APPDIR" "dist_release/VoiceType-x86_64.AppImage" || true



if command -v dpkg-deb >/dev/null 2>&1; then
  PKG="build/deb"
  rm -rf "$PKG"
  mkdir -p "$PKG/DEBIAN" "$PKG/usr/bin"
  cp -r dist/TalkieType/* "$PKG/usr/bin/"
  cat > "$PKG/DEBIAN/control" <<'EOF'
Package: voicetype
Version: 0.1.0
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Talkie Type
Description: Talkie Type voice-to-text tray app
EOF
  dpkg-deb --build "$PKG" "dist_release/voicetype_0.1.0_amd64.deb" || true
fi
