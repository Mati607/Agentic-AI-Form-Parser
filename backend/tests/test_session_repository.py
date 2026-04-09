"""Integration tests for session_repository against a temporary SQLite file."""

import pytest

from app.db import init_db
from app import session_repository as repo


@pytest.fixture
def repo_db(tmp_path, monkeypatch):
    db_path = tmp_path / "repo_test.db"
    monkeypatch.setattr("app.db.get_db_path", lambda: db_path)
    init_db()
    yield db_path


def test_create_list_get_delete(repo_db):
    sid = repo.create_session(
        {"passport": {"first_name": "A"}, "attorney": {"email": "x@y.z"}},
        title="Case 1",
        passport_filename="p.pdf",
        g28_filename=None,
        default_form_url="https://example.com/f",
        notes="note",
    )
    assert len(sid) == 32
    items, total = repo.list_sessions(limit=10, offset=0)
    assert total == 1
    assert items[0]["id"] == sid
    assert items[0]["title"] == "Case 1"
    assert items[0]["field_counts"]["passport"] == 1
    assert items[0]["field_counts"]["attorney"] == 1

    detail = repo.get_session(sid)
    assert detail is not None
    assert detail["extracted"]["passport"]["first_name"] == "A"
    assert detail["notes"] == "note"
    assert detail["last_fill"] is None

    assert repo.delete_session(sid) is True
    assert repo.get_session(sid) is None
    assert repo.delete_session(sid) is False


def test_update_last_fill(repo_db):
    sid = repo.create_session({"passport": {}, "attorney": {}})
    ok = repo.update_last_fill(
        sid,
        {"filled": ["passport.first_name"], "errors": [], "form_url": "https://x.com"},
    )
    assert ok is True
    detail = repo.get_session(sid)
    assert detail["last_fill"]["form_url"] == "https://x.com"
    items, _ = repo.list_sessions()
    assert items[0]["has_last_fill"] is True


def test_update_metadata(repo_db):
    sid = repo.create_session({"passport": {}, "attorney": {}}, title="T1")
    assert repo.update_session_metadata(sid, title="T2", notes="N1") is True
    d = repo.get_session(sid)
    assert d["title"] == "T2"
    assert d["notes"] == "N1"
    assert repo.update_session_metadata("deadbeef" * 2, title="x") is False


def test_create_with_quality_snapshot(repo_db):
    sid = repo.create_session(
        {"passport": {"first_name": "A"}, "attorney": {}},
        quality_snapshot={"schema_version": 1, "score": 77, "grade": "C", "findings": []},
    )
    d = repo.get_session(sid)
    assert d is not None
    assert d.get("readiness", {}).get("score") == 77
    items, _ = repo.list_sessions(limit=5, offset=0)
    assert items[0]["readiness_score"] == 77
    assert items[0]["readiness_grade"] == "C"


def test_list_pagination(repo_db):
    for i in range(5):
        repo.create_session({"passport": {"n": i}, "attorney": {}}, title=f"S{i}")
    page, total = repo.list_sessions(limit=2, offset=0)
    assert total == 5
    assert len(page) == 2
    page2, total2 = repo.list_sessions(limit=2, offset=2)
    assert total2 == 5
    assert page[0]["id"] != page2[0]["id"]
