from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from uuid import uuid4


class Status(StrEnum):
    QUEUED = "En cola"
    RUNNING = "Descargando"
    COMPLETED = "Completada"
    FAILED = "Error"
    CANCELLED = "Cancelada"


@dataclass(frozen=True)
class Media:
    id: str
    url: str
    title: str
    duration: float | None
    thumbnail: str | None
    resolutions: tuple[int, ...]
    formats: tuple[str, ...] = ()


@dataclass(frozen=True)
class DownloadOptions:
    destination: Path
    audio_only: bool = False
    resolution: int = 1080


@dataclass
class Job:
    media: Media
    options: DownloadOptions
    id: str = field(default_factory=lambda: uuid4().hex)
    status: Status = Status.QUEUED
    message: str = "Esperando turno"
    path: str = ""


@dataclass(frozen=True)
class Progress:
    percent: float | None = None
    downloaded: int = 0
    total: int | None = None
    speed: float | None = None
    eta: float | None = None
    phase: str = "Descargando"
