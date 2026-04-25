from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db import get_connection


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def create_job(
    *,
    passport_filename: str | None,
    g28_filename: str | None,
    passport_sha256: str | None,
    g28_sha256: str | None,
    retention_days: int = 30,
) -> str:
    jid = uuid.uuid4().hex
    now = _utc_now_iso()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO intake_jobs (
              id, created_at, updated_at, status, stage, error_message,
              passport_filename, g28_filename, passport_sha256, g28_sha256,
              retention_days, result_json
            ) VALUES (?, ?, ?, 'queued', 'queued', NULL, ?, ?, ?, ?, ?, NULL)
            """,
            (
                jid,
                now,
                now,
                passport_filename,
                g28_filename,
                passport_sha256,
                g28_sha256,
                int(retention_days),
            ),
        )
    return jid


def update_job(
    job_id: str,
    *,
    status: str | None = None,
    stage: str | None = None,
    error_message: str | None = None,
    result_json: str | None = None,
) -> None:
    now = _utc_now_iso()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM intake_jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            return
        st = status if status is not None else row["status"]
        sg = stage if stage is not None else row["stage"]
        err = error_message if error_message is not None else row["error_message"]
        rj = result_json if result_json is not None else row["result_json"]
        conn.execute(
            """
            UPDATE intake_jobs
            SET updated_at = ?, status = ?, stage = ?, error_message = ?, result_json = ?
            WHERE id = ?
            """,
            (now, st, sg, err, rj, job_id),
        )


def get_job(job_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM intake_jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        return None
    return dict(row)


def insert_artifact(
    job_id: str,
    *,
    kind: str,
    role: str,
    page_index: int | None,
    rel_path: str,
    content_type: str,
    byte_size: int,
    sha256: str,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO intake_artifacts (job_id, kind, role, page_index, rel_path, content_type, byte_size, sha256)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (job_id, kind, role, page_index, rel_path, content_type, int(byte_size), sha256),
        )
        return int(cur.lastrowid)


def list_artifacts(job_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, job_id, kind, role, page_index, rel_path, content_type, byte_size, sha256
            FROM intake_artifacts WHERE job_id = ? ORDER BY id ASC
            """,
            (job_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_artifact(artifact_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM intake_artifacts WHERE id = ?", (artifact_id,)).fetchone()
    return dict(row) if row else None


def get_artifact_for_job(job_id: str, artifact_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM intake_artifacts WHERE id = ? AND job_id = ?",
            (artifact_id, job_id),
        ).fetchone()
    return dict(row) if row else None


def log_audit(job_id: str, event_type: str, payload: dict[str, Any] | None = None) -> None:
    now = _utc_now_iso()
    blob = json.dumps(payload or {}, ensure_ascii=False)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO intake_audit_events (job_id, created_at, event_type, payload_json)
            VALUES (?, ?, ?, ?)
            """,
            (job_id, now, event_type, blob),
        )


def list_audit(job_id: str, limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 500))
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, job_id, created_at, event_type, payload_json
            FROM intake_audit_events
            WHERE job_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (job_id, limit),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["payload"] = json.loads(d.pop("payload_json") or "{}")
        except json.JSONDecodeError:
            d["payload"] = {}
        out.append(d)
    out.reverse()
    return out


def replace_baml_assertions(job_id: str, rows: list[dict[str, Any]]) -> None:
    """
    Upsert extracted fields as source=baml without clobbering existing human_override rows.
    """
    now = _utc_now_iso()
    with get_connection() as conn:
        for r in rows:
            conn.execute(
                """
                INSERT INTO intake_field_assertions (
                  job_id, field_path, value_json, confidence, source, reviewer_note, updated_at
                ) VALUES (?, ?, ?, ?, 'baml', NULL, ?)
                ON CONFLICT(job_id, field_path) DO UPDATE SET
                  value_json = CASE
                    WHEN intake_field_assertions.source = 'human_override'
                    THEN intake_field_assertions.value_json
                    ELSE excluded.value_json
                  END,
                  confidence = CASE
                    WHEN intake_field_assertions.source = 'human_override'
                    THEN intake_field_assertions.confidence
                    ELSE excluded.confidence
                  END,
                  source = intake_field_assertions.source,
                  reviewer_note = intake_field_assertions.reviewer_note,
                  updated_at = CASE
                    WHEN intake_field_assertions.source = 'human_override'
                    THEN intake_field_assertions.updated_at
                    ELSE excluded.updated_at
                  END
                """,
                (
                    job_id,
                    r["field_path"],
                    r["value_json"],
                    r.get("confidence"),
                    now,
                ),
            )


def list_assertions(job_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, job_id, field_path, value_json, confidence, source, reviewer_note, updated_at
            FROM intake_field_assertions
            WHERE job_id = ?
            ORDER BY field_path ASC
            """,
            (job_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def upsert_human_override(
    job_id: str,
    *,
    field_path: str,
    value_json: str,
    reviewer_note: str | None,
) -> None:
    now = _utc_now_iso()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO intake_field_assertions (
              job_id, field_path, value_json, confidence, source, reviewer_note, updated_at
            ) VALUES (?, ?, ?, NULL, 'human_override', ?, ?)
            ON CONFLICT(job_id, field_path) DO UPDATE SET
              value_json = excluded.value_json,
              source = 'human_override',
              reviewer_note = excluded.reviewer_note,
              updated_at = excluded.updated_at
            """,
            (job_id, field_path, value_json, reviewer_note, now),
        )


def assertions_to_merged(assertions: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {"passport": {}, "attorney": {}}
    for r in assertions:
        fp = r.get("field_path") or ""
        if "." not in fp:
            continue
        section, key = fp.split(".", 1)
        if section not in ("passport", "attorney"):
            continue
        raw = r.get("value_json")
        try:
            val = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            val = raw
        block = merged.setdefault(section, {})
        if isinstance(block, dict):
            block[key] = val
    return merged


def delete_job_cascade(job_id: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM intake_jobs WHERE id = ?", (job_id,))
        return cur.rowcount > 0


def list_jobs_older_than_days(days: int) -> list[str]:
    """Return job ids with created_at older than N days (SQLite datetime comparison)."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id FROM intake_jobs
            WHERE datetime(created_at) < datetime('now', ?)
            """,
            (f"-{int(days)} days",),
        ).fetchall()
    return [str(r["id"]) for r in rows]
