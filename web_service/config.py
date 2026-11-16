from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


def _integer(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as error:
        raise RuntimeError(f"{name} debe ser un entero.") from error
    if not minimum <= value <= maximum:
        raise RuntimeError(f"{name} debe estar entre {minimum} y {maximum}.")
    return value


def _origins(value: str) -> tuple[str, ...]:
    result: list[str] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        parsed = urlsplit(item)
        if parsed.scheme != "https" or not parsed.netloc or parsed.path not in {"", "/"}:
            raise RuntimeError("GOOGLE_SITES_ORIGINS solo admite orígenes HTTPS.")
        result.append(f"https://{parsed.netloc.lower()}")
    if not result:
        raise RuntimeError("Configura al menos un origen de Google Sites.")
    return tuple(dict.fromkeys(result))


@dataclass(frozen=True, slots=True)
class Settings:
    access_code: str
    session_secret: str
    public_base_url: str
    cookie_secure: bool
    google_sites_origins: tuple[str, ...]
    allowed_hosts: tuple[str, ...]
    media_proxy: str
    job_root: Path
    max_file_bytes: int
    max_storage_bytes: int
    max_job_seconds: int
    max_media_seconds: int
    max_concurrent_jobs: int
    max_pending_jobs: int
    job_ttl_seconds: int
    session_ttl_seconds: int

    @classmethod
    def from_env(cls) -> Settings:
        access_code = os.getenv("ACCESS_CODE", "")
        session_secret = os.getenv("SESSION_SECRET", "")
        base = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        parsed_base = urlsplit(base)
        if len(access_code) < 16:
            raise RuntimeError("ACCESS_CODE debe tener al menos 16 caracteres aleatorios.")
        if len(session_secret) < 32:
            raise RuntimeError("SESSION_SECRET debe tener al menos 32 caracteres aleatorios.")
        if (
            parsed_base.scheme not in {"http", "https"}
            or not parsed_base.hostname
            or parsed_base.username
            or parsed_base.password
            or parsed_base.path
            or parsed_base.query
            or parsed_base.fragment
        ):
            raise RuntimeError("PUBLIC_BASE_URL debe ser el origen público del servicio.")
        cookie_secure = os.getenv("COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
        if parsed_base.scheme == "https" and not cookie_secure:
            raise RuntimeError("Activa COOKIE_SECURE al publicar con HTTPS.")
        proxy = os.getenv("MEDIA_PROXY", "")
        if not proxy or urlsplit(proxy).scheme != "http" or not urlsplit(proxy).hostname:
            raise RuntimeError("MEDIA_PROXY debe apuntar al proxy HTTPS de salida.")
        hosts = tuple(
            dict.fromkeys(
                item.strip().lower()
                for item in os.getenv(
                    "ALLOWED_HOSTS", f"{parsed_base.hostname},localhost,127.0.0.1"
                ).split(",")
                if item.strip()
            )
        )
        max_file_bytes = _integer("MAX_FILE_BYTES", 104857600, 1048576, 1073741824)
        max_concurrent_jobs = _integer("MAX_CONCURRENT_JOBS", 1, 1, 4)
        max_storage_bytes = _integer("MAX_STORAGE_BYTES", 1073741824, 2097152, 10737418240)
        if max_storage_bytes < max_file_bytes * 2 * max_concurrent_jobs:
            raise RuntimeError(
                "MAX_STORAGE_BYTES debe cubrir dos veces MAX_FILE_BYTES por trabajo simultáneo."
            )
        return cls(
            access_code=access_code,
            session_secret=session_secret,
            public_base_url=f"{parsed_base.scheme}://{parsed_base.netloc}",
            cookie_secure=cookie_secure,
            google_sites_origins=_origins(
                os.getenv("GOOGLE_SITES_ORIGINS", "https://sites.google.com")
            ),
            allowed_hosts=hosts,
            media_proxy=proxy,
            job_root=Path(os.getenv("JOB_ROOT", "/data/jobs")).resolve(),
            max_file_bytes=max_file_bytes,
            max_storage_bytes=max_storage_bytes,
            max_job_seconds=_integer("MAX_JOB_SECONDS", 600, 30, 1800),
            max_media_seconds=_integer("MAX_MEDIA_SECONDS", 1800, 1, 14400),
            max_concurrent_jobs=max_concurrent_jobs,
            max_pending_jobs=_integer("MAX_PENDING_JOBS", 8, 1, 40),
            job_ttl_seconds=_integer("JOB_TTL_SECONDS", 3600, 60, 86400),
            session_ttl_seconds=_integer("SESSION_TTL_SECONDS", 43200, 300, 604800),
        )
