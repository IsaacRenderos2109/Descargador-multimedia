import json
import os
import re
import shutil
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yt_dlp

from .models import DownloadOptions, Media, Progress
from .validation import VIDEO_ID, validate_url

RESOLUTIONS = (360, 480, 720, 1080, 1440, 2160)
MAX_PLAYLIST_ITEMS = 200


class DownloadError(RuntimeError):
    pass


class Cancelled(DownloadError):
    pass


def check_cancel(event: threading.Event) -> None:
    if event.is_set():
        raise Cancelled("Operación cancelada.")


def runtime_paths() -> tuple[str, str, dict[str, dict[str, str]]]:
    """Use app-adjacent tools first, then PATH. Never download binaries at runtime."""
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()
    bin_dir = base / "tools"

    def find(name: str) -> str | None:
        local = bin_dir / (name + (".exe" if os.name == "nt" else ""))
        return str(local) if local.is_file() else shutil.which(name)

    ffmpeg, ffprobe = find("ffmpeg"), find("ffprobe")
    if not ffmpeg or not ffprobe:
        raise DownloadError("Faltan FFmpeg/FFprobe. Instálalos en PATH o en la carpeta tools.")
    if Path(ffmpeg).parent.resolve() != Path(ffprobe).parent.resolve():
        raise DownloadError("FFmpeg y FFprobe deben estar en la misma carpeta.")
    deno, node = find("deno"), find("node")
    if deno:
        runtimes = {"deno": {"path": deno}}
    elif node:
        runtimes = {"node": {"path": node}}
    else:
        raise DownloadError("Falta un runtime JavaScript: instala Deno o Node.js compatible.")
    return ffmpeg, ffprobe, runtimes


def format_selector(options: DownloadOptions) -> str:
    height = options.resolution
    # No silent lower-resolution fallback. Re-encode through FFmpeg when codecs differ.
    return (
        f"bv[height={height}]+ba/b[height={height}]" if not options.audio_only else "bestaudio/best"
    )


def explain_error(error: Exception) -> str:
    message = str(error)
    lowered = message.lower()
    if "requested format" in lowered or "no video formats" in lowered:
        return "El formato solicitado ya no está disponible. Vuelve a analizar el enlace."
    if any(
        word in lowered for word in ("private", "sign in", "login", "members", "age-restricted")
    ):
        return "Contenido restringido o privado. No se intentará eludir el acceso."
    if any(word in lowered for word in ("429", "too many requests")):
        return "La plataforma limitó las solicitudes. Espera antes de volver a intentar."
    if any(word in lowered for word in ("timed out", "network", "resolve", "connection")):
        return "Error de red. Comprueba la conexión y vuelve a intentar."
    return message[:1200] or type(error).__name__


