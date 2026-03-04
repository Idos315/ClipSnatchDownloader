"""
ytdlp_service.py - yt-dlp subprocess wrapper for ClipSnatch
"""
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Callable, Union

from models import FormatInfo, MediaEntry, PlaylistInfo, DownloadTask, DownloadStatus

logger = logging.getLogger(__name__)

# ─── Binary resolution ────────────────────────────────────────────────────────

def _find_binary(name: str) -> Optional[str]:
    """Find a binary: first check bundled resources, then PATH."""
    # 1. PyInstaller bundle: next to the executable
    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys.executable).parent
        candidate = bundle_dir / name
        if candidate.exists():
            return str(candidate)
        candidate = bundle_dir / "resources" / name
        if candidate.exists():
            return str(candidate)

    # 2. Adjacent resources/ folder (dev mode)
    dev_resources = Path(__file__).parent / "resources" / name
    if dev_resources.exists():
        return str(dev_resources)

    # 3. System PATH
    found = shutil.which(name)
    if found:
        return found

    # 4. Common Homebrew / standard paths
    for prefix in ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"]:
        p = Path(prefix) / name
        if p.exists():
            return str(p)

    return None


def get_ytdlp_path() -> str:
    path = _find_binary("yt-dlp")
    if not path:
        raise FileNotFoundError(
            "yt-dlp not found. Install it with: pip install yt-dlp  "
            "or place the binary in the resources/ folder."
        )
    return path


def get_ffmpeg_path() -> Optional[str]:
    return _find_binary("ffmpeg")


# ─── Cookie helpers ────────────────────────────────────────────────────────────

SUPPORTED_BROWSERS = ["chrome", "firefox", "edge", "chromium", "brave", "opera"]
# Safari cookies require special entitlement on macOS; skip for now.

def build_cookie_args(
    use_browser_cookies: bool,
    browser: Optional[str],
    cookies_file: Optional[str],
) -> list:
    args = []
    if cookies_file and os.path.isfile(cookies_file):
        args += ["--cookies", cookies_file]
    elif use_browser_cookies and browser:
        args += ["--cookies-from-browser", browser.lower()]
    return args


# ─── Metadata fetching ────────────────────────────────────────────────────────

def _parse_format(f: dict) -> FormatInfo:
    vcodec = f.get("vcodec", "none")
    acodec = f.get("acodec", "none")
    is_audio_only = vcodec in (None, "none") and acodec not in (None, "none")

    width = f.get("width")
    height = f.get("height")
    if width and height:
        resolution = f"{width}x{height}"
    elif height:
        resolution = f"{height}p"
    else:
        resolution = f.get("resolution") or f.get("format_note") or None

    return FormatInfo(
        format_id=f["format_id"],
        ext=f.get("ext", "?"),
        resolution=resolution,
        fps=f.get("fps"),
        vcodec=vcodec if vcodec != "none" else None,
        acodec=acodec if acodec != "none" else None,
        filesize=f.get("filesize") or f.get("filesize_approx"),
        tbr=f.get("tbr"),
        abr=f.get("abr"),
        vbr=f.get("vbr"),
        format_note=f.get("format_note"),
        is_audio_only=is_audio_only,
    )


def _entry_from_info(info: dict, url: str) -> MediaEntry:
    raw_formats = info.get("formats", [])
    formats = [_parse_format(f) for f in raw_formats]
    # Filter out storyboard / mhtml formats
    formats = [f for f in formats if f.ext not in ("mhtml",)]

    return MediaEntry(
        url=url,
        title=info.get("title", "Untitled"),
        duration=info.get("duration"),
        thumbnail_url=info.get("thumbnail"),
        formats=formats,
        webpage_url=info.get("webpage_url", url),
        extractor=info.get("extractor_key", ""),
        playlist_index=info.get("playlist_index"),
    )


def fetch_info(
    url: str,
    use_cookies: bool = False,
    browser: Optional[str] = None,
    cookies_file: Optional[str] = None,
    on_progress: Optional[Callable[[str], None]] = None,
) -> Union[MediaEntry, PlaylistInfo]:
    """
    Run yt-dlp -J to fetch metadata.
    Returns MediaEntry for single items, PlaylistInfo for playlists/carousels.
    """
    ytdlp = get_ytdlp_path()
    cmd = [ytdlp, "--dump-json", "--no-warnings", "--flat-playlist", url]
    cmd += build_cookie_args(use_cookies, browser, cookies_file)

    logger.debug("fetch_info cmd: %s", cmd)

    if on_progress:
        on_progress("Fetching media info…")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Timed out fetching media info. Check your internet connection.")
    except FileNotFoundError:
        raise RuntimeError(f"yt-dlp binary not found at: {ytdlp}")

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode != 0:
        _raise_helpful_error(stderr, url)

    # Multiple JSON lines = playlist / carousel
    lines = [l for l in stdout.splitlines() if l.strip().startswith("{")]
    if not lines:
        raise RuntimeError("yt-dlp returned no data. The URL may be invalid or private.")

    if len(lines) == 1:
        info = json.loads(lines[0])
        # Might be a playlist wrapper with a single entry
        if info.get("_type") == "playlist":
            return _handle_playlist_info(info, url, use_cookies, browser, cookies_file, on_progress)
        return _entry_from_info(info, url)

    # Multiple lines = flat playlist dump
    entries = []
    for line in lines:
        try:
            info = json.loads(line)
            entry = _entry_from_info(info, info.get("url", info.get("webpage_url", url)))
            entries.append(entry)
        except Exception as exc:
            logger.warning("Skipping malformed entry: %s", exc)
    
    if not entries:
        raise RuntimeError("No valid media entries found.")
    
    if len(entries) == 1:
        return entries[0]

    return PlaylistInfo(title="Playlist / Carousel", entries=entries)


