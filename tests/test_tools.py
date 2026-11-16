from pathlib import Path
from types import SimpleNamespace

import pytest

from video_downloader import service, workers
from video_downloader.service import DownloadError


def test_missing_tools_are_actionable(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(service.shutil, "which", lambda name: None)
    with pytest.raises(DownloadError, match="FFmpeg/FFprobe"):
        service.runtime_paths()


def test_local_tools_and_js_priority(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(service.shutil, "which", lambda name: None)
    tools = tmp_path / "tools"
    tools.mkdir()
    import os

    for name in ("ffmpeg", "ffprobe", "node", "deno"):
        (tools / (name + (".exe" if os.name == "nt" else ""))).touch()
    ffmpeg, ffprobe, runtime = service.runtime_paths()
    assert Path(ffmpeg).parent == Path(ffprobe).parent == tools
    assert set(runtime) == {"deno"}


def test_missing_javascript_runtime(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        service.shutil, "which", lambda name: f"/tools/{name}" if name.startswith("ff") else None
    )
    with pytest.raises(DownloadError, match="JavaScript"):
        service.runtime_paths()


def test_old_node_diagnosis(monkeypatch):
    monkeypatch.setattr(
        service,
        "runtime_paths",
        lambda: ("/bin/ffmpeg", "/bin/ffprobe", {"node": {"path": "/bin/node"}}),
    )
    monkeypatch.setattr(
        service.subprocess,
        "run",
        lambda command, **kw: SimpleNamespace(
            returncode=0, stdout="v20.0.0" if "node" in command[0] else "ffmpeg version 7.1\n"
        ),
    )
    with pytest.raises(DownloadError, match="Actualiza node"):
        service.diagnostics()


def test_windows_cancel_stops_process_tree(monkeypatch):
    class Process:
        pid = 1234
        alive = True

        def is_alive(self):
            return self.alive

        def join(self, timeout):
            self.alive = False

    calls = []
    monkeypatch.setattr(workers, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(
        workers.subprocess, "run", lambda cmd, **kwargs: calls.append((cmd, kwargs))
    )
    process = Process()
    workers.stop_process(process)
    assert calls[0][0] == ["taskkill", "/PID", "1234", "/T", "/F"]
    assert calls[0][1]["creationflags"] == 0x08000000
    assert not process.is_alive()
