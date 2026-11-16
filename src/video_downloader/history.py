import csv
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from .models import Job


class History:
    """Short-lived connections are safe across GUI and worker threads."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                """CREATE TABLE IF NOT EXISTS downloads (
                job_id TEXT PRIMARY KEY, finished_at TEXT NOT NULL,
                title TEXT NOT NULL, url TEXT NOT NULL, format TEXT NOT NULL,
                status TEXT NOT NULL, path TEXT NOT NULL, error TEXT NOT NULL)"""
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def record(self, job: Job) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO downloads VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    job.id,
                    datetime.now(UTC).isoformat(),
                    job.media.title,
                    job.media.url,
                    "MP3" if job.options.audio_only else f"MP4 {job.options.resolution}p",
                    str(job.status),
                    job.path,
                    job.message,
                ),
            )

    def rows(self, limit: int = 1000) -> list[dict[str, str]]:
        with self._connect() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM downloads ORDER BY finished_at DESC LIMIT ?", (limit,)
                )
            ]

    def export_csv(self, destination: Path) -> None:
        columns = ["job_id", "finished_at", "title", "url", "format", "status", "path", "error"]
        with destination.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            for row in self.rows(limit=1_000_000):
                # Spreadsheet formula injection protection for untrusted video titles.
                writer.writerow(
                    {
                        k: "'" + v if v.startswith(("=", "+", "-", "@", "\t", "\r")) else v
                        for k, v in row.items()
                    }
                )
