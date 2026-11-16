from __future__ import annotations

import hmac
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from video_downloader.validation import ValidationError as YouTubeValidationError
from video_downloader.validation import validate_url

from .config import Settings
from .manager import JobManager, PublicJobError, Runner

STATIC = Path(__file__).with_name("static")


class LoginBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=16, max_length=256)


class AnalyzeBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    urls: list[str] = Field(min_length=1, max_length=20)
    authorized: StrictBool


class DownloadBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str = Field(min_length=32, max_length=32, pattern=r"^[0-9a-f]{32}$")
    video_id: str = Field(min_length=11, max_length=11, pattern=r"^[A-Za-z0-9_-]{11}$")
    format: Literal["mp4", "mp3"]
    resolution: int = Field(ge=360, le=2160)
    authorized: StrictBool


async def read_body(request: Request, model: type[BaseModel]) -> BaseModel:
    length = request.headers.get("content-length")
    if length and (not length.isdecimal() or int(length) > 8192):
        raise HTTPException(413, "Solicitud demasiado grande.")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 8192:
            raise HTTPException(413, "Solicitud demasiado grande.")
    try:
        return model.model_validate_json(bytes(data))
    except (ValidationError, ValueError) as error:
        raise HTTPException(400, "Revisa los datos enviados.") from error


def ensure_origin(request: Request, settings: Settings) -> None:
    origin = request.headers.get("origin")
    if not origin or origin.rstrip("/") != settings.public_base_url:
        raise HTTPException(403, "Origen no permitido.")


def owner_for(request: Request, settings: Settings) -> str:
    session = request.session
    owner = session.get("owner")
    issued = session.get("issued")
    if (
        session.get("authenticated") is not True
        or not isinstance(owner, str)
        or len(owner) != 32
        or not isinstance(issued, int)
        or time.time() - issued > settings.session_ttl_seconds
    ):
        session.clear()
        raise HTTPException(401, "Inicia sesión para continuar.")
    return owner


def rate_limit(request: Request, key: str, limit: int = 20, window: int = 60) -> None:
    now = time.monotonic()
    buckets: dict[str, list[float]] = request.app.state.rate_buckets
    events = [timestamp for timestamp in buckets.get(key, []) if now - timestamp < window]
    if len(events) >= limit:
        buckets[key] = events
        raise HTTPException(429, "Demasiadas solicitudes. Espera un momento.")
    if key not in buckets and len(buckets) >= 10000:
        for name, values in list(buckets.items()):
            if not values or now - values[-1] >= window:
                buckets.pop(name, None)
        if len(buckets) >= 10000:
            raise HTTPException(429, "Demasiadas sesiones activas. Inténtalo más tarde.")
    events.append(now)
    buckets[key] = events
    if len(buckets) > 10000:
        for item in [
            name for name, values in buckets.items() if not values or now - values[-1] >= window
        ]:
            buckets.pop(item, None)


