"""
Intake job API: isolated DB/storage, mocked BAML pipeline.
"""

from __future__ import annotations

import io
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def intake_client(tmp_path, monkeypatch):
    monkeypatch.setattr("app.db.EXTRACTION_DB_PATH", tmp_path / "intake_test.db")
    monkeypatch.setattr("app.config.EXTRACTION_DB_PATH", tmp_path / "intake_test.db")
    monkeypatch.setattr("app.config.INTAKE_STORAGE_DIR", tmp_path / "intake_store")
    monkeypatch.setattr("app.config.INTAKE_SIGNING_SECRET", "test-secret")
    monkeypatch.setattr("app.config.INTAKE_RETENTION_DAYS", "3650")
    from app.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_google_api_key():
    with patch("app.main.GOOGLE_API_KEY", "test-key"), patch("app.intake.router.GOOGLE_API_KEY", "test-key"):
        yield


@pytest.fixture
def mock_intake_pipeline():
    async def _fake(job_id: str) -> None:
        from app.intake import repo, storage
        from app.intake.provenance import merged_to_field_assertions
        from app.preview_fill import normalize_merged_extracted

        merged = {
            "passport": {"first_name": "Test", "last_name": "User"},
            "attorney": {"family_name": "Law", "email": "a@example.com"},
        }
        norm = normalize_merged_extracted(merged)
        repo.replace_baml_assertions(job_id, merged_to_field_assertions(norm))
        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
            b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n"
            b"-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        rel = f"{job_id}/pages/passport-0.png"
        storage.write_bytes(rel, png)
        h = storage.sha256_bytes(png)
        repo.insert_artifact(
            job_id,
            kind="page_image",
            role="passport",
            page_index=0,
            rel_path=rel,
            content_type="image/png",
            byte_size=len(png),
            sha256=h,
        )
        repo.update_job(
            job_id,
            status="completed",
            stage="completed",
            error_message="",
            result_json=json.dumps(norm, ensure_ascii=False),
        )
        repo.log_audit(job_id, "completed", {"field_count": 4})

    with patch("app.intake.router.run_intake_pipeline", new=_fake):
        yield


def test_intake_jobs_requires_api_key(intake_client):
    with patch("app.intake.router.GOOGLE_API_KEY", ""):
        r = intake_client.post("/intake/jobs", files={"passport": ("p.pdf", io.BytesIO(b"x"), "application/pdf")})
    assert r.status_code == 503


def test_intake_jobs_no_files(intake_client, mock_google_api_key):
    r = intake_client.post("/intake/jobs")
    assert r.status_code == 400


def test_intake_job_happy_path(intake_client, mock_google_api_key, mock_intake_pipeline):
    r = intake_client.post(
        "/intake/jobs",
        files={"passport": ("p.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )
    assert r.status_code == 201
    job_id = r.json()["id"]

    g = intake_client.get(f"/intake/jobs/{job_id}")
    assert g.status_code == 200
    body = g.json()
    assert body["status"] == "completed"
    assert body.get("extracted", {}).get("passport", {}).get("first_name") == "Test"

    f = intake_client.get(f"/intake/jobs/{job_id}/fields")
    assert f.status_code == 200
    paths = {a["field_path"] for a in f.json()["assertions"]}
    assert "passport.first_name" in paths

    p = intake_client.patch(
        f"/intake/jobs/{job_id}/fields",
        json={"patches": [{"field_path": "passport.first_name", "value": "Overridden", "reviewer_note": "typo"}]},
    )
    assert p.status_code == 200
    names = {a["field_path"]: a for a in p.json()["assertions"]}
    assert names["passport.first_name"]["source"] == "human_override"
    assert json.loads(names["passport.first_name"]["value_json"]) == "Overridden"

    pr = intake_client.post(f"/intake/jobs/{job_id}/promote-to-session", json={"title": "From intake"})
    assert pr.status_code == 201
    sid = pr.json()["session_id"]
    assert sid and len(sid) == 32
    assert "readiness" in pr.json()


def test_intake_artifact_download_signed(intake_client, mock_google_api_key, mock_intake_pipeline):
    r = intake_client.post(
        "/intake/jobs",
        files={"passport": ("x.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")},
    )
    job_id = r.json()["id"]
    g = intake_client.get(f"/intake/jobs/{job_id}")
    links = g.json().get("page_image_links") or []
    assert links, "expected at least one rendered page link"
    path = links[0]["path"]
    assert path.startswith(f"/intake/jobs/{job_id}/artifacts/")
    dl = intake_client.get(path)
    assert dl.status_code == 200


def test_intake_artifact_download_bad_sig(intake_client, mock_google_api_key, mock_intake_pipeline):
    r = intake_client.post(
        "/intake/jobs",
        files={"passport": ("x.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")},
    )
    job_id = r.json()["id"]
    g = intake_client.get(f"/intake/jobs/{job_id}")
    aid = (g.json().get("page_image_links") or [{}])[0].get("artifact_id", 1)
    bad = intake_client.get(f"/intake/jobs/{job_id}/artifacts/{aid}/file?exp=9999999999&sig=bad")
    assert bad.status_code == 403
