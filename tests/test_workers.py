from dataclasses import replace

from tests.process_fixture import simulated_child
from video_downloader import workers
from video_downloader.workers import DownloadWorker


def test_real_child_process_ipc(qtbot, job, monkeypatch):
    monkeypatch.setattr(workers, "download_process", simulated_child)
    worker = DownloadWorker(job)
    with qtbot.waitSignal(worker.succeeded, timeout=10000) as signal:
        worker.start()
    assert signal.args == ["simulated.mp4"]
    assert worker.wait(5000)


def test_real_child_cancellation(qtbot, job, monkeypatch):
    monkeypatch.setattr(workers, "download_process", simulated_child)
    worker = DownloadWorker(replace(job, media=replace(job.media, title="wait")))
    with qtbot.waitSignal(worker.progressed, timeout=10000):
        worker.start()
    with qtbot.waitSignal(worker.cancelled, timeout=10000):
        worker.cancel()
    assert worker.wait(5000)


def test_crash_reported(qtbot, job, monkeypatch):
    monkeypatch.setattr(workers, "download_process", simulated_child)
    worker = DownloadWorker(replace(job, media=replace(job.media, title="crash")))
    with qtbot.waitSignal(worker.failed, timeout=10000) as signal:
        worker.start()
    assert "sin resultado" in signal.args[0]
    assert worker.wait(5000)
