from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal

from .history import History
from .models import Job, Status
from .workers import DownloadWorker


class DownloadQueue(QObject):
    changed = Signal(object)
    progressed = Signal(str, object)
    persistence_error = Signal(str)
    idle = Signal()

    def __init__(
        self,
        history: History,
        worker_factory: Callable[[Job], DownloadWorker] = DownloadWorker,
    ) -> None:
        super().__init__()
        self.history = history
        self.worker_factory = worker_factory
        self.jobs: list[Job] = []
        self.worker: DownloadWorker | None = None
        self.current: Job | None = None

    def add(self, jobs: list[Job]) -> None:
        for job in jobs:
            if any(
                old.media.id == job.media.id
                and old.options == job.options
                and old.status in {Status.QUEUED, Status.RUNNING}
                for old in self.jobs
            ):
                continue
            self.jobs.append(job)
            self.changed.emit(job)
        self._next()

    def _next(self) -> None:
        if self.worker is not None:
            return
        job = next((job for job in self.jobs if job.status == Status.QUEUED), None)
        if job is None:
            self.idle.emit()
            return
        self.current = job
        job.status = Status.RUNNING
        job.message = "Iniciando…"
        worker = self.worker_factory(job)
        self.worker = worker
        worker.progressed.connect(lambda progress: self.progressed.emit(job.id, progress))
        worker.succeeded.connect(lambda path: self._finish(job, Status.COMPLETED, "Guardado", path))
        worker.failed.connect(lambda message: self._finish(job, Status.FAILED, message))
        worker.cancelled.connect(
            lambda: self._finish(job, Status.CANCELLED, "Cancelada por el usuario")
        )
        worker.finished.connect(self._worker_finished)
        self.changed.emit(job)
        worker.start()

    def _finish(self, job: Job, status: Status, message: str, path: str = "") -> None:
        job.status, job.message, job.path = status, message, path
        self._record(job)
        self.changed.emit(job)

    def _record(self, job: Job) -> None:
        try:
            self.history.record(job)
        except Exception as error:
            self.persistence_error.emit(f"No se pudo guardar el historial: {error}")

    def _worker_finished(self) -> None:
        if self.current is not None and self.current.status == Status.RUNNING:
            self._finish(self.current, Status.FAILED, "El worker terminó sin resultado")
        if self.worker:
            self.worker.deleteLater()
        self.worker = None
        self.current = None
        QTimer.singleShot(0, self._next)

    def cancel(self, job_id: str) -> None:
        for job in self.jobs:
            if job.id != job_id:
                continue
            if job.status == Status.QUEUED:
                self._finish(job, Status.CANCELLED, "Cancelada antes de iniciar")
            elif job.status == Status.RUNNING and self.worker:
                job.message = "Cancelando…"
                self.changed.emit(job)
                self.worker.cancel()

    def cancel_all(self) -> None:
        for job in self.jobs:
            if job.status == Status.QUEUED:
                self._finish(job, Status.CANCELLED, "Cancelada antes de iniciar")
        if self.current:
            self.cancel(self.current.id)

    @property
    def busy(self) -> bool:
        return self.worker is not None or any(job.status == Status.QUEUED for job in self.jobs)
