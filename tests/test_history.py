import csv
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from video_downloader.history import History
from video_downloader.models import Status


def test_persistent_terminal_states_and_idempotency(tmp_path, job):
    path = tmp_path / "state/history.sqlite3"
    history = History(path)
    job.status = Status.COMPLETED
    job.path = str(tmp_path / "a 日本語.mp4")
    history.record(job)
    history.record(job)
    rows = History(path).rows()
    assert len(rows) == 1
    assert rows[0]["status"] == "Completada" and rows[0]["path"] == job.path


def test_parallel_writes_and_export(tmp_path, job):
    history = History(tmp_path / "h.sqlite3")
    jobs = [
        replace(job, id=str(n), media=replace(job.media, title="=HYPERLINK(test)"))
        for n in range(10)
    ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(history.record, jobs))
    output = tmp_path / "history.csv"
    history.export_csv(output)
    with output.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 10
    assert rows[0]["title"].startswith("'=")
    assert len(history.rows(limit=3)) == 3
