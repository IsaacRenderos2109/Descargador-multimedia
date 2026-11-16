from dataclasses import replace
from threading import Event

from PySide6.QtCore import QSettings, QThread, Signal

from video_downloader.history import History
from video_downloader.models import Progress, Status
from video_downloader.queue import DownloadQueue
from video_downloader.ui import MainWindow


class FakeWorker(QThread):
    progressed = Signal(object)
    succeeded = Signal(str)
    failed = Signal(str)
    cancelled = Signal()
    started_jobs = []

    def __init__(self, job):
        super().__init__()
        self.job = job
        self.was_cancelled = False
        self.cancel_event = Event()

    def cancel(self):
        self.was_cancelled = True
        self.cancel_event.set()

    def run(self):
        self.started_jobs.append(self.job.id)
        if self.job.media.title == "wait-for-cancel":
            self.cancel_event.wait(timeout=5)
        else:
            self.msleep(30)
        if self.was_cancelled:
            self.cancelled.emit()
        elif self.job.media.title == "fail":
            self.failed.emit("Error de red simulado")
        else:
            self.progressed.emit(Progress(50, 50, 100, 25, 2))
            self.succeeded.emit("C:/Videos/simulated.mp4")


def test_serial_queue_continues_after_failure_and_records(qtbot, tmp_path, job):
    history = History(tmp_path / "h.db")
    FakeWorker.started_jobs = []
    queue = DownloadQueue(history, FakeWorker)
    bad = replace(job, id="bad", media=replace(job.media, title="fail"))
    good = replace(job, id="good", media=replace(job.media, id="lmnopqrstuv"))
    with qtbot.waitSignal(queue.idle, timeout=5000):
        queue.add([bad, good])
    assert FakeWorker.started_jobs == ["bad", "good"]
    assert bad.status == Status.FAILED and good.status == Status.COMPLETED
    assert len(history.rows()) == 2


def test_cancel_all_and_duplicate_queue(qtbot, tmp_path, job):
    queue = DownloadQueue(History(tmp_path / "h.db"), FakeWorker)
    job = replace(job, media=replace(job.media, title="wait-for-cancel"))
    pending = replace(job, id="pending", media=replace(job.media, id="lmnopqrstuv"))
    with qtbot.waitSignal(queue.idle, timeout=5000):
        queue.add([job, replace(job, id="duplicate"), pending])
        queue.cancel_all()
    assert len(queue.jobs) == 2
    assert all(item.status == Status.CANCELLED for item in queue.jobs)


def window(qtbot, tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    result = MainWindow(History(tmp_path / "h.db"), settings)
    qtbot.addWidget(result)
    result.show()
    return result


def test_ui_consent_resolution_and_enqueue(qtbot, tmp_path, media, monkeypatch):
    ui = window(qtbot, tmp_path)
    errors = []
    monkeypatch.setattr(ui, "show_error", errors.append)
    jobs = []
    monkeypatch.setattr(ui.queue, "add", jobs.extend)
    ui.received_media([media])
    assert "Video de prueba" in ui.details.toPlainText()
    assert "00:02:03" in ui.details.toPlainText()
    ui.enqueue()
    assert not jobs and "autorización" in errors[-1]
    ui.consent.setChecked(True)
    ui.resolution.setCurrentIndex(5)
    ui.enqueue()
    assert not jobs and "Resolución" in errors[-1]
    ui.resolution.setCurrentIndex(3)
    ui.destination.setText(str(tmp_path))
    ui.enqueue()
    assert len(jobs) == 1 and jobs[0].options.resolution == 1080
    assert ui.tabs.currentIndex() == 1
    ui.close()


def test_ui_invalid_input_never_starts_worker(qtbot, tmp_path, monkeypatch):
    ui = window(qtbot, tmp_path)
    errors = []
    monkeypatch.setattr(ui, "show_error", errors.append)
    ui.urls.setPlainText("https://example.com/not-youtube")
    ui.inspect_urls()
    assert errors and ui.inspector is None
    ui.close()


def test_ui_analysis_worker_and_queue_integration(qtbot, tmp_path, media, monkeypatch):
    from video_downloader.service import Downloader

    monkeypatch.setattr(Downloader, "inspect", lambda self, url, cancel: [media])
    ui = window(qtbot, tmp_path)
    ui.queue.worker_factory = FakeWorker
    ui.urls.setPlainText(media.url)
    ui.inspect_urls()
    qtbot.waitUntil(lambda: ui.inspector is None, timeout=5000)
    assert ui.media_list.count() == 1
    ui.consent.setChecked(True)
    ui.destination.setText(str(tmp_path))
    with qtbot.waitSignal(ui.queue.idle, timeout=5000):
        ui.enqueue()
    assert ui.queue.jobs[0].status == Status.COMPLETED
    assert ui.history_table.rowCount() == 1
    assert ui.progress_bar.value() == 100
    ui.close()


def test_ui_indeterminate_progress_and_selection(qtbot, tmp_path, media):
    ui = window(qtbot, tmp_path)
    ui.received_media([media])
    ui.mark_media(False)
    assert ui.media_list.item(0).checkState().value == 0
    ui.mode.setCurrentIndex(1)
    assert not ui.resolution.isEnabled()
    ui.update_progress("unknown", Progress(downloaded=300, phase="Procesando con FFmpeg"))
    assert ui.progress_bar.maximum() == 0
    assert "FFmpeg" in ui.progress_label.text()
    ui.close()
