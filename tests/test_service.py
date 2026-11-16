import threading
from pathlib import Path

import pytest

from video_downloader import service
from video_downloader.models import DownloadOptions
from video_downloader.service import Cancelled, Downloader, DownloadError


@pytest.fixture(autouse=True)
def fake_tools(monkeypatch):
    monkeypatch.setattr(
        service,
        "runtime_paths",
        lambda: ("/tools/ffmpeg", "/tools/ffprobe", {"node": {"path": "/tools/node"}}),
    )


def info(**overrides):
    return {
        "id": "abcdefghijk",
        "title": "Título <&> 日本語",
        "duration": 42,
        "webpage_url": "https://www.youtube.com/watch?v=abcdefghijk",
        "thumbnail": "https://i.ytimg.com/vi/abcdefghijk/default.jpg",
        "formats": [
            {"format_id": "137", "height": 1080, "vcodec": "avc1", "acodec": "none", "ext": "mp4"},
            {"format_id": "140", "vcodec": "none", "acodec": "aac", "ext": "m4a"},
            {"format_id": "drm", "height": 2160, "has_drm": True, "vcodec": "avc1"},
        ],
        **overrides,
    }


class FakeYDL:
    configs = []
    metadata = None
    fail = None

    def __init__(self, options):
        self.options = options
        self.configs.append(options)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def extract_info(self, url, download=False):
        if self.fail:
            raise RuntimeError(self.fail)
        if not download:
            return self.metadata or info()
        folder = Path(self.options["outtmpl"]).parent
        extension = (
            "mp3" if self.options["postprocessors"][0]["key"] == "FFmpegExtractAudio" else "mp4"
        )
        output = folder / f"safe title [abcdefghijk].{extension}"
        output.write_bytes(b"simulated media, not a real YouTube download")
        for hook in self.options["progress_hooks"]:
            hook(
                {
                    "status": "downloading",
                    "downloaded_bytes": 50,
                    "total_bytes": 100,
                    "speed": 25,
                    "eta": 2,
                }
            )
            hook({"status": "finished", "downloaded_bytes": 100, "total_bytes": 100})
        for hook in self.options["post_hooks"]:
            hook(str(output))
        return info(filepath=str(output))


@pytest.fixture
def downloader():
    FakeYDL.configs = []
    FakeYDL.metadata = FakeYDL.fail = None
    return Downloader(FakeYDL)


def test_metadata_excludes_drm(downloader):
    media = downloader.inspect("https://youtu.be/abcdefghijk", threading.Event())[0]
    assert media.duration == 42
    assert media.resolutions == (1080,)
    assert len(media.formats) == 2
    assert media.thumbnail.startswith("https://i.ytimg.com/")
    assert FakeYDL.configs[0]["noplaylist"]


@pytest.mark.parametrize(
    "override",
    [
        {"is_live": True},
        {"live_status": "is_upcoming"},
        {"availability": "private"},
        {"availability": "needs_auth"},
        {"formats": [{"has_drm": True}]},
    ],
)
def test_reject_restricted_media(downloader, override):
    FakeYDL.metadata = info(**override)
    with pytest.raises(DownloadError):
        downloader.inspect("https://youtu.be/abcdefghijk", threading.Event())


def test_playlist_expansion_and_deduplication(monkeypatch, downloader):
    def extract(self, url, download=False):
        if "/playlist?" in url:
            return {"entries": [{"id": "abcdefghijk"}, {"id": "abcdefghijk"}]}
        return info()

    monkeypatch.setattr(FakeYDL, "extract_info", extract)
    result = downloader.inspect("https://youtube.com/playlist?list=PL1234567890", threading.Event())
    assert len(result) == 1
    assert FakeYDL.configs[0]["extract_flat"] == "in_playlist"


@pytest.mark.parametrize(
    "metadata",
    [
        {"entries": []},
        {"entries": [None]},
        {"entries": [{"id": "abcdefghijk"}], "playlist_count": 201},
        {"entries": [{"id": "abcdefghijk"}], "availability": "private"},
    ],
)
def test_bad_playlists(downloader, metadata):
    FakeYDL.metadata = metadata
    with pytest.raises(DownloadError):
        downloader.inspect("https://youtube.com/playlist?list=PL1234567890", threading.Event())


@pytest.mark.parametrize("audio", [True, False])
def test_download_options_progress_and_no_overwrite(downloader, media, tmp_path, audio):
    progress = []
    options = DownloadOptions(tmp_path, audio)
    first = downloader.download(media, options, threading.Event(), progress.append)
    second = downloader.download(media, options, threading.Event(), progress.append)
    assert first != second and first.is_file() and second.is_file()
    assert first.suffix == (".mp3" if audio else ".mp4")
    assert progress[0].percent == 50
    assert progress[0].speed == 25 and progress[0].eta == 2
    config = FakeYDL.configs[-1]
    assert config["windowsfilenames"] and not config["overwrites"]
    assert "cookies" not in config and "username" not in config
    assert config["format"] == ("bestaudio/best" if audio else "bv[height=1080]+ba/b[height=1080]")


def test_no_resolution_fallback(downloader, media, tmp_path):
    with pytest.raises(DownloadError, match="resolución"):
        downloader.download(
            media, DownloadOptions(tmp_path, resolution=2160), threading.Event(), lambda p: None
        )
    assert not list(tmp_path.iterdir())


def test_cancel_during_transfer_removes_only_own_files(downloader, media, tmp_path):
    existing = tmp_path / "existing.mp4"
    existing.write_bytes(b"user data")
    event = threading.Event()
    with pytest.raises(Cancelled):
        downloader.download(media, DownloadOptions(tmp_path), event, lambda progress: event.set())
    assert list(tmp_path.iterdir()) == [existing]


def test_cancel_before_inspection(downloader):
    event = threading.Event()
    event.set()
    with pytest.raises(Cancelled):
        downloader.inspect("https://youtu.be/abcdefghijk", event)
    assert not FakeYDL.configs


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        ("Requested format is not available", "formato"),
        ("Private video", "restringido"),
        ("HTTP Error 429", "limitó"),
        ("Connection timed out", "red"),
    ],
)
def test_error_classification_and_cleanup(downloader, media, tmp_path, error, expected):
    FakeYDL.fail = error
    with pytest.raises(DownloadError, match=expected):
        downloader.download(media, DownloadOptions(tmp_path), threading.Event(), lambda p: None)
    assert not list(tmp_path.iterdir())


def test_unknown_total(downloader, media, tmp_path, monkeypatch):
    def extract(self, url, download=False):
        self.options["progress_hooks"][0]({"downloaded_bytes": 10})
        raise RuntimeError("test")

    monkeypatch.setattr(FakeYDL, "extract_info", extract)
    values = []
    with pytest.raises(DownloadError):
        downloader.download(media, DownloadOptions(tmp_path), threading.Event(), values.append)
    assert values[0].percent is None and values[0].total is None
