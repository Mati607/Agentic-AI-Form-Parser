"""HTTP tests for /citizens."""

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app


@pytest.fixture
def citizen_client(tmp_path, monkeypatch):
    db_path = tmp_path / "citizens_api.db"
    monkeypatch.setattr("app.db.get_db_path", lambda: db_path)
    init_db()
    with TestClient(app) as client:
        yield client


def test_create_list_get_patch_delete_citizen(citizen_client):
    c = citizen_client.post(
        "/citizens",
        json={
            "display_name": "Asha Verma",
            "email": "asha@example.com",
            "case_reference": "FILE-1001",
            "status": "active",
        },
    )
    assert c.status_code == 201
    cid = c.json()["id"]
    assert len(cid) == 32
    assert c.json()["display_name"] == "Asha Verma"
    assert c.json()["session_count"] == 0

    lst = citizen_client.get("/citizens?q=Verma")
    assert lst.status_code == 200
    assert lst.json()["total"] >= 1

    one = citizen_client.get(f"/citizens/{cid}")
    assert one.status_code == 200
    assert one.json()["email"] == "asha@example.com"

    p = citizen_client.patch(f"/citizens/{cid}", json={"phone": "+1 555 0100"})
    assert p.status_code == 200
    assert p.json()["phone"] == "+1 555 0100"

    d = citizen_client.delete(f"/citizens/{cid}")
    assert d.status_code == 204
    assert citizen_client.get(f"/citizens/{cid}").status_code == 404


def test_citizen_detail_includes_sessions(citizen_client):
    cc = citizen_client.post("/citizens", json={"display_name": "Linked person"})
    cid = cc.json()["id"]
    s = citizen_client.post(
        "/extraction-sessions",
        json={
            "extracted": {"passport": {"last_name": "L"}, "attorney": {}},
            "citizen_id": cid,
        },
    )
    assert s.status_code == 201
    sid = s.json()["id"]

    detail = citizen_client.get(f"/citizens/{cid}?include_sessions=true")
    assert detail.status_code == 200
    body = detail.json()
    assert body["session_count"] == 1
    assert len(body["sessions"]) == 1
    assert body["sessions"][0]["id"] == sid


def test_create_session_invalid_citizen_returns_400(citizen_client):
    r = citizen_client.post(
        "/extraction-sessions",
        json={
            "extracted": {"passport": {}, "attorney": {}},
            "citizen_id": "deadbeef" * 2,
        },
    )
    assert r.status_code == 400