def _handle_playlist_info(
    info: dict,
    url: str,
    use_cookies: bool,
    browser: Optional[str],
    cookies_file: Optional[str],
    on_progress: Optional[Callable[[str], None]],
) -> Union[MediaEntry, PlaylistInfo]:
    """Re-fetch a playlist with full format info for each entry."""
    ytdlp = get_ytdlp_path()
    cmd = [ytdlp, "-J", "--no-warnings", url]
    cmd += build_cookie_args(use_cookies, browser, cookies_file)
    
    if on_progress:
        on_progress("Fetching playlist info (this may take a moment)…")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        _raise_helpful_error(result.stderr, url)

    full_info = json.loads(result.stdout)
    raw_entries = full_info.get("entries", [])

    if not raw_entries:
        # Single item wrapped in playlist
        return _entry_from_info(full_info, url)

    entries = [_entry_from_info(e, e.get("webpage_url", url)) for e in raw_entries if e]
    title = full_info.get("title", "Playlist")

    if len(entries) == 1:
        return entries[0]

    return PlaylistInfo(title=title, entries=entries)


def _raise_helpful_error(stderr: str, url: str):
    lower = stderr.lower()
    if any(k in lower for k in ("login", "sign in", "private", "not available", "age-restricted")):
        raise PermissionError(
            "This content requires authentication.\n\n"
            "Try enabling 'Use browser cookies' and selecting a browser where you're logged in, "
            "or import a cookies.txt file.\n\n"
            f"Detail: {stderr[:400]}"
        )
    if "not supported" in lower or "unsupported url" in lower:
        raise ValueError(
            f"URL not supported by yt-dlp: {url}\n\nDetail: {stderr[:400]}"
        )
    if "network" in lower or "connection" in lower:
        raise ConnectionError(
            f"Network error fetching URL.\n\nDetail: {stderr[:400]}"
        )
    raise RuntimeError(f"yt-dlp error:\n{stderr[:600]}")


# ─── Download ─────────────────────────────────────────────────────────────────

_PROGRESS_RE = re.compile(
    r"\[download\]\s+(?P<pct>[\d.]+)%\s+of\s+~?(?P<size>\S+)\s+"
    r"at\s+(?P<speed>\S+)\s+ETA\s+(?P<eta>\S+)"
)


def download(
    task: DownloadTask,
    on_progress: Callable[[float, str, str, str], None],
    on_status: Callable[[str], None],
    stop_flag: Callable[[], bool],
) -> str:
    """
    Download media. Returns path to the downloaded file.
    Calls on_progress(pct, speed, eta, status_line).
    """
    ytdlp = get_ytdlp_path()
    ffmpeg = get_ffmpeg_path()

    safe_title = _safe_filename(task.entry.title)
    out_template = str(Path(task.output_dir) / f"{safe_title}.%(ext)s")

    cmd = [
        ytdlp,
        "--no-warnings",
        "--newline",
        "--progress",
        "-o", out_template,
    ]

    # When the user wants MP4, force H.264+AAC — the only format QuickTime
    # reliably plays. We prefer native h264 streams and re-encode the rest.
    from models import OutputFormat as _OF
    if task.output_format == _OF.MP4 and ffmpeg:
        cmd += [
            "-f",
            "bestvideo[vcodec^=avc1]+bestaudio[ext=m4a]/"
            "bestvideo[vcodec^=avc]+bestaudio[ext=m4a]/"
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
            "bestvideo+bestaudio/best",
            "--merge-output-format", "mp4",
            "--postprocessor-args",
            "ffmpeg:-c:v libx264 -c:a aac -movflags +faststart",
        ]
    else:
        cmd += ["-f", task.format_id]

    if ffmpeg:
        cmd += ["--ffmpeg-location", str(Path(ffmpeg).parent)]

    cmd += build_cookie_args(task.use_cookies, task.browser, task.cookies_file)
    cmd += ["--", task.entry.webpage_url]

    logger.debug("download cmd: %s", cmd)
    on_status("Starting download…")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    last_file = None

    for line in proc.stdout:
        if stop_flag():
            proc.terminate()
            raise InterruptedError("Download cancelled.")

        line = line.rstrip()
        logger.debug("yt-dlp: %s", line)

        # Detect output file
        if line.startswith("[download] Destination:"):
            last_file = line.split("Destination:", 1)[1].strip()
        elif line.startswith("[Merger] Merging formats into"):
            last_file = line.split('"')[1] if '"' in line else last_file
        elif line.startswith("[ExtractAudio] Destination:"):
            last_file = line.split("Destination:", 1)[1].strip()

        # Parse progress
        m = _PROGRESS_RE.search(line)
        if m:
            pct = float(m.group("pct"))
            on_progress(pct, m.group("speed"), m.group("eta"), line)
        elif line.strip():
            on_status(line[:120])

    proc.wait()
    if proc.returncode not in (0, None):
        raise RuntimeError(f"yt-dlp exited with code {proc.returncode}")

    if not last_file:
        # Try to guess
        candidates = list(Path(task.output_dir).glob(f"{safe_title}.*"))
        if candidates:
            last_file = str(max(candidates, key=lambda p: p.stat().st_mtime))

    return last_file or ""


def _safe_filename(title: str) -> str:
    """Sanitize a title to be filesystem-safe."""
    safe = re.sub(r'[\\/*?:"<>|]', "_", title)
    safe = re.sub(r"\s+", " ", safe).strip()
    return safe[:180] or "download"
