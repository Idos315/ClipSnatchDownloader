"""
ui.py - PySide6 Qt UI for ClipSnatch
"""
import logging
import urllib.request
from pathlib import Path
from typing import Optional, List

from PySide6.QtCore import Qt, Signal, QObject, QRunnable, QThreadPool, Slot
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox, QFileDialog,
    QProgressBar, QTextEdit, QGroupBox, QFrame, QListWidget, QListWidgetItem,
    QStatusBar, QMessageBox, QScrollArea, QSizePolicy, QSpacerItem
)

from models import MediaEntry, PlaylistInfo, FormatInfo, OutputFormat, DownloadTask
from ytdlp_service import fetch_info, download, get_ytdlp_path, get_ffmpeg_path, SUPPORTED_BROWSERS
from ffmpeg_service import convert_to_mp3, convert_to_mp4

logger = logging.getLogger(__name__)

BG     = "#0f1117"
SURF   = "#1a1d27"
SURF2  = "#222536"
BORDER = "#2e3347"
ACCENT = "#5b6af0"
DARK   = "#4451c7"
TEXT   = "#e2e4ec"
MUTED  = "#6b7280"
ERR    = "#ef4444"

SS = f"""
* {{
    font-family: ".AppleSystemUIFont", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    color: {TEXT};
    box-sizing: border-box;
}}
QMainWindow, QWidget {{ background: {BG}; }}
QScrollArea {{ border: none; background: {BG}; }}
QScrollArea > QWidget > QWidget {{ background: {BG}; }}
QLabel {{ background: transparent; }}

QGroupBox {{
    background: {SURF};
    border: 1px solid {BORDER};
    border-radius: 10px;
    margin-top: 16px;
    padding: 16px 14px 12px 14px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px; top: -1px;
    padding: 0 5px;
    background: {SURF};
    color: {MUTED};
    font-size: 11px;
    font-weight: 600;
}}

QLineEdit {{
    background: {SURF2};
    border: 1.5px solid {BORDER};
    border-radius: 8px;
    padding: 9px 13px;
    color: {TEXT};
    font-size: 13px;
}}
QLineEdit:focus {{ border-color: {ACCENT}; background: #252840; }}

QPushButton {{
    background: {ACCENT};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 600;
    font-size: 13px;
    min-height: 36px;
}}
QPushButton:hover {{ background: {DARK}; }}
QPushButton:pressed {{ background: #3540a0; }}
QPushButton:disabled {{ background: {SURF2}; color: {MUTED}; }}

QPushButton#ghost {{
    background: {SURF2};
    border: 1.5px solid {BORDER};
    color: {TEXT};
    padding: 6px 12px;
    min-height: 32px;
}}
QPushButton#ghost:hover {{ background: {BORDER}; }}

QPushButton#big {{
    background: {ACCENT};
    font-size: 14px;
    font-weight: 700;
    min-height: 46px;
    border-radius: 10px;
    padding: 10px 20px;
}}
QPushButton#big:hover {{ background: {DARK}; }}
QPushButton#big:disabled {{ background: {SURF2}; color: {MUTED}; }}

QPushButton#danger {{
    background: {ERR};
    font-size: 14px;
    font-weight: 700;
    min-height: 46px;
    border-radius: 10px;
    padding: 10px 20px;
}}
QPushButton#danger:hover {{ background: #cc3333; }}

QComboBox {{
    background: {SURF2};
    border: 1.5px solid {BORDER};
    border-radius: 8px;
    padding: 7px 12px;
    color: {TEXT};
    min-height: 36px;
}}
QComboBox:hover {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {MUTED};
    margin-right: 10px;
}}
QComboBox QAbstractItemView {{
    background: {SURF2};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT};
    selection-background-color: {ACCENT};
    outline: none;
    padding: 3px;
}}

QCheckBox {{ color: {TEXT}; spacing: 7px; }}
QCheckBox::indicator {{
    width: 17px; height: 17px;
    border: 2px solid {BORDER};
    border-radius: 5px;
    background: {SURF2};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}

QProgressBar {{
    background: {SURF2};
    border: none;
    border-radius: 6px;
    min-height: 12px;
    max-height: 12px;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 6px;
}}

QTextEdit {{
    background: {SURF};
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: {MUTED};
    font-family: "Menlo", "Monaco", monospace;
    font-size: 11px;
    padding: 8px;
}}

QListWidget {{
    background: {SURF};
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: {TEXT};
    outline: none;
    padding: 3px;
}}
QListWidget::item {{ padding: 5px 8px; border-radius: 5px; }}
QListWidget::item:hover {{ background: {SURF2}; }}
QListWidget::item:selected {{ background: {SURF2}; }}

QScrollBar:vertical {{
    background: transparent; width: 8px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER}; min-height: 24px; border-radius: 4px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QStatusBar {{
    background: {SURF};
    border-top: 1px solid {BORDER};
    color: {MUTED};
    font-size: 12px;
    padding: 0 12px;
}}
"""

