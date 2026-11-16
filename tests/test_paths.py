import threading
from dataclasses import replace
from pathlib import Path

import pytest
import yt_dlp

from video_downloader.models import DownloadOptions
from video_downloader.service import Downloader, DownloadError


def test_windows_filename_sanitizing(tmp_path):
    with yt_dlp.YoutubeDL(
        {
            "quiet": True,
            "windowsfilenames": True,
            "outtmpl": str(tmp_path / "%(title).48B [%(id)s].%(ext)s"),
        }
    ) as downloader:
        filename = downloader.prepare_filename(
            {
                "id": "abcdefghijk",
                "title": 'CON: ../ 日本語 <bad>|?* "title"',
                "ext": "mp4",
            }
        )
    name = Path(filename).name
    assert not any(char in name for char in '<>:"/\\|?*')
    assert "abcdefghijk" in name and name.endswith(".mp4")
    assert len(name.encode("utf-8")) < 100


def test_reject_unsafe_video_id_before_creating_files(tmp_path, media):
    with pytest.raises(DownloadError, match="Identificador"):
        Downloader().download(
            replace(media, id="../../escape"),
            DownloadOptions(tmp_path),
            threading.Event(),
            lambda progress: None,
        )
    assert not list(tmp_path.iterdir())
