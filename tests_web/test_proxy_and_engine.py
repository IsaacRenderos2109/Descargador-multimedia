from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from infra.egress_proxy import allowed_host, public_address, tunnel
from web_service.engine_worker import WebDownloader
from web_service.manager import EngineFailure, validate_progress, validate_video

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "web_service" / "engine_worker.py"


def test_proxy_allowlist_and_ip_filter() -> None:
    assert allowed_host("www.youtube.com")
    assert allowed_host("r1---sn.googlevideo.com")
    assert allowed_host("i.ytimg.com")
    assert not allowed_host("youtube.com.attacker.example")
    assert not allowed_host("localhost")
    assert public_address("8.8.8.8")
    assert not public_address("127.0.0.1")
    assert not public_address("169.254.169.254")
    assert not public_address("::1")


def test_proxy_denies_private_connect_before_dns() -> None:
    async def exercise() -> bytes:
        server = await asyncio.start_server(tunnel, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        async with server:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.write(b"CONNECT 127.0.0.1:443 HTTP/1.1\r\nHost: 127.0.0.1:443\r\n\r\n")
            await writer.drain()
            result = await reader.read()
            writer.close()
            await writer.wait_closed()
            return result

    assert asyncio.run(exercise()).startswith(b"HTTP/1.1 403")


@pytest.mark.parametrize("output_format", ["mp3", "mp4"])
def test_synthetic_engine_generates_download_without_network(
    tmp_path: Path, output_format: str
) -> None:
    env = os.environ.copy()
    env.update({"MEDIA_ENGINE_MODE": "synthetic", "ALLOW_SYNTHETIC_TESTS": "1"})
    env.pop("MEDIA_PROXY", None)
    request = {
        "kind": "download",
        "url": "https://youtu.be/abcdefghijk",
        "format": output_format,
        "resolution": 360,
        "destination": str(tmp_path),
        "maxBytes": 10485760,
        "maxDuration": 1800,
        "maxJobSeconds": 30,
    }
    process = subprocess.run(
        [sys.executable, str(ENGINE)],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        env=env,
        timeout=40,
        check=False,
    )
    assert process.returncode == 0, process.stderr + process.stdout
    result = json.loads(process.stdout.splitlines()[-1])
    assert result["event"] == "result"
    media = Path(result["path"])
    assert media.parent == tmp_path
    assert media.suffix == f".{output_format}"
    assert media.stat().st_size == result["size"] > 0
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=format_name",
            "-of",
            "json",
            str(media),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    name = json.loads(probe.stdout)["format"]["format_name"]
    assert "mp3" in name if output_format == "mp3" else "mp4" in name


def test_synthetic_engine_rejects_unsafe_url(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.update({"MEDIA_ENGINE_MODE": "synthetic", "ALLOW_SYNTHETIC_TESTS": "1"})
    request = {
        "kind": "inspect",
        "url": "https://127.0.0.1/video",
        "destination": str(tmp_path),
        "maxBytes": 10485760,
    }
    process = subprocess.run(
        [sys.executable, str(ENGINE)],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
    )
    assert process.returncode != 0
    assert json.loads(process.stdout.splitlines()[-1])["event"] == "error"


def test_ytdlp_metadata_filter_rejects_private_and_drm() -> None:
    downloader = WebDownloader("http://localhost:3128", 10485760)
    private = {"id": "abcdefghijk", "availability": "private", "formats": [{"format_id": "1"}]}
    with pytest.raises(Exception, match="público"):
        downloader._media(private)
    drm = {
        "id": "abcdefghijk",
        "webpage_url": "https://www.youtube.com/watch?v=abcdefghijk",
        "formats": [{"format_id": "1", "has_drm": True, "height": 360}],
    }
    with pytest.raises(Exception, match="DRM"):
        downloader._media(drm)


def test_worker_messages_reject_mismatched_urls_and_non_finite_progress() -> None:
    invalid_video = {
        "id": "abcdefghijk",
        "url": "https://www.youtube.com/watch?v=lmnopqrstuv",
        "title": "Sintético",
        "duration": 10,
        "thumbnail": None,
        "resolutions": [360],
        "formats": ["mock"],
    }
    with pytest.raises(EngineFailure, match="PROTOCOL"):
        validate_video(invalid_video)
    with pytest.raises(EngineFailure, match="PROTOCOL"):
        validate_progress({"percent": float("inf")})