# ── Workers ───────────────────────────────────────────────────────────────────

class Sig(QObject):
    info_ready    = Signal(object)
    error         = Signal(str, str)
    progress      = Signal(float, str, str)
    status        = Signal(str)
    done          = Signal(str)
    conv_progress = Signal(float)


class FetchWorker(QRunnable):
    def __init__(self, url, use_cookies, browser, cookies_file):
        super().__init__()
        self.url, self.use_cookies = url, use_cookies
        self.browser, self.cookies_file = browser, cookies_file
        self.signals = Sig()

    @Slot()
    def run(self):
        try:
            result = fetch_info(
                self.url, use_cookies=self.use_cookies,
                browser=self.browser, cookies_file=self.cookies_file,
                on_progress=self.signals.status.emit,
            )
            self.signals.info_ready.emit(result)
        except PermissionError as e:
            self.signals.error.emit("auth", str(e))
        except Exception as e:
            self.signals.error.emit("general", str(e))


class DownloadWorker(QRunnable):
    def __init__(self, task):
        super().__init__()
        self.task = task
        self.signals = Sig()
        self._stop = False

    def stop(self): self._stop = True

    @Slot()
    def run(self):
        try:
            def on_prog(pct, speed, eta, _):
                self.signals.progress.emit(pct, speed, eta)

            out = download(self.task, on_progress=on_prog,
                           on_status=self.signals.status.emit,
                           stop_flag=lambda: self._stop)
            if self._stop: return

            if self.task.output_format == OutputFormat.MP3:
                self.signals.status.emit("Converting to MP3…")
                out = convert_to_mp3(
                    out, self.task.output_dir,
                    bitrate=self.task.audio_bitrate,
                    on_progress=lambda p, _: self.signals.conv_progress.emit(p),
                    stop_flag=lambda: self._stop)
            elif self.task.output_format == OutputFormat.MP4:
                if out:
                    self.signals.status.emit("Converting to MP4 (H.264)…")
                    out = convert_to_mp4(
                        out, self.task.output_dir,
                        on_progress=lambda p, _: self.signals.conv_progress.emit(p),
                        stop_flag=lambda: self._stop)
            self.signals.done.emit(out or "")
        except InterruptedError:
            self.signals.error.emit("cancelled", "Cancelled.")
        except Exception as e:
            logger.exception("Download error")
            self.signals.error.emit("general", str(e))


