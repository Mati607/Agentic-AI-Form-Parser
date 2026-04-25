from __future__ import annotations

import json
import traceback
from typing import Any

from app.extraction import (
    extract_from_g28_file,
    extract_from_passport_file,
    merge_extracted,
    validate_g28_file,
    validate_passport_file,
)
from app.preview_fill import normalize_merged_extracted
from app.intake import pdf_render, repo, storage
from app.intake.provenance import merged_to_field_assertions

ALLOWED_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
}


def _load_original(
    job_id: str,
    kind: str,
) -> tuple[bytes | None, str | None]:
    arts = repo.list_artifacts(job_id)
    for a in arts:
        if a.get("kind") == kind:
            data = storage.read_bytes(a["rel_path"])
            return data, a.get("content_type")
    return None, None


async def run_intake_pipeline(job_id: str) -> None:
    """
    Validate uploads, render review pages, run BAML extraction, persist merged JSON + assertions.
    """
    try:
        repo.update_job(job_id, status="validating", stage="validating_documents")
        repo.log_audit(job_id, "stage", {"stage": "validating_documents"})

        passport_bytes, passport_ct = _load_original(job_id, "original_passport")
        g28_bytes, g28_ct = _load_original(job_id, "original_g28")

        if not passport_bytes and not g28_bytes:
            raise RuntimeError("No uploaded documents found for this job.")

        validation_errors: dict[str, str] = {}

        if passport_bytes is not None:
            ct = (passport_ct or "").strip()
            if ct not in ALLOWED_TYPES:
                validation_errors["passport"] = f"Passport file must be PDF or image (JPEG/PNG). Got: {ct}"
            else:
                val = await validate_passport_file(passport_bytes, ct)
                if not val.get("is_valid"):
                    validation_errors["passport"] = val.get("reason") or "This document does not appear to be a passport."

        if g28_bytes is not None:
            ct = (g28_ct or "").strip()
            if ct not in ALLOWED_TYPES:
                validation_errors["g28"] = f"G-28 file must be PDF or image (JPEG/PNG). Got: {ct}"
            else:
                val = await validate_g28_file(g28_bytes, ct)
                if not val.get("is_valid"):
                    validation_errors["g28"] = val.get("reason") or "This document does not appear to be Form G-28/A-28."

        if validation_errors:
            msg = " ".join([f"{k}: {v}" for k, v in validation_errors.items()])
            repo.update_job(job_id, status="failed", stage="validation_failed", error_message=msg)
            repo.log_audit(job_id, "validation_failed", {"errors": validation_errors})
            return

        repo.update_job(job_id, status="rendering", stage="rendering_pages")
        repo.log_audit(job_id, "stage", {"stage": "rendering_pages"})
        await _render_review_pages(job_id, passport_bytes, passport_ct, g28_bytes, g28_ct)

        repo.update_job(job_id, status="extracting", stage="extracting")
        repo.log_audit(job_id, "stage", {"stage": "extracting"})

        passport_data: dict[str, Any] = {}
        g28_data: dict[str, Any] = {}

        if passport_bytes is not None and passport_ct:
            ct = passport_ct.strip()
            passport_data = await extract_from_passport_file(passport_bytes, ct)

        if g28_bytes is not None and g28_ct:
            ct = g28_ct.strip()
            g28_data = await extract_from_g28_file(g28_bytes, ct)

        merged = merge_extracted(passport_data, g28_data)
        normalized = normalize_merged_extracted(merged)
        result_blob = json.dumps(normalized, ensure_ascii=False)

        repo.update_job(job_id, status="indexing", stage="building_field_assertions")
        rows = merged_to_field_assertions(normalized)
        repo.replace_baml_assertions(job_id, rows)

        repo.update_job(job_id, status="completed", stage="completed", error_message="", result_json=result_blob)
        repo.log_audit(job_id, "completed", {"field_count": len(rows)})
    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()
        repo.update_job(
            job_id,
            status="failed",
            stage="failed",
            error_message=str(e) or "Pipeline failed.",
        )
        repo.log_audit(job_id, "failed", {"error": str(e), "traceback": tb[:8000]})


async def _render_review_pages(
    job_id: str,
    passport_bytes: bytes | None,
    passport_ct: str | None,
    g28_bytes: bytes | None,
    g28_ct: str | None,
) -> None:
    if passport_bytes and passport_ct and pdf_render.is_pdf(passport_ct):
        pages = pdf_render.render_pdf_to_png_pages(passport_bytes)
        for idx, png in pages:
            rel = f"{job_id}/pages/passport-{idx}.png"
            storage.write_bytes(rel, png)
            h = storage.sha256_bytes(png)
            repo.insert_artifact(
                job_id,
                kind="page_image",
                role="passport",
                page_index=idx,
                rel_path=rel,
                content_type="image/png",
                byte_size=len(png),
                sha256=h,
            )
    elif passport_bytes and passport_ct:
        pages = pdf_render.single_image_as_page(passport_bytes, passport_ct)
        idx, data = pages[0]
        ext = "png" if "png" in passport_ct.lower() else "jpg"
        rel = f"{job_id}/pages/passport-{idx}.{ext}"
        storage.write_bytes(rel, data)
        h = storage.sha256_bytes(data)
        ct = "image/png" if ext == "png" else "image/jpeg"
        repo.insert_artifact(
            job_id,
            kind="page_image",
            role="passport",
            page_index=idx,
            rel_path=rel,
            content_type=ct,
            byte_size=len(data),
            sha256=h,
        )

    if g28_bytes and g28_ct and pdf_render.is_pdf(g28_ct):
        pages = pdf_render.render_pdf_to_png_pages(g28_bytes)
        for idx, png in pages:
            rel = f"{job_id}/pages/g28-{idx}.png"
            storage.write_bytes(rel, png)
            h = storage.sha256_bytes(png)
            repo.insert_artifact(
                job_id,
                kind="page_image",
                role="g28",
                page_index=idx,
                rel_path=rel,
                content_type="image/png",
                byte_size=len(png),
                sha256=h,
            )
    elif g28_bytes and g28_ct:
        pages = pdf_render.single_image_as_page(g28_bytes, g28_ct)
        idx, data = pages[0]
        ext = "png" if "png" in g28_ct.lower() else "jpg"
        rel = f"{job_id}/pages/g28-{idx}.{ext}"
        storage.write_bytes(rel, data)
        h = storage.sha256_bytes(data)
        ct = "image/png" if ext == "png" else "image/jpeg"
        repo.insert_artifact(
            job_id,
            kind="page_image",
            role="g28",
            page_index=idx,
            rel_path=rel,
            content_type=ct,
            byte_size=len(data),
            sha256=h,
        )
