"""
ffmpeg_service.py - FFmpeg conversion wrapper for ClipSnatch
"""
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Callable, Optional

from ytdlp_service import get_ffmpeg_path

logger = logging.getLogger(__name__)

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)")
_TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+)\.(\d+)")


def _parse_time(h, m, s, cs) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100


def convert_to_mp3(
    input_path: str,
    output_dir: str,
    bitrate: str = "192k",
    on_progress: Optional[Callable[[float, str], None]] = None,
    stop_flag: Optional[Callable[[], bool]] = None,
) -> str:
    """Convert any audio/video file to MP3."""
    ffmpeg = get_ffmpeg_path()
    if not ffmpeg:
        raise FileNotFoundError(
            "ffmpeg not found. Install it or place the binary in resources/."
        )

    stem = Path(input_path).stem
    out_path = str(Path(output_dir) / f"{stem}.mp3")

    cmd = [
        ffmpeg, "-y",
        "-i", input_path,
        "-vn",                  # no video
        "-acodec", "libmp3lame",
        "-b:a", bitrate,
        "-id3v2_version", "3",
        out_path,
    ]

    logger.debug("ffmpeg mp3 cmd: %s", cmd)
    _run_ffmpeg(cmd, on_progress, stop_flag)

    if os.path.isfile(input_path) and input_path != out_path:
        try:
            os.remove(input_path)
        except OSError:
            pass

    return out_path


def convert_to_mp4(
    input_path: str,
    output_dir: str,
    on_progress: Optional[Callable[[float, str], None]] = None,
    stop_flag: Optional[Callable[[], bool]] = None,
) -> str:
    """
    Re-mux/transcode to MP4 with H.264 video + AAC audio.
    If already H.264 + AAC, stream-copy (fast). Otherwise transcode.
    """
    ffmpeg = get_ffmpeg_path()
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg not found.")

    stem = Path(input_path).stem
    out_path = str(Path(output_dir) / f"{stem}.mp4")

    if input_path == out_path:
        out_path = str(Path(output_dir) / f"{stem}_converted.mp4")

    # Try stream copy first (fast path)
    cmd = [
        ffmpeg, "-y",
        "-i", input_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-movflags", "+faststart",
        out_path,
    ]

    logger.debug("ffmpeg mp4 cmd: %s", cmd)
    try:
        _run_ffmpeg(cmd, on_progress, stop_flag)
    except RuntimeError:
        # Fallback: full transcode
        cmd = [
            ffmpeg, "-y",
            "-i", input_path,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            out_path,
        ]
        logger.info("Stream copy failed, retrying with full transcode")
        _run_ffmpeg(cmd, on_progress, stop_flag)

    if os.path.isfile(input_path) and input_path != out_path:
        try:
            os.remove(input_path)
        except OSError:
            pass

    return out_path


def _run_ffmpeg(
    cmd: list,
    on_progress: Optional[Callable[[float, str], None]],
    stop_flag: Optional[Callable[[], bool]],
):
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    total_secs: Optional[float] = None
    stderr_buf = []

    for line in proc.stdout:
        if stop_flag and stop_flag():
            proc.terminate()
            raise InterruptedError("Conversion cancelled.")

        line = line.rstrip()
        logger.debug("ffmpeg: %s", line)
        stderr_buf.append(line)

        m = _DURATION_RE.search(line)
        if m and total_secs is None:
            total_secs = _parse_time(*m.groups())

        m = _TIME_RE.search(line)
        if m and on_progress:
            current = _parse_time(*m.groups())
            pct = (current / total_secs * 100) if total_secs else 0
            on_progress(min(pct, 99.9), line[:100])

    proc.wait()
    if proc.returncode not in (0, None):
        err = "\n".join(stderr_buf[-20:])
        raise RuntimeError(f"ffmpeg failed (code {proc.returncode}):\n{err}")

    if on_progress:
        on_progress(100.0, "Conversion complete")
