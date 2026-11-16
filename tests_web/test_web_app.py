from __future__ import annotations

import asyncio
import re
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from web_service.app import create_app
from web_service.config import Settings
from web_service.manager import JobManager, PublicJobError


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        access_code="a-long-test-access-code-123456",
        session_secret="a-session-signing-secret-long-enough-for-tests-123",
        public_base_url="http://testserver",
        cookie_secure=False,
        google_sites_origins=("https://sites.google.com",),
        allowed_hosts=("testserver",),
        media_proxy="http://127.0.0.1:3128",
        job_root=tmp_path / "jobs",
        max_file_bytes=10485760,
        max_storage_bytes=67108864,
        max_job_seconds=10,
        max_media_seconds=1800,
        max_concurrent_jobs=1,
        max_pending_jobs=8,
        job_ttl_seconds=600,
        session_ttl_seconds=3600,
    )


class FakeRunner:
    def __init__(self) -> None:
        self.started: set[str] = set()

    async def run(self, request: dict[str, Any], directory: Path, emit: Any) -> dict[str, Any]:
        if request["kind"] == "inspect":
            video_id = re.search(r"v=([A-Za-z0-9_-]{11})", request["url"])
            assert video_id
            identifier = video_id.group(1)
            emit(
                {
                    "event": "metadata",
                    "videos": [
                        {
                            "id": identifier,
                            "url": request["url"],
                            "title": f"Video sintético {identifier}",
                            "duration": 1,
                            "thumbnail": None,
                            "resolutions": [360, 720],
                            "formats": ["test: mp4", "test: audio"],
                        }
                    ],
                }
            )
        else:
            output_format = request["format"]
            output = directory / f"synthetic.{output_format}"
            output.write_bytes(b"synthetic-media-content")
            emit({"event": "result", "path": str(output), "size": output.stat().st_size})
        await asyncio.sleep(0)
        return {"ok": True}


def post_headers() -> dict[str, str]:
    return {"Origin": "http://testserver"}


def login(client: TestClient) -> None:
    result = client.post(
        "/api/login", headers=post_headers(), json={"code": "a-long-test-access-code-123456"}
    )
    assert result.status_code == 200


def wait_for(client: TestClient, job_id: str, status: str) -> dict[str, Any]:
    for _ in range(100):
        result = client.get(f"/api/jobs/{job_id}")
        assert result.status_code == 200
        if result.json()["status"] == status:
            return result.json()
        time.sleep(0.01)
    raise AssertionError(f"job {job_id} did not reach {status}")


def test_google_sites_headers_and_static_page(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path), FakeRunner())
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert 'lang="es"' in response.text
        assert "Content-Security-Policy" in response.headers
        assert "https://sites.google.com" in response.headers["content-security-policy"]
        assert "x-frame-options" not in response.headers
        assert response.headers["cache-control"] == "private, no-store"


