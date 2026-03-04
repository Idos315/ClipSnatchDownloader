"""
models.py - Data structures for ClipSnatch
"""
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class OutputFormat(Enum):
    ORIGINAL = "original"
    MP4 = "mp4"
    MP3 = "mp3"


class DownloadStatus(Enum):
    IDLE = "idle"
    FETCHING = "fetching"
    READY = "ready"
    DOWNLOADING = "downloading"
    CONVERTING = "converting"
    DONE = "done"
    ERROR = "error"


@dataclass
class FormatInfo:
    format_id: str
    ext: str
    resolution: Optional[str]
    fps: Optional[float]
    vcodec: Optional[str]
    acodec: Optional[str]
    filesize: Optional[int]
    tbr: Optional[float]   # total bitrate
    abr: Optional[float]   # audio bitrate
    vbr: Optional[float]   # video bitrate
    format_note: Optional[str]
    is_audio_only: bool = False

    @property
    def display_label(self) -> str:
        if self.is_audio_only:
            br = f"{int(self.abr)}kbps" if self.abr else ""
            return f"Audio only {self.ext.upper()} {br}".strip()
        res = self.resolution or "unknown"
        note = f" ({self.format_note})" if self.format_note else ""
        fps_str = f" {int(self.fps)}fps" if self.fps and self.fps > 30 else ""
        size_str = ""
        if self.filesize:
            mb = self.filesize / (1024 * 1024)
            size_str = f" ~{mb:.1f}MB"
        return f"{res}{fps_str} {self.ext.upper()}{note}{size_str}"


@dataclass
class MediaEntry:
    """Represents a single media item (one video/clip)."""
    url: str
    title: str
    duration: Optional[float]
    thumbnail_url: Optional[str]
    formats: List[FormatInfo]
    webpage_url: str
    extractor: str
    playlist_index: Optional[int] = None
    selected: bool = True  # for carousel/playlist multi-select


@dataclass
class PlaylistInfo:
    """Represents a playlist or carousel of multiple items."""
    title: str
    entries: List[MediaEntry]
    is_playlist: bool = True


@dataclass
class DownloadTask:
    entry: MediaEntry
    format_id: str
    output_format: OutputFormat
    output_dir: str
    audio_bitrate: str = "192k"
    use_cookies: bool = False
    browser: Optional[str] = None
    cookies_file: Optional[str] = None

    # runtime state
    status: DownloadStatus = DownloadStatus.IDLE
    progress: float = 0.0
    speed: str = ""
    eta: str = ""
    error_message: str = ""
    output_path: str = ""
