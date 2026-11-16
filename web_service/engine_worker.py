"""Isolated JSON-lines adapter that reuses the desktop yt-dlp service."""

from __future__ import annotations

import json
import os
import resource
import subprocess
import sys
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from video_downloader.models import DownloadOptions, Media, Progress  # noqa: E402
from video_downloader.service import Downloader, DownloadError  # noqa: E402
from video_downloader.validation import VIDEO_ID, validate_url  # noqa: E402


def emit(event: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
    sys.stdout.flush()


class WebDownloader(Downloader):
    def __init__(self, proxy: str, maximum: int) -> None:
        super().__init__()
        self.proxy = proxy
        self.maximum = maximum

    def _base(self) -> dict[str, Any]:
        return super()._base() | {
            "proxy": self.proxy,
            "max_filesize": self.maximum,
            "cachedir": False,
            "noplaylist": True,
            "concurrent_fragment_downloads": 1,
            "postprocessor_args": {"ffmpeg": ["-threads", "2"]},
        }


def safe_thumbnail(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "https" and (host == "ytimg.com" or host.endswith(".ytimg.com")):
        return value[:2048]
    return None


def media_dict(media: Media) -> dict[str, Any]:
    return {
        "id": media.id,
        "url": media.url,
        "title": media.title[:500],
        "duration": media.duration,
        "thumbnail": safe_thumbnail(media.thumbnail),
        "resolutions": list(media.resolutions),
        "formats": [value[:256] for value in media.formats[:80]],
    }


def synthetic(request: dict[str, Any], destination: Path) -> None:
    if os.getenv("ALLOW_SYNTHETIC_TESTS") != "1":
        raise ValueError("synthetic mode is disabled")
    url = validate_url(str(request.get("url", "")))
    if urlsplit(url).path == "/playlist":
        raise ValueError("playlists are not supported")
    if request["kind"] == "inspect":
        emit(
            {
                "event": "metadata",
                "videos": [
                    {
                        "id": "abcdefghijk",
                        "url": "https://www.youtube.com/watch?v=abcdefghijk",
                        "title": "Medio sintético de prueba",
                        "duration": 1,
                        "thumbnail": None,
                        "resolutions": [360, 720],
                        "formats": [
                            "synthetic: mp4 360p",
                            "synthetic: mp4 720p",
                            "synthetic: audio",
                        ],
                    }
                ],
            }
        )
        return

    requested = request.get("format")
    if requested not in {"mp4", "mp3"}:
        raise ValueError("invalid output format")
    output = destination / f"synthetic.{requested}"
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-f", "lavfi"]
    if requested == "mp3":
        args.extend(["-i", "sine=frequency=440:duration=1", "-c:a", "libmp3lame", "-b:a", "128k"])
    else:
        resolution = request.get("resolution")
        if resolution not in {360, 720}:
            raise ValueError("unavailable resolution")
        args.extend(
            [
                "-i",
                f"color=c=0x6c5ce7:s={resolution * 16 // 9}x{resolution}:d=1",
                "-c:v",
                "libx264",
                "-threads",
                "2",
                "-pix_fmt",
                "yuv420p",
            ]
        )
    subprocess.run([*args, str(output)], check=True, timeout=30, shell=False)
    size = output.stat().st_size
    if size > int(request["maxBytes"]):
        output.unlink(missing_ok=True)
        raise DownloadError("size limit")
    emit({"event": "result", "path": str(output.resolve()), "size": size})


def main() -> int:
    try:
        line = sys.stdin.buffer.readline(16385)
        if not line or len(line) > 16384:
            raise ValueError("invalid request size")
        request = json.loads(line)
        if request.get("kind") not in {"inspect", "download"}:
            raise ValueError("invalid operation")
        url = validate_url(str(request.get("url", "")))
        if urlsplit(url).path == "/playlist":
            raise ValueError("playlists are not supported")
        destination = Path(str(request.get("destination", ""))).resolve(strict=True)
        if not destination.is_dir():
            raise ValueError("invalid destination")
        maximum = min(int(request.get("maxBytes", 104857600)), 1073741824)
        duration_limit = min(int(request.get("maxDuration", 1800)), 14400)
        job_seconds = min(int(request.get("maxJobSeconds", 600)), 1800)
        resource.setrlimit(resource.RLIMIT_CPU, (job_seconds, job_seconds))
        resource.setrlimit(resource.RLIMIT_FSIZE, (maximum, maximum))

        if os.getenv("MEDIA_ENGINE_MODE") == "synthetic":
            synthetic(request, destination)
            return 0

        proxy = os.getenv("MEDIA_PROXY", "")
        if not proxy:
            raise DownloadError("controlled egress proxy required")
        downloader = WebDownloader(proxy, maximum)
        if request["kind"] == "inspect":
            videos = downloader.inspect(url, threading.Event())
            if len(videos) != 1:
                raise DownloadError("only individual public videos are supported")
            video = videos[0]
            if video.duration is None or video.duration > duration_limit:
                raise DownloadError("duration limit")
            emit({"event": "metadata", "videos": [media_dict(video)]})
            return 0

        value = request.get("media")
        if not isinstance(value, dict):
            raise ValueError("missing inspected media")
        media_id = str(value.get("id", ""))
        if not VIDEO_ID.fullmatch(media_id) or media_id != str(request.get("videoId", "")):
            raise ValueError("invalid media id")
        media_url = validate_url(str(value.get("url", "")))
        if media_url != url or media_url.rsplit("=", 1)[-1] != media_id:
            raise ValueError("media URL mismatch")
        duration = value.get("duration")
        if duration is None or float(duration) > duration_limit:
            raise DownloadError("duration limit")
        resolutions = tuple(int(item) for item in value.get("resolutions", []))
        formats = str(request.get("format", ""))
        resolution = int(request.get("resolution", 0))
        if formats not in {"mp3", "mp4"} or (formats == "mp4" and resolution not in resolutions):
            raise DownloadError("unavailable format")
        media = Media(
            id=media_id,
            url=media_url,
            title=str(value.get("title", media_id))[:500],
            duration=float(duration),
            thumbnail=safe_thumbnail(value.get("thumbnail")),
            resolutions=resolutions,
            formats=tuple(str(item)[:256] for item in value.get("formats", [])[:80]),
        )

        def progress(value: Progress) -> None:
            if value.downloaded > maximum:
                raise DownloadError("size limit")
            emit({"event": "progress", "progress": asdict(value)})

        output = downloader.download(
            media,
            DownloadOptions(
                destination=destination, audio_only=formats == "mp3", resolution=resolution
            ),
            threading.Event(),
            progress,
        )
        size = output.stat().st_size
        if size > maximum or output.resolve().parent.parent != destination:
            if size > maximum:
                output.unlink(missing_ok=True)
            raise DownloadError("invalid output")
        emit({"event": "result", "path": str(output.resolve()), "size": size})
        return 0
    except Exception as error:
        text = str(error).lower()
        code = (
            "RESTRICTED"
            if any(
                term in text
                for term in ("private", "sign in", "drm", "restricted", "authentication")
            )
            else "NETWORK"
            if any(term in text for term in ("network", "connection", "timed out", "proxy"))
            else "LIMIT"
            if any(term in text for term in ("limit", "large", "too big"))
            else "FORMAT"
            if "format" in text or "resolution" in text
            else "ENGINE"
        )
        emit({"event": "error", "code": code})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