class Downloader:
    def __init__(self, factory: Callable[..., Any] = yt_dlp.YoutubeDL) -> None:
        self.factory = factory

    def _base(self) -> dict[str, Any]:
        ffmpeg, _, runtimes = runtime_paths()
        return {
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 15,
            "retries": 2,
            "fragment_retries": 2,
            "extractor_retries": 1,
            "ffmpeg_location": str(Path(ffmpeg).parent),
            "js_runtimes": runtimes,
            "windowsfilenames": True,
            "ignoreconfig": True,
            "allow_unplayable_formats": False,
            # EJS is supplied by yt-dlp[default]; no remote component execution opt-in.
        }

    def _media(self, data: dict[str, Any]) -> Media:
        if not VIDEO_ID.fullmatch(str(data.get("id", ""))):
            raise DownloadError("La plataforma devolvió un identificador inválido.")
        if data.get("is_live") or data.get("live_status") in {"is_live", "is_upcoming"}:
            raise DownloadError("Las emisiones en directo o futuras no están admitidas.")
        if data.get("availability") in {
            "private",
            "premium_only",
            "subscriber_only",
            "needs_auth",
            "unlisted",
        }:
            raise DownloadError("Solo se admite contenido público y sin restricciones de acceso.")
        formats = [f for f in data.get("formats", []) if not f.get("has_drm")]
        heights = {
            int(f["height"]) for f in formats if f.get("height") and f.get("vcodec") != "none"
        }
        if not formats:
            raise DownloadError("No hay formatos públicos disponibles sin DRM.")
        return Media(
            id=str(data["id"]),
            url=validate_url(data.get("webpage_url") or f"https://youtu.be/{data['id']}"),
            title=str(data.get("title") or data["id"]),
            duration=data.get("duration"),
            thumbnail=data.get("thumbnail"),
            resolutions=tuple(h for h in RESOLUTIONS if h in heights),
            formats=tuple(
                f"{f.get('format_id', '?')}: {f.get('ext', '?')} "
                f"{f.get('height') or 'audio'} "
                f"({f.get('vcodec', '?')}/{f.get('acodec', '?')})"
                for f in formats
            ),
        )

    def inspect(self, url: str, cancel: threading.Event) -> list[Media]:
        url = validate_url(url)
        check_cancel(cancel)
        options = self._base() | {"skip_download": True, "noplaylist": True}
        is_playlist = "/playlist?" in url
        if is_playlist:
            options.update(
                {
                    "extract_flat": "in_playlist",
                    "noplaylist": False,
                    "playlistend": MAX_PLAYLIST_ITEMS + 1,
                }
            )
        with self.factory(options) as ydl:
            data = ydl.extract_info(url, download=False)
        check_cancel(cancel)
        if not data:
            raise DownloadError("La plataforma no devolvió información.")
        if not is_playlist:
            return [self._media(data)]
        if data.get("availability") in {"private", "unlisted", "needs_auth"}:
            raise DownloadError("La lista debe ser pública.")
        entries = list(data.get("entries") or [])
        if (
            len(entries) > MAX_PLAYLIST_ITEMS
            or (data.get("playlist_count") or 0) > MAX_PLAYLIST_ITEMS
        ):
            raise DownloadError(
                f"La lista supera {MAX_PLAYLIST_ITEMS} elementos. Usa enlaces individuales."
            )
        if not entries:
            raise DownloadError("La lista está vacía o no es accesible.")
        result: list[Media] = []
        for entry in entries:
            check_cancel(cancel)
            if not entry or not entry.get("id"):
                raise DownloadError(
                    "La lista contiene elementos inaccesibles. Usa enlaces individuales."
                )
            result.extend(self.inspect(f"https://youtu.be/{entry['id']}", cancel))
        return list({media.id: media for media in result}.values())

    def download(
        self,
        media: Media,
        options: DownloadOptions,
        cancel: threading.Event,
        progress: Callable[[Progress], None],
        *,
        work_token: str | None = None,
    ) -> Path:
        check_cancel(cancel)
        validate_url(media.url)
        if not VIDEO_ID.fullmatch(media.id):
            raise DownloadError("Identificador de video inválido.")
        if not options.audio_only and options.resolution not in media.resolutions:
            raise DownloadError("La resolución seleccionada no está disponible para este video.")
        destination = options.destination.expanduser().resolve()
        destination.mkdir(parents=True, exist_ok=True)
        # Full-path headroom for Windows MAX_PATH and long Unicode titles.
        if os.name == "nt" and len(str(destination)) > 120:
            raise DownloadError("Elige una carpeta con una ruta de menos de 120 caracteres.")
        final_paths: list[str] = []

        def hook(data: dict[str, Any]) -> None:
            check_cancel(cancel)
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            downloaded = data.get("downloaded_bytes", 0)
            progress(
                Progress(
                    percent=min(100.0, downloaded / total * 100) if total else None,
                    downloaded=downloaded,
                    total=total,
                    speed=data.get("speed"),
                    eta=data.get("eta"),
                    phase="Procesando con FFmpeg"
                    if data.get("status") == "finished"
                    else "Descargando",
                )
            )

        def post_hook(data: dict[str, Any]) -> None:
            check_cancel(cancel)
            progress(Progress(phase="Procesando con FFmpeg"))
            info = data.get("info_dict") or {}
            if info.get("filepath"):
                final_paths.append(str(info["filepath"]))

        # Unique job directory avoids overwriting existing media and isolates cancellation debris.
        import uuid

        token = work_token or uuid.uuid4().hex
        if re.fullmatch(r"[0-9a-f]{32}", token) is None:
            raise DownloadError("Identificador de descarga inválido.")
        work = destination / f"VD-{media.id}-{token}"
        work.mkdir()
        completed = False
        try:
            config = self._base() | {
                "noplaylist": True,
                "format": format_selector(options),
                "outtmpl": str(work / "%(title).48B [%(id)s].%(ext)s"),
                "restrictfilenames": False,
                "overwrites": False,
                "progress_hooks": [hook],
                "postprocessor_hooks": [post_hook],
                "post_hooks": [final_paths.append],
            }
            if options.audio_only:
                config["postprocessors"] = [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ]
            else:
                config.update(
                    {
                        "merge_output_format": "mp4",
                        "postprocessors": [
                            {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}
                        ],
                        "postprocessor_args": {
                            "VideoConvertor+ffmpeg_o": [
                                "-c:v",
                                "libx264",
                                "-preset",
                                "fast",
                                "-crf",
                                "20",
                                "-c:a",
                                "aac",
                                "-movflags",
                                "+faststart",
                            ]
                        },
                    }
                )
            with self.factory(config) as ydl:
                ydl.extract_info(media.url, download=True)
            check_cancel(cancel)
            extension = ".mp3" if options.audio_only else ".mp4"
            candidates = [Path(p) for p in final_paths if Path(p).suffix.lower() == extension]
            candidates.extend(work.glob(f"*{extension}"))
            output = next(
                (
                    p.resolve()
                    for p in reversed(candidates)
                    if p.is_file() and p.stat().st_size > 0 and p.resolve().parent == work.resolve()
                ),
                None,
            )
            if output is None:
                raise DownloadError("No se encontró el archivo final esperado.")
            completed = True
            return output
        except Exception as error:
            if cancel.is_set():
                raise Cancelled("Descarga cancelada.") from error
            raise DownloadError(explain_error(error)) from error
        finally:
            if not completed:
                shutil.rmtree(work, ignore_errors=True)


def diagnostics() -> str:
    ffmpeg, ffprobe, runtimes = runtime_paths()
    result: dict[str, str] = {}
    for name, executable in {
        "ffmpeg": ffmpeg,
        "ffprobe": ffprobe,
        **{k: v["path"] for k, v in runtimes.items()},
    }.items():
        command = [executable, "-version" if name in {"ffmpeg", "ffprobe"} else "--version"]
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=0x08000000 if os.name == "nt" else 0,
        )
        if process.returncode:
            raise DownloadError(f"No se puede ejecutar {name}.")
        result[name] = process.stdout.splitlines()[0]
        if name in {"node", "deno"}:
            version = re.search(r"(\d+)\.(\d+)\.(\d+)", result[name])
            minimum = (22, 0, 0) if name == "node" else (2, 3, 0)
            if not version or tuple(map(int, version.groups())) < minimum:
                raise DownloadError(f"Actualiza {name}; versión mínima: {minimum}.")
    return json.dumps(result, ensure_ascii=False, indent=2)
