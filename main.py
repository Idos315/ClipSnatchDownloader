"""
main.py - ClipSnatch entry point
"""
import logging
import sys
import os

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

# ── PySide6 / Qt environment ───────────────────────────────────────────────────
# Silence Qt internal warnings on macOS
os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-logging")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from ui import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ClipSnatch")
    app.setOrganizationName("ClipSnatch")
    app.setApplicationDisplayName("ClipSnatch")

    # App icon (if bundled)
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
