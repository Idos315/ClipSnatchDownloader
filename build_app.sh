#!/bin/bash
# ============================================================
#  ClipSnatch — build_app.sh
#  Run from inside the clipsnatch folder:  bash build_app.sh
# ============================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   ClipSnatch  —  App Builder         ║"
echo "╚══════════════════════════════════════╝"
echo ""

if [ ! -f ".venv/bin/python" ]; then
  echo "▶ Creating virtual environment…"
  python3 -m venv .venv
fi

source .venv/bin/activate
echo "▶ Installing dependencies…"
pip install --upgrade pip --quiet
pip install PySide6 yt-dlp pyinstaller --quiet

# Install create-dmg if not present
if ! command -v create-dmg &>/dev/null; then
  echo "▶ Installing create-dmg…"
  brew install create-dmg
fi

echo "▶ Downloading yt-dlp binary…"
mkdir -p resources
curl -L --progress-bar \
  "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos" \
  -o resources/yt-dlp
chmod +x resources/yt-dlp
xattr -d com.apple.quarantine resources/yt-dlp 2>/dev/null || true

FFMPEG_PATH=$(command -v ffmpeg 2>/dev/null || true)
if [ -n "$FFMPEG_PATH" ]; then
  echo "▶ Bundling ffmpeg…"
  sudo cp "$FFMPEG_PATH" resources/ffmpeg
  sudo chmod 755 resources/ffmpeg
  xattr -d com.apple.quarantine resources/ffmpeg 2>/dev/null || true
else
  echo "⚠  ffmpeg not found. Install with: brew install ffmpeg"
fi

# Detect icon
ICON_ARG=""
if [ -f "assets/icon.icns" ]; then
  ICON_ARG="assets/icon.icns"
  echo "✅ Found icon: assets/icon.icns"
elif [ -f "assets/icon.png" ]; then
  ICON_ARG="assets/icon.png"
  echo "✅ Found icon: assets/icon.png"
else
  echo "ℹ  No icon found in assets/ — using default."
fi

ICON_LINE="icon=None,"
BUNDLE_ICON=""
if [ -n "$ICON_ARG" ]; then
  ICON_LINE="icon=\"$ICON_ARG\","
  BUNDLE_ICON="icon=\"$ICON_ARG\","
fi

echo "▶ Writing PyInstaller spec…"
cat > _build.spec << SPEC
import os
from pathlib import Path
block_cipher = None
datas = []
for name in ["yt-dlp", "ffmpeg", "ffprobe"]:
    p = Path("resources") / name
    if p.exists():
        datas.append((str(p), "resources"))
a = Analysis(
    ["main.py"], pathex=["."], binaries=[], datas=datas,
    hiddenimports=["PySide6.QtCore","PySide6.QtGui","PySide6.QtWidgets"],
    hookspath=[], runtime_hooks=[],
    excludes=["tkinter","matplotlib","numpy"], cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
    name="ClipSnatch", debug=False, strip=False, upx=False,
    console=False, argv_emulation=True, $ICON_LINE)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False, name="ClipSnatch")
app = BUNDLE(coll, name="ClipSnatch.app",
    bundle_identifier="com.clipsnatch.app", version="1.0.0",
    $BUNDLE_ICON
    info_plist={
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
        "LSMinimumSystemVersion": "11.0",
        "CFBundleShortVersionString": "1.0.0",
    })
SPEC

echo "▶ Building ClipSnatch.app…"
pyinstaller --clean --noconfirm _build.spec

xattr -rd com.apple.quarantine dist/ClipSnatch.app 2>/dev/null || true

# ── Build DMG ──────────────────────────────────────────────
echo "▶ Creating DMG installer…"
rm -f dist/ClipSnatch.dmg

DMG_ARGS=(
  --volname "ClipSnatch"
  --window-pos 200 120
  --window-size 600 400
  --icon-size 128
  --icon "ClipSnatch.app" 150 200
  --hide-extension "ClipSnatch.app"
  --app-drop-link 450 200
)

if [ -n "$ICON_ARG" ]; then
  DMG_ARGS+=(--volicon "$ICON_ARG")
fi

create-dmg "${DMG_ARGS[@]}" dist/ClipSnatch.dmg dist/ClipSnatch.app

xattr -rd com.apple.quarantine dist/ClipSnatch.dmg 2>/dev/null || true

# Copy both to Desktop
echo "▶ Copying to Desktop…"
rm -rf ~/Desktop/ClipSnatch.app
rm -f ~/Desktop/ClipSnatch.dmg
cp -R dist/ClipSnatch.app ~/Desktop/ClipSnatch.app
cp dist/ClipSnatch.dmg ~/Desktop/ClipSnatch.dmg

rm -f _build.spec
rm -rf build __pycache__

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅  Done!                                               ║"
echo "║                                                          ║"
echo "║  ClipSnatch.app  — double-click to run directly         ║"
echo "║  ClipSnatch.dmg  — share this with others               ║"
echo "║                                                          ║"
echo "║  Both are on your Desktop.                              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