class ThumbWorker(QRunnable):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.signals = Sig()

    @Slot()
    def run(self):
        try:
            req = urllib.request.Request(self.url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = r.read()
            img = QImage()
            img.loadFromData(data)
            if not img.isNull():
                pix = QPixmap.fromImage(img).scaled(
                    200, 112,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
                self.signals.info_ready.emit(pix)
        except Exception:
            pass


# ── Playlist row ──────────────────────────────────────────────────────────────

class PlaylistRow(QWidget):
    def __init__(self, entry, idx):
        super().__init__()
        self.entry = entry
        row = QHBoxLayout(self)
        row.setContentsMargins(4, 2, 4, 2)
        row.setSpacing(8)
        self.cb = QCheckBox()
        self.cb.setChecked(True)
        row.addWidget(self.cb)
        lbl = QLabel(f"{idx}. {entry.title[:80]}")
        lbl.setStyleSheet(f"color: {TEXT}; font-size: 12px;")
        lbl.setWordWrap(False)
        row.addWidget(lbl, 1)
        if entry.duration:
            d = int(entry.duration)
            t = QLabel(f"{d//60}:{d%60:02d}")
            t.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
            row.addWidget(t)

    @property
    def is_selected(self): return self.cb.isChecked()


def cap(text, color=MUTED):
    """Small uppercase caption label."""
    l = QLabel(text)
    l.setStyleSheet(
        f"color: {color}; font-size: 11px; font-weight: 600; "
        f"letter-spacing: 0.3px; background: transparent;"
    )
    return l


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ClipSnatch")
        self.setMinimumSize(640, 600)
        self.resize(820, 820)

        self._entry: Optional[MediaEntry] = None
        self._playlist: Optional[PlaylistInfo] = None
        self._worker: Optional[DownloadWorker] = None
        self._pool = QThreadPool.globalInstance()
        self._pool.setMaxThreadCount(4)
        self._out_dir = str(Path.home() / "Downloads")
        self._cookies_file: Optional[str] = None
        self._batch: list = []
        self._batching = False
        self._playlist_rows: list = []

        self.setStyleSheet(SS)
        self._build()
        self._check_bins()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setCentralWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        root = QVBoxLayout(container)
        root.setContentsMargins(22, 22, 22, 22)
        root.setSpacing(12)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        logo = QLabel("⬇  ClipSnatch")
        logo.setStyleSheet(
            f"font-size: 22px; font-weight: 800; color: {TEXT}; letter-spacing: -0.4px;"
        )
        hdr.addWidget(logo)
        hdr.addStretch()
        powered = QLabel("powered by yt-dlp")
        powered.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        hdr.addWidget(powered)
        root.addLayout(hdr)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color: {BORDER}; background: {BORDER}; max-height: 1px; border: none;")
        root.addWidget(div)

        # ── URL box ─────────────────────────────────────────────────────────
        url_box = QGroupBox("URL")
        url_v = QVBoxLayout(url_box)
        url_v.setSpacing(0)

        url_row = QHBoxLayout()
        url_row.setSpacing(8)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(
            "Paste a YouTube, TikTok, Instagram or Facebook URL…"
        )
        self.url_input.setMinimumHeight(40)
        self.url_input.returnPressed.connect(self._fetch)
        url_row.addWidget(self.url_input, 1)

        paste_btn = QPushButton("Paste")
        paste_btn.setObjectName("ghost")
        paste_btn.setMinimumWidth(60)
        paste_btn.clicked.connect(
            lambda: self.url_input.setText(QApplication.clipboard().text())
        )
        url_row.addWidget(paste_btn)

        self.fetch_btn = QPushButton("Fetch Info")
        self.fetch_btn.setMinimumWidth(90)
        self.fetch_btn.clicked.connect(self._fetch)
        url_row.addWidget(self.fetch_btn)

        url_v.addLayout(url_row)
        root.addWidget(url_box)

        # ── Media info box ───────────────────────────────────────────────────
        self.info_box = QGroupBox("Media Info")
        info_v = QVBoxLayout(self.info_box)
        info_v.setSpacing(10)

        # Single item
        self._single = QWidget()
        sh = QHBoxLayout(self._single)
        sh.setContentsMargins(0, 0, 0, 0)
        sh.setSpacing(14)

        self.thumb = QLabel("No preview")
        self.thumb.setFixedSize(200, 112)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setStyleSheet(
            f"background: {SURF2}; border-radius: 8px; border: 1px solid {BORDER};"
            f"color: {MUTED}; font-size: 12px;"
        )
        sh.addWidget(self.thumb)

        meta = QVBoxLayout()
        meta.setSpacing(5)
        self.title_lbl = QLabel("—")
        self.title_lbl.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {TEXT};"
        )
        self.title_lbl.setWordWrap(True)
        meta.addWidget(self.title_lbl)
        self.dur_lbl = QLabel("")
        self.dur_lbl.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        meta.addWidget(self.dur_lbl)
        self.src_lbl = QLabel("")
        self.src_lbl.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        meta.addWidget(self.src_lbl)
        meta.addStretch()
        sh.addLayout(meta, 1)
        info_v.addWidget(self._single)

        # Playlist
        self._pl_widget = QWidget()
        pl_v = QVBoxLayout(self._pl_widget)
        pl_v.setContentsMargins(0, 0, 0, 0)
        pl_v.setSpacing(6)

        pl_hdr = QHBoxLayout()
        self.pl_title_lbl = QLabel("Playlist")
        self.pl_title_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {TEXT};"
        )
        pl_hdr.addWidget(self.pl_title_lbl, 1)
        for txt, val in [("All", True), ("None", False)]:
            b = QPushButton(txt)
            b.setObjectName("ghost")
            b.setMinimumWidth(48)
            b.clicked.connect(
                lambda _, v=val: [r.cb.setChecked(v) for r in self._playlist_rows]
            )
            pl_hdr.addWidget(b)
        pl_v.addLayout(pl_hdr)

        self.pl_list = QListWidget()
        self.pl_list.setMaximumHeight(130)
        pl_v.addWidget(self.pl_list)
        self._pl_widget.setVisible(False)
        info_v.addWidget(self._pl_widget)
        root.addWidget(self.info_box)

        # ── Download options ─────────────────────────────────────────────────
        opts_box = QGroupBox("Download Options")
        opts_v = QVBoxLayout(opts_box)
        opts_v.setSpacing(12)

        # Row: Format
        fmt_v = QVBoxLayout()
        fmt_v.setSpacing(4)
        fmt_v.addWidget(cap("FORMAT / QUALITY"))
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItem("Fetch a URL first", "")
        self.fmt_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        fmt_v.addWidget(self.fmt_combo)
        opts_v.addLayout(fmt_v)

        # Row: Save As + Bitrate side by side
        save_row = QHBoxLayout()
        save_row.setSpacing(12)

        out_v = QVBoxLayout()
        out_v.setSpacing(4)
        out_v.addWidget(cap("SAVE AS"))
        self.out_combo = QComboBox()
        for f in OutputFormat:
            self.out_combo.addItem(f.value.upper(), f)
        self.out_combo.currentIndexChanged.connect(self._on_out_changed)
        out_v.addWidget(self.out_combo)
        save_row.addLayout(out_v, 1)

        self._abr_v = QVBoxLayout()
        self._abr_v.setSpacing(4)
        self._abr_cap = cap("AUDIO BITRATE")
        self._abr_v.addWidget(self._abr_cap)
        self.abr_combo = QComboBox()
        for br in ["128k", "192k", "256k", "320k"]:
            self.abr_combo.addItem(br)
        self.abr_combo.setCurrentIndex(1)
        self._abr_v.addWidget(self.abr_combo)
        self._abr_wrapper = QWidget()
        self._abr_wrapper.setLayout(self._abr_v)
        self._abr_wrapper.setVisible(False)
        save_row.addWidget(self._abr_wrapper, 1)
        save_row.addStretch(2)

        opts_v.addLayout(save_row)

        # Row: Save folder
        folder_v = QVBoxLayout()
        folder_v.setSpacing(4)
        folder_v.addWidget(cap("SAVE TO FOLDER"))
        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)
        self.fld_lbl = QLabel(self._short(self._out_dir))
        self.fld_lbl.setStyleSheet(f"color: {TEXT}; font-size: 12px;")
        self.fld_lbl.setToolTip(self._out_dir)
        self.fld_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        folder_row.addWidget(self.fld_lbl, 1)
        browse = QPushButton("Browse…")
        browse.setObjectName("ghost")
        browse.setMinimumWidth(80)
        browse.clicked.connect(self._pick_folder)
        folder_row.addWidget(browse)
        folder_v.addLayout(folder_row)
        opts_v.addLayout(folder_v)

        root.addWidget(opts_box)

        # ── Auth box ─────────────────────────────────────────────────────────
        auth_box = QGroupBox("Authentication  (for Instagram / Facebook / private content)")
        auth_v = QVBoxLayout(auth_box)
        auth_v.setSpacing(10)

        row_a = QHBoxLayout()
        row_a.setSpacing(10)
        self.cookies_cb = QCheckBox("Use browser cookies")
        self.cookies_cb.toggled.connect(lambda v: self.browser_combo.setEnabled(v))
        row_a.addWidget(self.cookies_cb)
        self.browser_combo = QComboBox()
        for b in SUPPORTED_BROWSERS:
            self.browser_combo.addItem(b.capitalize(), b)
        self.browser_combo.setEnabled(False)
        self.browser_combo.setMinimumWidth(130)
        row_a.addWidget(self.browser_combo)
        row_a.addStretch()
        auth_v.addLayout(row_a)

        row_b = QHBoxLayout()
        row_b.setSpacing(10)
        imp_btn = QPushButton("Import cookies.txt")
        imp_btn.setObjectName("ghost")
        imp_btn.setMinimumWidth(150)
        imp_btn.clicked.connect(self._pick_cookies)
        row_b.addWidget(imp_btn)
        self.ck_lbl = QLabel("No file selected")
        self.ck_lbl.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        row_b.addWidget(self.ck_lbl, 1)
        auth_v.addLayout(row_b)

        root.addWidget(auth_box)

        # ── Download / Cancel ────────────────────────────────────────────────
        self.dl_btn = QPushButton("⬇   Download")
        self.dl_btn.setObjectName("big")
        self.dl_btn.setEnabled(False)
        self.dl_btn.clicked.connect(self._on_download)
        root.addWidget(self.dl_btn)

        self.cancel_btn = QPushButton("✕   Cancel")
        self.cancel_btn.setObjectName("danger")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._on_cancel)
        root.addWidget(self.cancel_btn)

        # ── Progress ─────────────────────────────────────────────────────────
        prog_box = QGroupBox("Progress")
        prog_v = QVBoxLayout(prog_box)
        prog_v.setSpacing(8)

        bar_row = QHBoxLayout()
        bar_row.setSpacing(10)
        self.prog_bar = QProgressBar()
        self.prog_bar.setValue(0)
        self.prog_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        bar_row.addWidget(self.prog_bar, 1)
        self.pct_lbl = QLabel("0%")
        self.pct_lbl.setFixedWidth(40)
        self.pct_lbl.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        bar_row.addWidget(self.pct_lbl)
        prog_v.addLayout(bar_row)

        stats_row = QHBoxLayout()
        self.speed_lbl = QLabel("")
        self.speed_lbl.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        stats_row.addWidget(self.speed_lbl, 1)
        self.eta_lbl = QLabel("")
        self.eta_lbl.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        stats_row.addWidget(self.eta_lbl)
        prog_v.addLayout(stats_row)
        root.addWidget(prog_box)

        # ── Log ──────────────────────────────────────────────────────────────
        log_box = QGroupBox("Log")
        log_v = QVBoxLayout(log_box)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(90)
        self.log_box.setPlaceholderText("Activity will appear here…")
        log_v.addWidget(self.log_box)
        root.addWidget(log_box)

        root.addStretch()

        self.setStatusBar(QStatusBar())
        self._update_status()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _short(self, p):
        h = str(Path.home())
        return ("~" + p[len(h):]) if p.startswith(h) else (p[-44:] if len(p) > 44 else p)

    def _log(self, msg):
        self.log_box.append(msg)
        sb = self.log_box.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _update_status(self):
        try:
            get_ytdlp_path()
            ff = get_ffmpeg_path()
            self.statusBar().showMessage(
                "yt-dlp ✓     ffmpeg " + ("✓" if ff else "✗  (brew install ffmpeg)")
            )
        except FileNotFoundError:
            self.statusBar().showMessage("⚠  yt-dlp not found — run: pip install yt-dlp")

    def _check_bins(self):
        try:
            get_ytdlp_path()
        except FileNotFoundError:
            QMessageBox.critical(self, "Missing dependency",
                "yt-dlp not found.\n\nRun in Terminal:\n\n  pip install yt-dlp")
        if not get_ffmpeg_path():
            self._log("⚠  ffmpeg not found — MP3/MP4 conversion unavailable.\n"
                      "   Install with:  brew install ffmpeg")

    def _on_out_changed(self, _):
        self._abr_wrapper.setVisible(
            self.out_combo.currentData() == OutputFormat.MP3
        )

    def _pick_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Choose folder", self._out_dir)
        if d:
            self._out_dir = d
            self.fld_lbl.setText(self._short(d))
            self.fld_lbl.setToolTip(d)

    def _pick_cookies(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "Select cookies.txt", str(Path.home()), "Text Files (*.txt)"
        )
        if p:
            self._cookies_file = p
            self.ck_lbl.setText(Path(p).name)
        else:
            self._cookies_file = None
            self.ck_lbl.setText("No file selected")

    # ── Fetch ─────────────────────────────────────────────────────────────────

    def _fetch(self):
        url = self.url_input.text().strip()
        if not url:
            self._log("Please enter a URL first.")
            return
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText("Fetching…")
        self.dl_btn.setEnabled(False)
        self._log(f"Fetching: {url}")
        w = FetchWorker(url, self.cookies_cb.isChecked(),
                        self.browser_combo.currentData(), self._cookies_file)
        w.signals.info_ready.connect(self._on_info)
        w.signals.error.connect(self._on_fetch_err)
        w.signals.status.connect(self._log)
        self._pool.start(w)

    @Slot(object)
    def _on_info(self, result):
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("Fetch Info")
        self.dl_btn.setEnabled(True)
        self._log("✅ Ready.")
        if isinstance(result, PlaylistInfo):
            self._playlist = result; self._entry = None
            self._show_playlist(result)
            self.fmt_combo.clear()
            self.fmt_combo.addItem("Best quality (auto)", "bestvideo+bestaudio/best")
            self.fmt_combo.addItem("Audio only", "bestaudio/best")
        else:
            self._entry = result; self._playlist = None
            self._show_single(result)
            self._load_formats(result.formats)

    @Slot(str, str)
    def _on_fetch_err(self, kind, msg):
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("Fetch Info")
        self._log(f"ERROR: {msg[:200]}")
        box = QMessageBox(self)
        box.setIcon(
            QMessageBox.Icon.Warning if kind == "auth" else QMessageBox.Icon.Critical
        )
        box.setWindowTitle("Could not fetch media info")
        box.setText(msg[:500])
        if kind == "auth":
            box.setInformativeText(
                "Enable 'Use browser cookies' and pick the browser you're logged in with, "
                "or import a cookies.txt file."
            )
        box.exec()

    def _show_single(self, e: MediaEntry):
        self._single.setVisible(True)
        self._pl_widget.setVisible(False)
        self.title_lbl.setText(e.title[:120])
        self.title_lbl.setToolTip(e.title)
        if e.duration:
            d = int(e.duration); h, r = divmod(d, 3600); m, s = divmod(r, 60)
            self.dur_lbl.setText(
                f"Duration: {h}:{m:02d}:{s:02d}" if h else f"Duration: {m}:{s:02d}"
            )
        else:
            self.dur_lbl.setText("")
        self.src_lbl.setText(f"Source: {e.extractor}")
        self.thumb.setText("Loading…")
        if e.thumbnail_url:
            tw = ThumbWorker(e.thumbnail_url)
            tw.signals.info_ready.connect(self._set_thumb)
            self._pool.start(tw)

    @Slot(object)
    def _set_thumb(self, pix):
        self.thumb.setPixmap(pix)
        self.thumb.setText("")

    def _show_playlist(self, pl: PlaylistInfo):
        self._single.setVisible(False)
        self._pl_widget.setVisible(True)
        self.pl_title_lbl.setText(f"{pl.title}  ({len(pl.entries)} items)")
        self.pl_list.clear(); self._playlist_rows = []
        for i, e in enumerate(pl.entries, 1):
            row = PlaylistRow(e, i)
            item = QListWidgetItem()
            item.setSizeHint(row.sizeHint())
            self.pl_list.addItem(item)
            self.pl_list.setItemWidget(item, row)
            self._playlist_rows.append(row)

    def _load_formats(self, formats: List[FormatInfo]):
        self.fmt_combo.clear()
        if not formats:
            self.fmt_combo.addItem("Best available", "bestvideo+bestaudio/best")
            return
        video = sorted(
            [f for f in formats if not f.is_audio_only and f.vcodec],
            key=lambda f: (
                int(f.resolution.split("x")[1]) if f.resolution and "x" in f.resolution
                else int(f.resolution[:-1]) if f.resolution and f.resolution[:-1].isdigit()
                else 0
            ), reverse=True
        )
        audio = sorted(
            [f for f in formats if f.is_audio_only],
            key=lambda f: f.abr or 0, reverse=True
        )
        self.fmt_combo.addItem("Best quality (auto)", "bestvideo+bestaudio/best")
        self.fmt_combo.insertSeparator(1)
        for f in video[:12]:
            self.fmt_combo.addItem(f.display_label, f.format_id)
        if audio:
            self.fmt_combo.insertSeparator(self.fmt_combo.count())
            for f in audio[:5]:
                self.fmt_combo.addItem(f.display_label, f.format_id)

    # ── Download ──────────────────────────────────────────────────────────────

    def _on_download(self):
        if self._playlist:
            entries = [r.entry for r in self._playlist_rows if r.is_selected]
            if not entries:
                QMessageBox.warning(self, "Nothing selected", "Select at least one item.")
                return
            self._batch = list(entries); self._batching = True
            self._next_in_batch()
        elif self._entry:
            self._run(self._entry)
        else:
            self._log("Fetch a URL first.")

    def _next_in_batch(self):
        if not self._batch:
            self._log("✅ All downloads complete!")
            self._batching = False
            return
        e = self._batch.pop(0)
        self._log(f"Downloading: {e.title[:60]}")
        self._run(e)

    def _run(self, entry: MediaEntry):
        task = DownloadTask(
            entry=entry,
            format_id=self.fmt_combo.currentData() or "bestvideo+bestaudio/best",
            output_format=self.out_combo.currentData() or OutputFormat.ORIGINAL,
            output_dir=self._out_dir,
            audio_bitrate=self.abr_combo.currentText(),
            use_cookies=self.cookies_cb.isChecked(),
            browser=self.browser_combo.currentData(),
            cookies_file=self._cookies_file,
        )
        self.dl_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        self.prog_bar.setValue(0)
        self.pct_lbl.setText("0%")
        self.speed_lbl.setText("")
        self.eta_lbl.setText("")

        self._worker = DownloadWorker(task)
        self._worker.signals.progress.connect(self._on_prog)
        self._worker.signals.status.connect(self._on_stat)
        self._worker.signals.done.connect(self._on_done)
        self._worker.signals.error.connect(self._on_dl_err)
        self._worker.signals.conv_progress.connect(
            lambda p: (
                self.prog_bar.setValue(int(p)),
                self.pct_lbl.setText(f"{p:.0f}%"),
                self.speed_lbl.setText("Converting…"),
            )
        )
        self._pool.start(self._worker)

    @Slot(float, str, str)
    def _on_prog(self, pct, speed, eta):
        self.prog_bar.setValue(int(pct))
        self.pct_lbl.setText(f"{pct:.0f}%")
        self.speed_lbl.setText(f"⚡ {speed}")
        self.eta_lbl.setText(f"ETA {eta}")

    @Slot(str)
    def _on_stat(self, msg):
        self._log(msg)
        self.statusBar().showMessage(msg[:100])

    @Slot(str)
    def _on_done(self, path):
        self.prog_bar.setValue(100)
        self.pct_lbl.setText("100%")
        self.eta_lbl.setText("Done ✓")
        self.speed_lbl.setText("")
        self.dl_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self._log(f"✅ Saved to: {path}" if path else "✅ Download complete.")
        if path:
            self.statusBar().showMessage(f"Saved: {Path(path).name}")
        if self._batching:
            self._next_in_batch()

    @Slot(str, str)
    def _on_dl_err(self, kind, msg):
        self.dl_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.prog_bar.setValue(0)
        self.pct_lbl.setText("0%")
        self.eta_lbl.setText("")
        self._batching = False
        if kind == "cancelled":
            self._log("Cancelled.")
            return
        self._log(f"ERROR: {msg[:300]}")
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("Download Failed")
        box.setText(msg[:500])
        if any(k in msg.lower() for k in ("login", "cookie", "private", "auth")):
            box.setInformativeText(
                "This content may require authentication.\n"
                "Enable 'Use browser cookies' and select your browser."
            )
        box.exec()

    def _on_cancel(self):
        self._batch = []
        self._batching = False
        if self._worker:
            self._worker.stop()
