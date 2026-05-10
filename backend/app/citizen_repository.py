"""
CRUD for citizens (portal profiles) stored in SQLite.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.db import get_connection

_VALID_STATUS = frozenset({"active", "archived", "lead"})


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_status(raw: str | None) -> str:
    s = (raw or "active").strip().lower()
    return s if s in _VALID_STATUS else "active"


def citizen_exists(citizen_id: str) -> bool:
    if not citizen_id or not str(citizen_id).strip():
        return False
    with get_connection() as conn:
        r = conn.execute("SELECT 1 AS o FROM citizens WHERE id = ? LIMIT 1", (citizen_id.strip(),)).fetchone()
        return r is not None


def create_citizen(
    *,
    display_name: str,
    email: str | None = None,
    phone: str | None = None,
    preferred_language: str | None = None,
    case_reference: str | None = None,
    status: str | None = None,
    notes: str | None = None,
) -> str:
    cid = uuid.uuid4().hex
    now = _utc_now_iso()
    st = normalize_status(status)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO citizens (
              id, created_at, updated_at, display_name, email, phone,
              preferred_language, case_reference, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cid,
                now,
                now,
                (display_name or "").strip() or "Unnamed",
                email,
                phone,
                preferred_language,
                case_reference,
                st,
                notes,
            ),
        )
    return cid


def _row_to_summary(row: Any, *, session_count: int | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": row["id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "display_name": row["display_name"],
        "email": row["email"],
        "phone": row["phone"],
        "preferred_language": row["preferred_language"],
        "case_reference": row["case_reference"],
        "status": row["status"],
    }
    if session_count is not None:
        out["session_count"] = session_count
    return out


def _row_to_detail(row: Any) -> dict[str, Any]:
    d = _row_to_summary(row)
    d["notes"] = row["notes"]
    return d


def list_citizens(
    limit: int = 50,
    offset: int = 0,
    *,
    q: str | None = None,
    status: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    where_parts = ["1 = 1"]
    params: list[Any] = []

    if q and q.strip():
        term = f"%{q.strip()}%"
        where_parts.append(
            "(c.display_name LIKE ? OR c.email LIKE ? OR c.phone LIKE ? OR "
            "c.case_reference LIKE ? OR c.notes LIKE ?)"
        )
        params.extend([term, term, term, term, term])

    if status and status.strip():
        where_parts.append("c.status = ?")
        params.append(status.strip().lower())

    where_sql = " AND ".join(where_parts)
    with get_connection() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM citizens c WHERE {where_sql}",
            params,
        ).fetchone()["n"]
        rows = conn.execute(
            f"""
            SELECT c.*,
              (SELECT COUNT(*) FROM extraction_sessions s WHERE s.citizen_id = c.id) AS session_count
            FROM citizens c
            WHERE {where_sql}
            ORDER BY datetime(c.updated_at) DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()

    items = []
    for r in rows:
        sc = int(r["session_count"] if r["session_count"] is not None else 0)
        items.append(_row_to_summary(r, session_count=sc))
    return items, int(total)


def get_citizen(citizen_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT c.*,
              (SELECT COUNT(*) FROM extraction_sessions s WHERE s.citizen_id = c.id) AS session_count
            FROM citizens c WHERE c.id = ?
            """,
            (citizen_id,),
        ).fetchone()
    if row is None:
        return None
    d = _row_to_detail(row)
    d["session_count"] = int(row["session_count"] or 0)
    return d


def update_citizen(
    citizen_id: str,
    *,
    display_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    preferred_language: str | None = None,
    case_reference: str | None = None,
    status: str | None = None,
    notes: str | None = None,
) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM citizens WHERE id = ?", (citizen_id,)).fetchone()
        if row is None:
            return False
        new_name = row["display_name"] if display_name is None else ((display_name or "").strip() or "Unnamed")
        new_email = row["email"] if email is None else email
        new_phone = row["phone"] if phone is None else phone
        new_lang = row["preferred_language"] if preferred_language is None else preferred_language
        new_ref = row["case_reference"] if case_reference is None else case_reference
        new_status = row["status"] if status is None else normalize_status(status)
        new_notes = row["notes"] if notes is None else notes
        now = _utc_now_iso()
        cur = conn.execute(
            """
            UPDATE citizens SET
              display_name = ?, email = ?, phone = ?, preferred_language = ?,
              case_reference = ?, status = ?, notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                new_name,
                new_email,
                new_phone,
                new_lang,
                new_ref,
                new_status,
                new_notes,
                now,
                citizen_id,
            ),
        )
        return cur.rowcount > 0


def delete_citizen(citizen_id: str) -> bool:
    """Remove citizen and unlink sessions (citizen_id set to NULL)."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE extraction_sessions SET citizen_id = NULL, updated_at = ? WHERE citizen_id = ?",
            (_utc_now_iso(), citizen_id),
        )
        cur = conn.execute("DELETE FROM citizens WHERE id = ?", (citizen_id,))
        return cur.rowcount > 0
