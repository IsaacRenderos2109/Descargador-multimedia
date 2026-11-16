import multiprocessing as mp
import os
import queue
import shutil
import signal
import subprocess
import threading
import time
from typing import Any

from PySide6.QtCore import QThread, Signal

from .models import Job
from .service import Cancelled, Downloader, check_cancel, diagnostics, explain_error


class DiagnosticsWorker(QThread):
    ready = Signal(str)
    failed = Signal(str)

    def run(self) -> None:
        try:
            self.ready.emit(diagnostics())
        except Exception as error:
            self.failed.emit(explain_error(error))


def download_process(job: Job, messages: Any) -> None:
    """Separate process lets cancellation stop yt-dlp AND its FFmpeg children."""
    if os.name != "nt":
        os.setsid()
    try:
        path = Downloader().download(
            job.media,
            job.options,
            threading.Event(),
            lambda progress: messages.put(("progress", progress)),
            work_token=job.id,
        )
        messages.put(("success", str(path)))
    except Exception as error:
        messages.put(("error", explain_error(error)))


def stop_process(process: Any) -> None:
    if not process.is_alive():
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                timeout=10,
                creationflags=0x08000000,
            )
        except (OSError, subprocess.TimeoutExpired):
            process.terminate()
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            process.terminate()
    process.join(timeout=3)
    if process.is_alive():
        if os.name != "nt":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.kill()
        process.join(timeout=3)


class DownloadWorker(QThread):
    progressed = Signal(object)
    succeeded = Signal(str)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, job: Job) -> None:
        super().__init__()
        self.job = job
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        context = mp.get_context("spawn")
        messages = context.Queue()
        process = context.Process(target=download_process, args=(self.job, messages))
        started = False
        succeeded = False
        try:
            check_cancel(self.cancel_event)
            process.start()
            started = True
            dead_since: float | None = None
            while True:
                check_cancel(self.cancel_event)
                try:
                    kind, payload = messages.get(timeout=0.1)
                except queue.Empty:
                    if not process.is_alive():
                        dead_since = dead_since or time.monotonic()
                        if time.monotonic() - dead_since > 1:
                            raise RuntimeError(
                                f"El proceso terminó sin resultado ({process.exitcode})."
                            ) from None
                    continue
                if kind == "progress":
                    self.progressed.emit(payload)
                elif kind == "success":
                    succeeded = True
                    self.succeeded.emit(payload)
                    break
                else:
                    self.failed.emit(payload)
                    break
        except Cancelled:
            self.cancelled.emit()
        except Exception as error:
            self.failed.emit(explain_error(error))
        finally:
            if started:
                stop_process(process)
            if not succeeded:
                folder = self.job.options.destination.expanduser().resolve() / (
                    f"VD-{self.job.media.id}-{self.job.id}"
                )
                # Names are generated internally. Never remove a destination or shared folder.
                import re

                if re.fullmatch(r"[0-9a-f]{32}", self.job.id):
                    shutil.rmtree(folder, ignore_errors=True)
            messages.close()
            messages.cancel_join_thread()


class InspectWorker(QThread):
    found = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, urls: list[str]) -> None:
        super().__init__()
        self.urls = urls
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        try:
            downloader = Downloader()
            media = []
            for url in self.urls:
                media.extend(downloader.inspect(url, self.cancel_event))
            check_cancel(self.cancel_event)
            self.found.emit(list({item.id: item for item in media}.values()))
        except Cancelled:
            self.cancelled.emit()
        except Exception as error:
            self.failed.emit(explain_error(error))


def smoke_child(messages: Any) -> None:
    """Verify bundled extractor/EJS imports and a frozen spawn roundtrip, offline."""
    from importlib.resources import files

    import yt_dlp
    import yt_dlp_ejs

    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as downloader:
        extractor = downloader.get_info_extractor("Youtube")
        scripts = files("yt_dlp_ejs").joinpath("yt", "solver")
        messages.put(
            bool(
                extractor
                and yt_dlp_ejs
                and scripts.joinpath("core.min.js").is_file()
                and scripts.joinpath("lib.min.js").is_file()
            )
        )
