#!/bin/bash
# ============================================================
#  ClipSnatch Installer
#  Just run:  bash install.sh
# ============================================================

set -e
echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║        ClipSnatch Installer               ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# Check for Python 3.10+
PYTHON=$(command -v python3 || true)
if [ -z "$PYTHON" ]; then
  echo "❌ Python 3 not found."
  echo "   Download it from https://www.python.org/downloads/"
  exit 1
fi

PY_VER=$($PYTHON -c "import sys; print(sys.version_info.minor)")
if [ "$PY_VER" -lt 10 ]; then
  echo "❌ Python 3.10+ is required. You have 3.$PY_VER"
  echo "   Download a newer version from https://www.python.org/downloads/"
  exit 1
fi

echo "✅ Python 3.$PY_VER found."

# Fix SSL certificates (common macOS issue)
CERT_CMD="/Applications/Python 3.$PY_VER/Install Certificates.command"
if [ -f "$CERT_CMD" ]; then
  echo "▶ Fixing SSL certificates…"
  bash "$CERT_CMD" > /dev/null 2>&1 || true
fi

# Install Homebrew if missing
if ! command -v brew &>/dev/null; then
  echo "▶ Installing Homebrew (required for ffmpeg)…"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  # Add brew to path for Apple Silicon
  if [ -f "/opt/homebrew/bin/brew" ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi
fi

# Install ffmpeg
if ! command -v ffmpeg &>/dev/null; then
  echo "▶ Installing ffmpeg…"
  brew install ffmpeg
else
  echo "✅ ffmpeg found."
fi

# Create venv
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "▶ Setting up Python environment…"
$PYTHON -m venv .venv
source .venv/bin/activate
pip install --upgrade pip --quiet
pip install PySide6 yt-dlp pyinstaller --quiet

# Download yt-dlp binary for bundling
echo "▶ Downloading yt-dlp binary…"
mkdir -p resources
curl -L --progress-bar \
  "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos" \
  -o resources/yt-dlp
chmod +x resources/yt-dlp
xattr -d com.apple.quarantine resources/yt-dlp 2>/dev/null || true

# Bundle ffmpeg
FFMPEG_PATH=$(command -v ffmpeg 2>/dev/null || true)
if [ -n "$FFMPEG_PATH" ]; then
  cp "$FFMPEG_PATH" resources/ffmpeg
  chmod +x resources/ffmpeg
  xattr -d com.apple.quarantine resources/ffmpeg 2>/dev/null || true
fi

# Write spec
cat > _build.spec << 'SPEC'
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
    console=False, argv_emulation=True)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False, name="ClipSnatch")
app = BUNDLE(coll, name="ClipSnatch.app",
    bundle_identifier="com.clipsnatch.app", version="1.0.0",
    info_plist={
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
        "LSMinimumSystemVersion": "11.0",
        "CFBundleShortVersionString": "1.0.0",
    })
SPEC

# Build
echo "▶ Building ClipSnatch.app (2–4 minutes)…"
pyinstaller --clean --noconfirm _build.spec

echo "▶ Removing quarantine flags…"
xattr -rd com.apple.quarantine dist/ClipSnatch.app 2>/dev/null || true

echo "▶ Copying to Desktop…"
rm -rf ~/Desktop/ClipSnatch.app
cp -R dist/ClipSnatch.app ~/Desktop/ClipSnatch.app

# Cleanup
rm -f _build.spec
rm -rf build dist __pycache__

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  ✅  Done!                                             ║"
echo "║                                                        ║"
echo "║  ClipSnatch.app is on your Desktop.                   ║"
echo "║  Double-click it any time to launch.                  ║"
echo "║  You can drag it to Applications too.                 ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