def create_app(settings: Settings, runner: Runner | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        manager = JobManager(settings, runner)
        await manager.start()
        app.state.settings = settings
        app.state.manager = manager
        app.state.rate_buckets = {}
        app.state.login_buckets = {}
        try:
            yield
        finally:
            await manager.close()

    app = FastAPI(
        title="Video Downloader",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie="video_downloader_session",
        max_age=settings.session_ttl_seconds,
        same_site="none" if settings.cookie_secure else "lax",
        https_only=settings.cookie_secure,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts))

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any):
        response = await call_next(request)
        ancestors = " ".join(("'self'", *settings.google_sites_origins))
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data: https://*.ytimg.com; connect-src 'self'; "
            f"frame-ancestors {ancestors}; object-src 'none'; base-uri 'self'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "private, no-store"
        if urlsplit(settings.public_base_url).scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        # Do not set X-Frame-Options: CSP frame-ancestors permits the configured Sites origins.
        return response

    @app.exception_handler(PublicJobError)
    async def public_job_error(_: Request, error: PublicJobError) -> JSONResponse:
        return JSONResponse({"error": error.message}, status_code=error.status)

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(STATIC / "index.html", media_type="text/html; charset=utf-8")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/session")
    async def session(request: Request) -> dict[str, bool]:
        try:
            owner_for(request, settings)
            return {"authenticated": True}
        except HTTPException:
            return {"authenticated": False}

    @app.post("/api/login")
    async def login(request: Request) -> dict[str, bool]:
        ensure_origin(request, settings)
        body = await read_body(request, LoginBody)
        assert isinstance(body, LoginBody)
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        attempts: dict[str, list[float]] = request.app.state.login_buckets
        if client not in attempts and len(attempts) >= 10000:
            for address, values in list(attempts.items()):
                if not values or now - values[-1] >= 300:
                    attempts.pop(address, None)
            if len(attempts) >= 10000:
                raise HTTPException(429, "Demasiados intentos. Espera cinco minutos.")
        history = [value for value in attempts.get(client, []) if now - value < 300]
        if len(history) >= 10:
            attempts[client] = history
            raise HTTPException(429, "Demasiados intentos. Espera cinco minutos.")
        if not hmac.compare_digest(body.code.encode(), settings.access_code.encode()):
            history.append(now)
            attempts[client] = history
            raise HTTPException(401, "Código de acceso incorrecto.")
        attempts.pop(client, None)
        request.session.clear()
        request.session.update(
            {"authenticated": True, "owner": os.urandom(16).hex(), "issued": int(time.time())}
        )
        return {"authenticated": True}

    @app.post("/api/logout")
    async def logout(request: Request) -> dict[str, bool]:
        ensure_origin(request, settings)
        request.session.clear()
        return {"authenticated": False}

    @app.get("/api/jobs")
    async def jobs(request: Request) -> list[dict[str, Any]]:
        owner = owner_for(request, settings)
        return request.app.state.manager.list(owner)

    @app.get("/api/jobs/{job_id}")
    async def get_job(job_id: str, request: Request) -> dict[str, Any]:
        owner = owner_for(request, settings)
        return request.app.state.manager.get(owner, job_id).public()

    @app.post("/api/analyze")
    async def analyze(request: Request) -> dict[str, list[str]]:
        ensure_origin(request, settings)
        owner = owner_for(request, settings)
        rate_limit(request, f"analyze:{owner}")
        body = await read_body(request, AnalyzeBody)
        assert isinstance(body, AnalyzeBody)
        if body.authorized is not True:
            raise HTTPException(
                400, "Confirma que tienes autorización para procesar estos enlaces."
            )
        normalized: list[str] = []
        for value in body.urls:
            if urlsplit(value.strip()).scheme != "https":
                raise HTTPException(400, "Utiliza enlaces HTTPS de YouTube.")
            try:
                url = validate_url(value)
            except YouTubeValidationError as error:
                raise HTTPException(400, "Solo se admiten enlaces públicos de YouTube.") from error
            if urlsplit(url).path == "/playlist":
                raise HTTPException(400, "En esta versión pega enlaces individuales, no listas.")
            normalized.append(url)
        unique = list(dict.fromkeys(normalized))
        request.app.state.manager.assert_capacity(len(unique))
        ids = [request.app.state.manager.submit_inspection(owner, url).id for url in unique]
        return {"job_ids": ids}

    @app.post("/api/jobs/{job_id}/download")
    async def download(job_id: str, request: Request) -> dict[str, str]:
        ensure_origin(request, settings)
        owner = owner_for(request, settings)
        rate_limit(request, f"download:{owner}")
        body = await read_body(request, DownloadBody)
        assert isinstance(body, DownloadBody)
        if body.authorized is not True:
            raise HTTPException(
                400, "Confirma que tienes autorización para descargar este contenido."
            )
        if body.source_id != job_id:
            raise HTTPException(400, "El análisis indicado no coincide.")
        job = request.app.state.manager.submit_download(
            owner,
            body.source_id,
            body.video_id,
            body.format,
            body.resolution,
        )
        return {"job_id": job.id}

    @app.delete("/api/jobs/{job_id}")
    async def cancel(job_id: str, request: Request) -> dict[str, str]:
        ensure_origin(request, settings)
        owner = owner_for(request, settings)
        job = await request.app.state.manager.cancel(owner, job_id)
        return {"status": job.status}

    @app.get("/api/jobs/{job_id}/file")
    async def file(job_id: str, request: Request) -> FileResponse:
        owner = owner_for(request, settings)
        job = request.app.state.manager.get(owner, job_id)
        if job.status != "completed" or not job.file_path or not job.file_path.is_file():
            raise HTTPException(404, "Archivo no disponible o caducado.")
        extension = ".mp3" if job.file_path.suffix.lower() == ".mp3" else ".mp4"
        media_type = "audio/mpeg" if extension == ".mp3" else "video/mp4"
        return FileResponse(
            job.file_path,
            media_type=media_type,
            filename=f"VideoDownloader-{job.id}{extension}",
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )

    return app
