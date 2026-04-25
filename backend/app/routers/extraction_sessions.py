"""
HTTP API for persisting merged extractions and re-running form fill without re-uploading files.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from starlette.responses import Response

from app.extraction_quality import build_readiness_report
from app.extraction_quality.report import readiness_report_to_markdown
from app.form_filler import fill_form
from app.preview_fill import normalize_merged_extracted
from app import session_repository as session_repo
from app.schemas.extraction_sessions import (
    CreateExtractionSessionRequest,
    ExtractionSessionListResponse,
    FillStoredSessionFormRequest,
    PatchExtractionSessionRequest,
)

router = APIRouter()


def _as_merged_dict(extracted: Any) -> dict[str, Any]:
    if hasattr(extracted, "model_dump"):
        return extracted.model_dump()
    return dict(extracted) if isinstance(extracted, dict) else {}


@router.post("", status_code=201)
def create_extraction_session(payload: CreateExtractionSessionRequest) -> dict[str, Any]:
    merged = _as_merged_dict(payload.extracted)
    normalized = normalize_merged_extracted(merged)
    readiness = build_readiness_report(normalized)
    sid = session_repo.create_session(
        normalized,
        title=payload.title,
        passport_filename=payload.passport_filename,
        g28_filename=payload.g28_filename,
        default_form_url=payload.default_form_url,
        notes=payload.notes,
        quality_snapshot=readiness,
    )
    return {"id": sid, "readiness": readiness}


@router.get("", response_model=ExtractionSessionListResponse)
def list_extraction_sessions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ExtractionSessionListResponse:
    items, total = session_repo.list_sessions(limit=limit, offset=offset)
    return ExtractionSessionListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{session_id}")
def get_extraction_session(session_id: str) -> dict[str, Any]:
    row = session_repo.get_session(session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return row


@router.patch("/{session_id}")
def patch_extraction_session(session_id: str, payload: PatchExtractionSessionRequest) -> dict[str, Any]:
    ok = session_repo.update_session_metadata(
        session_id,
        title=payload.title,
        notes=payload.notes,
        default_form_url=payload.default_form_url,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found.")
    row = session_repo.get_session(session_id)
    assert row is not None
    return row


@router.delete("/{session_id}", status_code=204, response_model=None)
def delete_extraction_session(session_id: str) -> None:
    if not session_repo.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")


@router.get("/{session_id}/export")
def export_extraction_session(session_id: str) -> Response:
    row = session_repo.get_session(session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    export_obj = {
        "id": row["id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "title": row["title"],
        "passport_filename": row["passport_filename"],
        "g28_filename": row["g28_filename"],
        "default_form_url": row["default_form_url"],
        "notes": row["notes"],
        "extracted": row.get("extracted"),
        "last_fill": row.get("last_fill"),
        "readiness": row.get("readiness"),
    }
    body = json.dumps(export_obj, ensure_ascii=False, indent=2)
    filename = f"extraction-session-{session_id[:8]}.json"
    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{session_id}/readiness.md")
def export_readiness_markdown(session_id: str) -> Response:
    row = session_repo.get_session(session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    readiness = row.get("readiness") if isinstance(row, dict) else None
    if not isinstance(readiness, dict):
        raise HTTPException(status_code=404, detail="Readiness snapshot not found for this session.")
    title = row.get("title") if isinstance(row.get("title"), str) and row.get("title") else None
    subject = row.get("passport_filename") or row.get("g28_filename") or row.get("id")
    md = readiness_report_to_markdown(readiness, title=title or "Extraction Readiness Report", subject=str(subject))
    filename = f"readiness-{session_id[:8]}.md"
    return Response(
        content=md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _validate_form_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        raise HTTPException(status_code=400, detail="form_url is required.")
    if not u.startswith("http://") and not u.startswith("https://"):
        raise HTTPException(status_code=400, detail="form_url must be http or https.")
    return u


@router.post("/{session_id}/fill-form")
async def fill_form_from_session(session_id: str, payload: FillStoredSessionFormRequest) -> dict[str, Any]:
    row = session_repo.get_session(session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    extracted = row.get("extracted") or {}
    if not isinstance(extracted, dict):
        extracted = {}
    form_url = _validate_form_url(payload.form_url)
    result = await fill_form(extracted, form_url=form_url)
    summary = {
        "filled": result["filled"],
        "errors": result["errors"],
        "form_url": result["url"],
        "opened_in_existing_browser": result.get("opened_in_existing_browser", False),
    }
    session_repo.update_last_fill(session_id, summary)
    return {
        "session_id": session_id,
        "extracted": extracted,
        "filled_fields": result["filled"],
        "errors": result["errors"],
        "form_url": result["url"],
        "opened_in_existing_browser": result.get("opened_in_existing_browser", False),
    }
