"""
CRUD for extraction_sessions stored in SQLite.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db import get_connection

_MAX_TAGS = 20
_MAX_TAG_LEN = 48


def normalize_tags_list(raw: list[str] | None) -> list[str]:
    """Lowercase, trim, dedupe, cap count/length for stored session tags."""
    if not raw:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for t in raw:
        if not isinstance(t, str):
            continue
        s = t.strip().lower()[:_MAX_TAG_LEN]
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= _MAX_TAGS:
            break
    return out


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_quality_blob(raw: Any) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        q = json.loads(raw)
        return q if isinstance(q, dict) else None
    except json.JSONDecodeError:
        return None


def _parse_tags_blob(raw: Any) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return normalize_tags_list([str(x) for x in data if x is not None])
    except (json.JSONDecodeError, TypeError):
        pass
    return []


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
    quality = _parse_quality_blob(row["quality_json"])
    out: dict[str, Any] = {
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
    if quality:
        out["readiness_score"] = quality.get("score")
        out["readiness_grade"] = quality.get("grade")
    out["tags"] = _parse_tags_blob(row["tags_json"])
    return out


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
    quality = _parse_quality_blob(row["quality_json"])
    detail = {
        **summary,
        "extracted": extracted,
        "last_fill": last_fill,
        "notes": row["notes"],
    }
    if quality is not None:
        detail["readiness"] = quality
    return detail


def create_session(
    extracted: dict[str, Any],
    *,
    title: str | None = None,
    passport_filename: str | None = None,
    g28_filename: str | None = None,
    default_form_url: str | None = None,
    notes: str | None = None,
    quality_snapshot: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> str:
    """Insert a new session; returns generated id (UUID hex)."""
    sid = uuid.uuid4().hex
    now = _utc_now_iso()
    payload = json.dumps(extracted, ensure_ascii=False)
    qblob = json.dumps(quality_snapshot, ensure_ascii=False) if quality_snapshot is not None else None
    tags_blob = (
        json.dumps(normalize_tags_list(tags), ensure_ascii=False) if tags is not None else None
    )
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO extraction_sessions (
              id, created_at, updated_at, title, passport_filename, g28_filename,
              default_form_url, extracted_json, last_fill_json, notes, quality_json, tags_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
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
                qblob,
                tags_blob,
            ),
        )
    return sid


def list_sessions(
    limit: int = 50,
    offset: int = 0,
    *,
    q: str | None = None,
    tags_any: list[str] | None = None,
    min_score: float | None = None,
    grades: list[str] | None = None,
    has_fill: bool | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Return (page of summaries, total count). Optional filters combine with AND."""
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    where_parts: list[str] = ["1 = 1"]
    params: list[Any] = []

    if q and q.strip():
        term = f"%{q.strip()}%"
        where_parts.append(
            "(title LIKE ? OR notes LIKE ? OR passport_filename LIKE ? OR "
            "g28_filename LIKE ? OR extracted_json LIKE ?)"
        )
        params.extend([term, term, term, term, term])

    tag_vals = normalize_tags_list(tags_any or [])
    if tag_vals:
        placeholders = ",".join("?" * len(tag_vals))
        where_parts.append(
            f"EXISTS (SELECT 1 FROM json_each(COALESCE(tags_json, '[]')) AS je "
            f"WHERE je.value IN ({placeholders}))"
        )
        params.extend(tag_vals)

    if min_score is not None:
        where_parts.append("CAST(json_extract(quality_json, '$.score') AS REAL) >= ?")
        params.append(float(min_score))

    if grades:
        gnorm = [g.strip().upper()[:4] for g in grades if g and str(g).strip()]
        gnorm = [g for g in gnorm if g]
        if gnorm:
            placeholders = ",".join("?" * len(gnorm))
            where_parts.append(f"json_extract(quality_json, '$.grade') IN ({placeholders})")
            params.extend(gnorm)

    if has_fill is True:
        where_parts.append("last_fill_json IS NOT NULL AND TRIM(COALESCE(last_fill_json, '')) != ''")
    elif has_fill is False:
        where_parts.append("(last_fill_json IS NULL OR TRIM(COALESCE(last_fill_json, '')) = '')")

    where_sql = " AND ".join(where_parts)
    with get_connection() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS c FROM extraction_sessions WHERE {where_sql}",
            params,
        ).fetchone()["c"]
        rows = conn.execute(
            f"""
            SELECT id, created_at, updated_at, title, passport_filename, g28_filename,
                   default_form_url, extracted_json, last_fill_json, notes, quality_json, tags_json
            FROM extraction_sessions
            WHERE {where_sql}
            ORDER BY datetime(created_at) DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
    return [_row_to_summary(r) for r in rows], int(total)


def get_session(session_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, created_at, updated_at, title, passport_filename, g28_filename,
                   default_form_url, extracted_json, last_fill_json, notes, quality_json, tags_json
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


def update_readiness_snapshot(session_id: str, quality_snapshot: dict[str, Any]) -> bool:
    """Persist a new readiness report JSON blob; bumps updated_at."""
    now = _utc_now_iso()
    blob = json.dumps(quality_snapshot, ensure_ascii=False)
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE extraction_sessions
            SET quality_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (blob, now, session_id),
        )
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
    tags: list[str] | None = None,
) -> bool:
    """Patch optional metadata fields; None means leave unchanged (except tags: pass a list to replace)."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT title, notes, default_form_url, tags_json FROM extraction_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return False
        new_title = row["title"] if title is None else title
        new_notes = row["notes"] if notes is None else notes
        new_url = row["default_form_url"] if default_form_url is None else default_form_url
        if tags is None:
            new_tags_blob = row["tags_json"]
        else:
            new_tags_blob = json.dumps(normalize_tags_list(tags), ensure_ascii=False)
        now = _utc_now_iso()
        cur = conn.execute(
            """
            UPDATE extraction_sessions
            SET title = ?, notes = ?, default_form_url = ?, tags_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_title, new_notes, new_url, new_tags_blob, now, session_id),
        )
        return cur.rowcount > 0
