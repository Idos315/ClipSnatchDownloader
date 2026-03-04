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
  cp "$FFMPEG_PATH" resources/ffmpeg
  chmod +x resources/ffmpeg
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
  echo "   To add one: put icon.icns in the assets/ folder and re-run."
fi

echo "▶ Writing PyInstaller spec…"
ICON_LINE="icon=None,"
if [ -n "$ICON_ARG" ]; then
  ICON_LINE="icon=\"$ICON_ARG\","
fi

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
    icon="$ICON_ARG",
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

echo "▶ Copying to Desktop…"
rm -rf ~/Desktop/ClipSnatch.app
cp -R dist/ClipSnatch.app ~/Desktop/ClipSnatch.app

rm -f _build.spec
rm -rf build dist __pycache__

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅  ClipSnatch.app is on your Desktop!              ║"
echo "║  Double-click to launch. Drag to Applications too.  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
