from __future__ import annotations

import asyncio
import json
import math
import os
import re
import shutil
import signal
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit
from uuid import uuid4

from video_downloader.validation import ValidationError as YouTubeValidationError
from video_downloader.validation import validate_url

from .config import Settings


class PublicJobError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class EngineFailure(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class Runner(Protocol):
    async def run(
        self,
        request: dict[str, Any],
        directory: Path,
        emit: Any,
    ) -> dict[str, Any]: ...


class SubprocessRunner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def run(self, request: dict[str, Any], directory: Path, emit: Any) -> dict[str, Any]:
        child_request = request | {
            "destination": str(directory),
            "maxBytes": self.settings.max_file_bytes,
            "maxDuration": self.settings.max_media_seconds,
            "maxJobSeconds": self.settings.max_job_seconds,
        }
        safe_env = {
            key: os.environ[key]
            for key in ("PATH", "LANG", "LC_ALL", "SYSTEMROOT", "WINDIR", "SSL_CERT_FILE")
            if key in os.environ
        }
        safe_env.update(
            {
                "HOME": str(directory),
                "MEDIA_PROXY": self.settings.media_proxy,
                "MEDIA_ENGINE_MODE": os.getenv("MEDIA_ENGINE_MODE", "real"),
                "ALLOW_SYNTHETIC_TESTS": os.getenv("ALLOW_SYNTHETIC_TESTS", "0"),
                "NO_PROXY": "",
                "no_proxy": "",
            }
        )
        script = Path(__file__).with_name("engine_worker.py")
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(script),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            cwd=directory,
            env=safe_env,
            start_new_session=(os.name != "nt"),
            limit=1_100_000,
        )
        assert process.stdin and process.stdout
        total_stdout = 0
        got_result = False
        last_disk_check = 0.0
        try:
            process.stdin.write(
                json.dumps(child_request, ensure_ascii=False).encode("utf-8") + b"\n"
            )
            await process.stdin.drain()
            process.stdin.close()
            while True:
                try:
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=0.25)
                except TimeoutError:
                    line = None
                if line is None:
                    if process.returncode is not None:
                        break
                elif not line:
                    break
                else:
                    total_stdout += len(line)
                    if len(line) > 1_000_000 or total_stdout > 2_000_000:
                        raise EngineFailure("LIMIT")
                    try:
                        event = json.loads(
                            line,
                            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
                        )
                    except (json.JSONDecodeError, ValueError) as error:
                        raise EngineFailure("PROTOCOL") from error
                    if not isinstance(event, dict):
                        raise EngineFailure("PROTOCOL")
                    kind = event.get("event")
                    if kind == "error":
                        code = event.get("code")
                        if code not in {"RESTRICTED", "NETWORK", "LIMIT", "FORMAT", "ENGINE"}:
                            raise EngineFailure("PROTOCOL")
                        raise EngineFailure(code)
                    if kind == "metadata":
                        videos = event.get("videos")
                        if not isinstance(videos, list) or len(videos) != 1:
                            raise EngineFailure("PROTOCOL")
                        event["videos"] = [validate_video(videos[0])]
                    elif kind == "progress":
                        event["progress"] = validate_progress(event.get("progress"))
                    elif kind == "result":
                        candidate = Path(str(event.get("path", "")))
                        if candidate.is_symlink():
                            raise EngineFailure("UNSAFE_FILE")
                        path = candidate.resolve(strict=True)
                        size = int(event.get("size", 0))
                        if (
                            not path.is_file()
                            or not path.is_relative_to(directory.resolve())
                            or size < 1
                            or size > self.settings.max_file_bytes
                            or path.stat().st_size != size
                            or (path.parent != directory and path.parent.parent != directory)
                        ):
                            raise EngineFailure("UNSAFE_FILE")
                        event["path"] = str(path)
                        event["size"] = size
                        got_result = True
                    else:
                        raise EngineFailure("PROTOCOL")
                    emit(event)
                if time.monotonic() - last_disk_check >= 1:
                    last_disk_check = time.monotonic()
                    if (
                        await asyncio.to_thread(directory_size, directory)
                        > self.settings.max_file_bytes * 2
                    ):
                        raise EngineFailure("LIMIT")
            return_code = await process.wait()
            if return_code != 0 or not got_result and request["kind"] == "download":
                raise EngineFailure("ENGINE")
            return {"ok": True}
        finally:
            if process.returncode is None:
                await terminate_process(process)


