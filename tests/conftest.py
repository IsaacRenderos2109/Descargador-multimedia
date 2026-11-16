from pathlib import Path

import pytest

from video_downloader.models import DownloadOptions, Job, Media


@pytest.fixture
def media() -> Media:
    return Media(
        "abcdefghijk",
        "https://www.youtube.com/watch?v=abcdefghijk",
        "Video de prueba",
        123,
        None,
        (360, 720, 1080),
        ("137: mp4 1080",),
    )


@pytest.fixture
def job(media: Media, tmp_path: Path) -> Job:
    return Job(media, DownloadOptions(tmp_path / "downloads"))
