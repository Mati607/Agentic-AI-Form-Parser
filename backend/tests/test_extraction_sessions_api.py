"""HTTP tests for /extraction-sessions and /preview-fill."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app


@pytest.fixture
def session_client(tmp_path, monkeypatch):
    db_path = tmp_path / "api_sessions.db"
    monkeypatch.setattr("app.db.get_db_path", lambda: db_path)
    init_db()
    with TestClient(app) as client:
        yield client


def test_preview_fill_endpoint(session_client):
    r = session_client.post(
        "/preview-fill",
        json={"passport": {"first_name": "Zoe"}, "attorney": {"city": "Boston"}},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["stats"]["mapped_with_value"] >= 2
    ids = {row["field_id"] for row in data["rows"] if row["would_attempt_fill"]}
    assert "passport.first_name" in ids
    assert "attorney.city" in ids


def test_create_and_get_session(session_client):
    body = {
        "extracted": {"passport": {"last_name": "Lee"}, "attorney": {}},
        "title": "My run",
        "passport_filename": "scan.pdf",
    }
    c = session_client.post("/extraction-sessions", json=body)
    assert c.status_code == 201
    created = c.json()
    assert "readiness" in created
    assert "score" in created["readiness"]
    sid = created["id"]
    g = session_client.get(f"/extraction-sessions/{sid}")
    assert g.status_code == 200
    assert g.json()["title"] == "My run"
    assert g.json()["extracted"]["passport"]["last_name"] == "Lee"


def test_list_sessions(session_client):
    session_client.post(
        "/extraction-sessions",
        json={"extracted": {"passport": {}, "attorney": {"email": "a@b.c"}}},
    )
    r = session_client.get("/extraction-sessions?limit=10&offset=0")
    assert r.status_code == 200
    payload = r.json()
    assert payload["total"] >= 1
    assert payload["items"][0]["field_counts"]["attorney"] >= 1


def test_patch_and_delete_session(session_client):
    sid = session_client.post(
        "/extraction-sessions",
        json={"extracted": {"passport": {}, "attorney": {}}},
    ).json()["id"]
    p = session_client.patch(
        f"/extraction-sessions/{sid}",
        json={"title": "Updated", "notes": "Hello"},
    )
    assert p.status_code == 200
    assert p.json()["title"] == "Updated"
    d = session_client.delete(f"/extraction-sessions/{sid}")
    assert d.status_code == 204
    assert session_client.get(f"/extraction-sessions/{sid}").status_code == 404


def test_export_session(session_client):
    sid = session_client.post(
        "/extraction-sessions",
        json={"extracted": {"passport": {"sex": "F"}, "attorney": {}}},
    ).json()["id"]
    r = session_client.get(f"/extraction-sessions/{sid}/export")
    assert r.status_code == 200
    assert "attachment" in r.headers.get("content-disposition", "")
    obj = json.loads(r.text)
    assert obj["extracted"]["passport"]["sex"] == "F"


def test_fill_from_session_persists_summary(session_client):
    sid = session_client.post(
        "/extraction-sessions",
        json={"extracted": {"passport": {"first_name": "Pat"}, "attorney": {}}},
    ).json()["id"]
    with patch("app.routers.extraction_sessions.fill_form", new_callable=AsyncMock) as m_fill:
        m_fill.return_value = {
            "filled": ["passport.first_name"],
            "errors": [],
            "url": "https://example.com/form",
            "opened_in_existing_browser": False,
        }
        r = session_client.post(
            f"/extraction-sessions/{sid}/fill-form",
            json={"form_url": "https://example.com/form"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["filled_fields"] == ["passport.first_name"]
    m_fill.assert_called_once()
    again = session_client.get(f"/extraction-sessions/{sid}")
    assert again.json()["last_fill"]["form_url"] == "https://example.com/form"


def test_fill_from_session_invalid_url(session_client):
    sid = session_client.post(
        "/extraction-sessions",
        json={"extracted": {"passport": {}, "attorney": {}}},
    ).json()["id"]
    r = session_client.post(
        f"/extraction-sessions/{sid}/fill-form",
        json={"form_url": "ftp://bad"},
    )
    assert r.status_code == 400


def test_fill_from_session_not_found(session_client):
    missing_id = "f" * 32
    r = session_client.post(
        f"/extraction-sessions/{missing_id}/fill-form",
        json={"form_url": "https://example.com/form"},
    )
    assert r.status_code == 404
