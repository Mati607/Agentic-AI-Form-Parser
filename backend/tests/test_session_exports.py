"""Tests for CSV/HTML exports and JSON Schema bundle endpoints."""

from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app
from app.exports.merged_json_schema import merged_extraction_schema, schema_bundle


def test_schema_bundle_shape():
    bundle = schema_bundle()
    assert bundle["schema_version"] == 1
    assert "merged_extraction" in bundle and "session_export" in bundle
    assert bundle["merged_extraction"]["type"] == "object"


def test_merged_extraction_schema_flags():
    merged = merged_extraction_schema(envelope=False)
    assert merged["properties"]["passport"]["type"] == "object"
    assert "last_name" in merged["properties"]["passport"]["properties"]


def test_export_endpoints(tmp_path, monkeypatch):
    db_path = tmp_path / "export_sessions.db"
    monkeypatch.setattr("app.db.get_db_path", lambda: db_path)
    init_db()
    client = TestClient(app)

    c = client.post(
        "/extraction-sessions",
        json={
            "extracted": {
                "passport": {"last_name": "Nguyen", "first_name": "An"},
                "attorney": {"email": "rep@firm.example", "city": "Seattle"},
            },
            "title": "Export me",
            "notes": "demo",
        },
    )
    assert c.status_code == 201
    sid = c.json()["id"]

    sch = client.get("/extraction-sessions/export-schema")
    assert sch.status_code == 200
    assert sch.json()["schema_version"] == 1

    csv_r = client.get(f"/extraction-sessions/{sid}/export.csv")
    assert csv_r.status_code == 200
    text = csv_r.text
    assert "passport,last_name,passport.last_name,Nguyen" in text.replace("\r\n", "\n")
    assert "__meta__" in text

    html_r = client.get(f"/extraction-sessions/{sid}/export.html")
    assert html_r.status_code == 200
    body = html_r.text
    assert "<!DOCTYPE html>" in body
    assert "Nguyen" in body
    assert "Readiness" in body or "readiness" in body.lower()
