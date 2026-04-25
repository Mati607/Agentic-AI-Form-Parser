from __future__ import annotations

import json
import time
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import GOOGLE_API_KEY, INTAKE_SIGNING_SECRET
from app.extraction_quality import build_readiness_report
from app.preview_fill import normalize_merged_extracted
from app import session_repository as session_repo
from app.intake import repo, storage
from app.intake.pipeline import run_intake_pipeline
from app.intake.schemas import PatchFieldsRequest, PromoteToSessionRequest
from app.intake.tokens import sign_artifact_download, verify_artifact_download

router = APIRouter()


def _require_api_key() -> None:
    if not GOOGLE_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_API_KEY is not set. Set it in .env for document intake and extraction.",
        )


def _signed_file_path(job_id: str, artifact_id: int, exp: int) -> str:
    sig = sign_artifact_download(artifact_id, exp, INTAKE_SIGNING_SECRET)
    return f"/intake/jobs/{job_id}/artifacts/{artifact_id}/file?exp={exp}&sig={sig}"


@router.post("/jobs", status_code=201)
async def create_intake_job(
    background_tasks: BackgroundTasks,
    passport: Optional[UploadFile] = File(None),
    g28: Optional[UploadFile] = File(None),
):
    """
    Create an intake job: stores originals on disk, then runs the pipeline in the background.
    """
    _require_api_key()
    if not passport and not g28:
        raise HTTPException(status_code=400, detail="Upload at least one file: passport or g28.")

    passport_filename = passport.filename if passport else None
    g28_filename = g28.filename if g28 else None
    passport_raw: bytes | None = await passport.read() if passport else None
    g28_raw: bytes | None = await g28.read() if g28 else None
    passport_sha = storage.sha256_bytes(passport_raw) if passport_raw else None
    g28_sha = storage.sha256_bytes(g28_raw) if g28_raw else None

    job_id = repo.create_job(
        passport_filename=passport_filename,
        g28_filename=g28_filename,
        passport_sha256=passport_sha,
        g28_sha256=g28_sha,
        retention_days=30,
    )
    repo.log_audit(job_id, "job_created", {"passport": bool(passport_raw), "g28": bool(g28_raw)})

    if passport_raw is not None:
        ct = (passport.content_type if passport else None) or "application/octet-stream"
        rel = f"{job_id}/original/passport.bin"
        storage.write_bytes(rel, passport_raw)
        repo.insert_artifact(
            job_id,
            kind="original_passport",
            role="passport",
            page_index=None,
            rel_path=rel,
            content_type=ct,
            byte_size=len(passport_raw),
            sha256=passport_sha or "",
        )

    if g28_raw is not None:
        ct = (g28.content_type if g28 else None) or "application/octet-stream"
        rel = f"{job_id}/original/g28.bin"
        storage.write_bytes(rel, g28_raw)
        repo.insert_artifact(
            job_id,
            kind="original_g28",
            role="g28",
            page_index=None,
            rel_path=rel,
            content_type=ct,
            byte_size=len(g28_raw),
            sha256=g28_sha or "",
        )

    background_tasks.add_task(run_intake_pipeline, job_id)
    return {"id": job_id, "status": "queued"}


@router.get("/jobs/{job_id}")
def get_intake_job(job_id: str) -> dict[str, Any]:
    row = repo.get_job(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found.")
    arts = repo.list_artifacts(job_id)
    audit = repo.list_audit(job_id, limit=80)
    exp = int(time.time()) + 15 * 60
    page_links: list[dict[str, Any]] = []
    for a in arts:
        if a.get("kind") != "page_image":
            continue
        aid = int(a["id"])
        page_links.append(
            {
                "artifact_id": aid,
                "role": a.get("role"),
                "page_index": a.get("page_index"),
                "content_type": a.get("content_type"),
                "path": _signed_file_path(job_id, aid, exp),
                "exp": exp,
            }
        )
    out = dict(row)
    out.pop("result_json", None)
    out["artifacts"] = arts
    out["audit"] = audit
    out["page_image_links"] = page_links
    if row.get("status") == "completed" and row.get("result_json"):
        try:
            out["extracted"] = json.loads(row["result_json"])
        except json.JSONDecodeError:
            out["extracted"] = None
    return out


@router.get("/jobs/{job_id}/fields")
def get_intake_fields(job_id: str) -> dict[str, Any]:
    if not repo.get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found.")
    assertions = repo.list_assertions(job_id)
    return {"assertions": assertions}


@router.patch("/jobs/{job_id}/fields")
def patch_intake_fields(job_id: str, body: PatchFieldsRequest) -> dict[str, Any]:
    if not repo.get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found.")
    for p in body.patches:
        try:
            vjson = json.dumps(p.value, ensure_ascii=False)
        except (TypeError, ValueError):
            vjson = json.dumps(str(p.value), ensure_ascii=False)
        repo.upsert_human_override(
            job_id,
            field_path=p.field_path.strip(),
            value_json=vjson,
            reviewer_note=p.reviewer_note,
        )
        repo.log_audit(
            job_id,
            "field_override",
            {"field_path": p.field_path, "reviewer_note": p.reviewer_note},
        )
    return get_intake_fields(job_id)


@router.get("/jobs/{job_id}/artifacts/{artifact_id}/file")
def download_intake_artifact(
    job_id: str,
    artifact_id: int,
    exp: int,
    sig: str,
):
    if not verify_artifact_download(artifact_id, int(exp), sig, INTAKE_SIGNING_SECRET):
        raise HTTPException(status_code=403, detail="Invalid or expired download link.")
    art = repo.get_artifact_for_job(job_id, artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    path = storage.storage_root() / art["rel_path"]
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact file missing.")
    return FileResponse(str(path), media_type=art.get("content_type") or "application/octet-stream")


@router.post("/jobs/{job_id}/promote-to-session", status_code=201)
def promote_intake_job_to_session(job_id: str, body: PromoteToSessionRequest) -> dict[str, Any]:
    row = repo.get_job(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found.")
    if row.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Job must be completed before promoting to a session.")
    assertions = repo.list_assertions(job_id)
    merged = repo.assertions_to_merged(assertions)
    normalized = normalize_merged_extracted(merged)
    readiness = build_readiness_report(normalized)
    sid = session_repo.create_session(
        normalized,
        title=body.title or f"Intake {job_id[:8]}",
        passport_filename=row.get("passport_filename"),
        g28_filename=row.get("g28_filename"),
        default_form_url=body.default_form_url,
        notes=body.notes,
        quality_snapshot=readiness,
    )
    repo.log_audit(job_id, "promoted_to_session", {"session_id": sid})
    return {"session_id": sid, "readiness": readiness, "extracted": normalized}