def test_access_code_url_validation_and_authorized_job_file_isolation(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    app = create_app(settings, FakeRunner())
    with TestClient(app) as client, TestClient(app) as other:
        assert client.get("/api/jobs").status_code == 401
        bad = client.post(
            "/api/login", headers=post_headers(), json={"code": "incorrect-access-code"}
        )
        assert bad.status_code == 401
        login(client)
        assert client.get("/api/session").json() == {"authenticated": True}

        rejected = client.post(
            "/api/analyze",
            headers=post_headers(),
            json={
                "urls": ["https://youtube.com.attacker.example/watch?v=abcdefghijk"],
                "authorized": True,
            },
        )
        assert rejected.status_code == 400
        unconsented = client.post(
            "/api/analyze",
            headers=post_headers(),
            json={"urls": ["https://youtu.be/abcdefghijk"], "authorized": False},
        )
        assert unconsented.status_code == 400

        result = client.post(
            "/api/analyze",
            headers=post_headers(),
            json={
                "urls": ["https://youtu.be/abcdefghijk", "https://youtube.com/watch?v=lmnopqrstuv"],
                "authorized": True,
            },
        )
        assert result.status_code == 200
        job_ids = result.json()["job_ids"]
        assert len(job_ids) == 2
        inspected = wait_for(client, job_ids[0], "completed")
        video = inspected["metadata"][0]

        assert (
            other.post(
                "/api/login",
                headers=post_headers(),
                json={"code": "a-long-test-access-code-123456"},
            ).status_code
            == 200
        )
        assert other.get(f"/api/jobs/{job_ids[0]}").status_code == 404

        queued = client.post(
            f"/api/jobs/{job_ids[0]}/download",
            headers=post_headers(),
            json={
                "source_id": job_ids[0],
                "video_id": video["id"],
                "format": "mp4",
                "resolution": 360,
                "authorized": True,
            },
        )
        assert queued.status_code == 200
        download_id = queued.json()["job_id"]
        wait_for(client, download_id, "completed")
        file = client.get(f"/api/jobs/{download_id}/file")
        assert file.status_code == 200
        assert file.content == b"synthetic-media-content"
        assert file.headers["content-type"] == "video/mp4"
        assert "attachment" in file.headers["content-disposition"]
        assert other.get(f"/api/jobs/{download_id}/file").status_code == 404


class SlowRunner:
    async def run(self, request: dict[str, Any], directory: Path, emit: Any) -> dict[str, Any]:
        await asyncio.sleep(30)
        return {"ok": True}


def test_cancel_terminates_owned_job(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path), SlowRunner())
    with TestClient(app) as client:
        login(client)
        result = client.post(
            "/api/analyze",
            headers=post_headers(),
            json={"urls": ["https://youtu.be/abcdefghijk"], "authorized": True},
        )
        job_id = result.json()["job_ids"][0]
        for _ in range(100):
            status = client.get(f"/api/jobs/{job_id}").json()["status"]
            if status == "running":
                break
            time.sleep(0.01)
        cancelled = client.delete(f"/api/jobs/{job_id}", headers=post_headers())
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"
        assert client.get(f"/api/jobs/{job_id}").json()["status"] == "cancelled"


def test_api_to_ffmpeg_synthetic_download_uses_isolated_worker(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setenv("MEDIA_ENGINE_MODE", "synthetic")
    monkeypatch.setenv("ALLOW_SYNTHETIC_TESTS", "1")
    app = create_app(make_settings(tmp_path))
    with TestClient(app) as client:
        login(client)
        analysis = client.post(
            "/api/analyze",
            headers=post_headers(),
            json={"urls": ["https://youtu.be/abcdefghijk"], "authorized": True},
        )
        assert analysis.status_code == 200
        source_id = analysis.json()["job_ids"][0]
        metadata = wait_for(client, source_id, "completed")["metadata"][0]
        download = client.post(
            f"/api/jobs/{source_id}/download",
            headers=post_headers(),
            json={
                "source_id": source_id,
                "video_id": metadata["id"],
                "format": "mp3",
                "resolution": 360,
                "authorized": True,
            },
        )
        assert download.status_code == 200
        job_id = download.json()["job_id"]
        wait_for(client, job_id, "completed")
        file = client.get(f"/api/jobs/{job_id}/file")
        assert file.status_code == 200
        assert file.headers["content-type"] == "audio/mpeg"
        assert file.content.startswith(b"ID3")


def test_temporary_storage_limit_counts_completed_files(tmp_path: Path) -> None:
    async def exercise() -> None:
        manager = JobManager(make_settings(tmp_path))
        await manager.start()
        try:
            job = manager._new_job("owner", "download", "Archivo existente")
            assert job.directory
            job.status = "completed"
            with (job.directory / "large.mp4").open("wb") as media:
                media.truncate(45 * 1024 * 1024)
            with pytest.raises(PublicJobError, match="almacenamiento temporal"):
                manager.assert_storage_capacity()
        finally:
            await manager.close()

    asyncio.run(exercise())
