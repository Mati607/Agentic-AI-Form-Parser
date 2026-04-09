"""
CRUD for extraction_sessions stored in SQLite.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db import get_connection


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _row_to_summary(row: Any) -> dict[str, Any]:
    """Lightweight dict for list endpoints."""
    extracted: dict[str, Any] = {}
    try:
        extracted = json.loads(row["extracted_json"] or "{}")
    except json.JSONDecodeError:
        extracted = {}
    p = extracted.get("passport")
    a = extracted.get("attorney")
    passport_n = len(p) if isinstance(p, dict) else 0
    attorney_n = len(a) if isinstance(a, dict) else 0
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "title": row["title"],
        "passport_filename": row["passport_filename"],
        "g28_filename": row["g28_filename"],
        "default_form_url": row["default_form_url"],
        "field_counts": {"passport": passport_n, "attorney": attorney_n},
        "has_last_fill": bool(row["last_fill_json"]),
    }


def _row_to_detail(row: Any) -> dict[str, Any]:
    summary = _row_to_summary(row)
    try:
        extracted = json.loads(row["extracted_json"] or "{}")
    except json.JSONDecodeError:
        extracted = {}
    last_fill = None
    if row["last_fill_json"]:
        try:
            last_fill = json.loads(row["last_fill_json"])
        except json.JSONDecodeError:
            last_fill = None
    return {
        **summary,
        "extracted": extracted,
        "last_fill": last_fill,
        "notes": row["notes"],
    }


def create_session(
    extracted: dict[str, Any],
    *,
    title: str | None = None,
    passport_filename: str | None = None,
    g28_filename: str | None = None,
    default_form_url: str | None = None,
    notes: str | None = None,
) -> str:
    """Insert a new session; returns generated id (UUID hex)."""
    sid = uuid.uuid4().hex
    now = _utc_now_iso()
    payload = json.dumps(extracted, ensure_ascii=False)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO extraction_sessions (
              id, created_at, updated_at, title, passport_filename, g28_filename,
              default_form_url, extracted_json, last_fill_json, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
            """,
            (
                sid,
                now,
                now,
                title,
                passport_filename,
                g28_filename,
                default_form_url,
                payload,
                notes,
            ),
        )
    return sid


def list_sessions(limit: int = 50, offset: int = 0) -> tuple[list[dict[str, Any]], int]:
    """Return (page of summaries, total count)."""
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM extraction_sessions").fetchone()["c"]
        rows = conn.execute(
            """
            SELECT id, created_at, updated_at, title, passport_filename, g28_filename,
                   default_form_url, extracted_json, last_fill_json, notes
            FROM extraction_sessions
            ORDER BY datetime(created_at) DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
    return [_row_to_summary(r) for r in rows], int(total)


def get_session(session_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, created_at, updated_at, title, passport_filename, g28_filename,
                   default_form_url, extracted_json, last_fill_json, notes
            FROM extraction_sessions WHERE id = ?
            """,
            (session_id,),
        ).fetchone()
    if row is None:
        return None
    return _row_to_detail(row)


def delete_session(session_id: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM extraction_sessions WHERE id = ?", (session_id,))
        return cur.rowcount > 0


def update_last_fill(session_id: str, fill_summary: dict[str, Any]) -> bool:
    """Persist last fill result JSON; bumps updated_at."""
    now = _utc_now_iso()
    blob = json.dumps(fill_summary, ensure_ascii=False)
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE extraction_sessions
            SET last_fill_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (blob, now, session_id),
        )
        return cur.rowcount > 0


def update_session_metadata(
    session_id: str,
    *,
    title: str | None = None,
    notes: str | None = None,
    default_form_url: str | None = None,
) -> bool:
    """Patch optional metadata fields; None means leave unchanged."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT title, notes, default_form_url FROM extraction_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return False
        new_title = row["title"] if title is None else title
        new_notes = row["notes"] if notes is None else notes
        new_url = row["default_form_url"] if default_form_url is None else default_form_url
        now = _utc_now_iso()
        cur = conn.execute(
            """
            UPDATE extraction_sessions
            SET title = ?, notes = ?, default_form_url = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_title, new_notes, new_url, now, session_id),
        )
        return cur.rowcount > 0