def directory_size(directory: Path) -> int:
    total = 0
    for root, directories, files in os.walk(directory, followlinks=False):
        directories[:] = [name for name in directories if not (Path(root) / name).is_symlink()]
        for name in files:
            path = Path(root) / name
            if path.is_symlink():
                raise EngineFailure("UNSAFE_FILE")
            total += path.stat().st_size
    return total


async def terminate_process(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    try:
        if os.name == "nt":
            process.terminate()
        else:
            os.killpg(process.pid, signal.SIGTERM)
        await asyncio.wait_for(process.wait(), timeout=2)
    except (ProcessLookupError, TimeoutError):
        try:
            if os.name == "nt":
                process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        await process.wait()


def validate_video(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EngineFailure("PROTOCOL")
    video_id = value.get("id")
    url = value.get("url")
    title = value.get("title")
    duration = value.get("duration")
    resolutions = value.get("resolutions")
    formats = value.get("formats")
    try:
        canonical_url = validate_url(url) if isinstance(url, str) else None
    except YouTubeValidationError:
        canonical_url = None
    if (
        not isinstance(video_id, str)
        or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id)
        or not isinstance(url, str)
        or urlsplit(url).scheme != "https"
        or urlsplit(url).hostname not in {"www.youtube.com", "youtube.com"}
        or not isinstance(title, str)
        or not isinstance(duration, (int, float))
        or not 0 <= duration <= 14400
        or not isinstance(resolutions, list)
        or any(value not in {360, 480, 720, 1080, 1440, 2160} for value in resolutions)
        or not isinstance(formats, list)
        or canonical_url != f"https://www.youtube.com/watch?v={video_id}"
    ):
        raise EngineFailure("PROTOCOL")
    thumbnail = value.get("thumbnail")
    if thumbnail is not None:
        parsed_thumbnail = urlsplit(thumbnail) if isinstance(thumbnail, str) else None
        if (
            not parsed_thumbnail
            or parsed_thumbnail.scheme != "https"
            or not (parsed_thumbnail.hostname or "").endswith(".ytimg.com")
        ):
            thumbnail = None
    return {
        "id": video_id,
        "url": url,
        "title": title[:500],
        "duration": duration,
        "thumbnail": thumbnail,
        "resolutions": sorted(set(resolutions)),
        "formats": [item[:256] for item in formats[:80] if isinstance(item, str)],
    }


def validate_progress(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EngineFailure("PROTOCOL")
    numeric = ("percent", "downloaded", "total", "speed", "eta")
    for name in numeric:
        item = value.get(name)
        if item is not None and (
            not isinstance(item, (int, float)) or not math.isfinite(item) or item < 0
        ):
            raise EngineFailure("PROTOCOL")
    percent = value.get("percent")
    if percent is not None and percent > 100:
        raise EngineFailure("PROTOCOL")
    phase = value.get("phase", "Descargando")
    if not isinstance(phase, str):
        raise EngineFailure("PROTOCOL")
    return {
        "percent": percent,
        "downloaded": int(value.get("downloaded") or 0),
        "total": value.get("total"),
        "speed": value.get("speed"),
        "eta": value.get("eta"),
        "phase": phase[:120],
    }


ERROR_MESSAGES = {
    "CANCELLED": "Trabajo cancelado.",
    "FORMAT": "El formato seleccionado ya no está disponible. Analiza el enlace otra vez.",
    "LIMIT": "El medio supera los límites permitidos.",
    "NETWORK": "No se pudo conectar con YouTube. Inténtalo más tarde.",
    "RESTRICTED": "El video es privado, restringido o requiere autenticación.",
    "ENGINE": "No se pudo procesar el video. Revisa FFmpeg e inténtalo de nuevo.",
}


@dataclass(slots=True)
class Job:
    id: str
    owner: str
    kind: str
    title: str
    created_at: float
    updated_at: float
    status: str = "queued"
    progress: dict[str, Any] | None = None
    metadata: list[dict[str, Any]] | None = None
    error: str | None = None
    file_path: Path | None = None
    file_size: int | None = None
    expires_at: float | None = None
    directory: Path | None = None
    task: asyncio.Task[None] | None = field(default=None, repr=False)

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title[:500],
            "status": self.status,
            "progress": self.progress,
            "metadata": self.metadata,
            "error": self.error,
            "createdAt": datetime.fromtimestamp(self.created_at, UTC).isoformat(),
            "updatedAt": datetime.fromtimestamp(self.updated_at, UTC).isoformat(),
            "file": (
                {
                    "size": self.file_size,
                    "expiresAt": datetime.fromtimestamp(self.expires_at, UTC).isoformat(),
                }
                if self.file_path and self.expires_at and self.status == "completed"
                else None
            ),
        }


class JobManager:
    def __init__(self, settings: Settings, runner: Runner | None = None) -> None:
        self.settings = settings
        self.runner = runner or SubprocessRunner(settings)
        self.jobs: dict[str, Job] = {}
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)
        self.run_root: Path | None = None
        self.cleanup_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self.settings.job_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Only remove directories carrying our private sentinel and older than the TTL.
        now = time.time()
        for path in self.settings.job_root.glob("instance-*"):
            marker = path / ".video-downloader-owned"
            if (
                path.is_dir()
                and marker.is_file()
                and now - path.stat().st_mtime > self.settings.job_ttl_seconds
            ):
                shutil.rmtree(path, ignore_errors=True)
        self.run_root = Path(tempfile.mkdtemp(prefix="instance-", dir=self.settings.job_root))
        (self.run_root / ".video-downloader-owned").touch(mode=0o600)
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def close(self) -> None:
        if self.cleanup_task:
            self.cleanup_task.cancel()
            await asyncio.gather(self.cleanup_task, return_exceptions=True)
        tasks = [job.task for job in self.jobs.values() if job.task and not job.task.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if self.run_root:
            shutil.rmtree(self.run_root, ignore_errors=True)

    def assert_capacity(self, count: int) -> None:
        active = sum(job.status in {"queued", "running"} for job in self.jobs.values())
        if count < 1 or active + count > self.settings.max_pending_jobs:
            raise PublicJobError(429, "La cola está llena. Espera a que terminen algunos trabajos.")
        if len(self.jobs) >= 200:
            self._prune_history()
            if len(self.jobs) >= 200:
                raise PublicJobError(429, "El historial temporal está lleno. Inténtalo más tarde.")

    def assert_storage_capacity(self) -> None:
        active_downloads = sum(
            job.kind == "download" and job.status in {"queued", "running"}
            for job in self.jobs.values()
        )
        active_directories = {
            job.directory.resolve()
            for job in self.jobs.values()
            if job.kind == "download" and job.status in {"queued", "running"} and job.directory
        }
        current = 0
        for path in self.settings.job_root.iterdir():
            if self.run_root and path == self.run_root:
                current += sum(
                    directory_size(job.directory)
                    for job in self.jobs.values()
                    if job.directory and job.directory.resolve() not in active_directories
                )
            else:
                current += directory_size(path)
        required = current + active_downloads * self.settings.max_file_bytes * 2
        required += self.settings.max_file_bytes * 2
        if required > self.settings.max_storage_bytes:
            raise PublicJobError(
                429, "El almacenamiento temporal está lleno. Espera a que caduquen archivos."
            )

    def submit_inspection(self, owner: str, url: str) -> Job:
        self.assert_capacity(1)
        job = self._new_job(owner, "inspect", "Analizando enlace")
        job.task = asyncio.create_task(self._execute(job, {"kind": "inspect", "url": url}))
        return job

    def submit_download(
        self,
        owner: str,
        source_id: str,
        video_id: str,
        output_format: str,
        resolution: int,
    ) -> Job:
        self.assert_capacity(1)
        source = self.get(owner, source_id)
        if source.kind != "inspect" or source.status != "completed" or not source.metadata:
            raise PublicJobError(409, "Primero analiza un video disponible.")
        video = next((item for item in source.metadata if item["id"] == video_id), None)
        if not video:
            raise PublicJobError(404, "Video no encontrado en el análisis.")
        if output_format not in {"mp4", "mp3"}:
            raise PublicJobError(400, "Formato no admitido.")
        if output_format == "mp4" and resolution not in video["resolutions"]:
            raise PublicJobError(400, "Esa calidad no está disponible para este video.")
        if output_format == "mp3" and resolution not in {360, 480, 720, 1080, 1440, 2160}:
            resolution = video["resolutions"][0] if video["resolutions"] else 360
        self.assert_storage_capacity()
        title = video["title"]
        job = self._new_job(owner, "download", title)
        request = {
            "kind": "download",
            "url": video["url"],
            "videoId": video["id"],
            "media": video,
            "format": output_format,
            "resolution": resolution,
        }
        job.task = asyncio.create_task(self._execute(job, request))
        return job

    def _new_job(self, owner: str, kind: str, title: str) -> Job:
        if not self.run_root:
            raise RuntimeError("El gestor de trabajos no está iniciado.")
        now = time.time()
        job = Job(uuid4().hex, owner, kind, title[:500], now, now)
        job.directory = Path(tempfile.mkdtemp(prefix=f"job-{job.id}-", dir=self.run_root))
        self.jobs[job.id] = job
        return job

    async def _execute(self, job: Job, request: dict[str, Any]) -> None:
        try:
            async with self.semaphore:
                job.status = "running"
                job.updated_at = time.time()

                def emit(event: dict[str, Any]) -> None:
                    job.updated_at = time.time()
                    if event["event"] == "metadata":
                        job.metadata = event["videos"]
                        job.title = event["videos"][0]["title"]
                    elif event["event"] == "progress":
                        job.progress = event["progress"]
                    elif event["event"] == "result":
                        job.file_path = Path(event["path"])
                        job.file_size = int(event["size"])

                assert job.directory
                await asyncio.wait_for(
                    self.runner.run(request, job.directory, emit),
                    timeout=self.settings.max_job_seconds,
                )
                job.updated_at = time.time()
                if job.kind == "inspect":
                    if not job.metadata:
                        raise EngineFailure("ENGINE")
                    job.status = "completed"
                else:
                    if not job.file_path or not job.file_path.is_file():
                        raise EngineFailure("ENGINE")
                    job.status = "completed"
                    job.expires_at = time.time() + self.settings.job_ttl_seconds
        except asyncio.CancelledError:
            job.status = "cancelled"
            job.error = ERROR_MESSAGES["CANCELLED"]
            job.updated_at = time.time()
            raise
        except TimeoutError:
            job.status = "failed"
            job.error = "El trabajo superó el tiempo máximo permitido."
            job.updated_at = time.time()
        except EngineFailure as error:
            job.status = "failed"
            job.error = ERROR_MESSAGES.get(error.code, ERROR_MESSAGES["ENGINE"])
            job.updated_at = time.time()
        except Exception:
            job.status = "failed"
            job.error = ERROR_MESSAGES["ENGINE"]
            job.updated_at = time.time()
        finally:
            if job.status != "completed" and job.directory:
                shutil.rmtree(job.directory, ignore_errors=True)
                job.directory = None

    def get(self, owner: str, job_id: str) -> Job:
        job = self.jobs.get(job_id)
        if not job or job.owner != owner:
            raise PublicJobError(404, "Trabajo no encontrado.")
        return job

    def list(self, owner: str) -> list[dict[str, Any]]:
        jobs = (job for job in self.jobs.values() if job.owner == owner)
        return [
            job.public()
            for job in sorted(jobs, key=lambda item: item.created_at, reverse=True)[:100]
        ]

    async def cancel(self, owner: str, job_id: str) -> Job:
        job = self.get(owner, job_id)
        if job.status not in {"queued", "running"}:
            raise PublicJobError(409, "El trabajo ya terminó.")
        if job.task and not job.task.done():
            job.task.cancel()
            await asyncio.gather(job.task, return_exceptions=True)
        return job

    async def _cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(min(30, self.settings.job_ttl_seconds))
            now = time.time()
            for job in self.jobs.values():
                if job.status == "completed" and job.expires_at and job.expires_at <= now:
                    if job.directory:
                        shutil.rmtree(job.directory, ignore_errors=True)
                    job.directory = None
                    job.file_path = None
                    job.file_size = None
                    job.status = "expired"
                    job.updated_at = now
            self._prune_history()

    def _prune_history(self) -> None:
        finished = sorted(
            (job for job in self.jobs.values() if job.status not in {"queued", "running"}),
            key=lambda item: item.created_at,
        )
        while len(self.jobs) >= 200 and finished:
            old = finished.pop(0)
            if old.directory:
                shutil.rmtree(old.directory, ignore_errors=True)
            self.jobs.pop(old.id, None)
