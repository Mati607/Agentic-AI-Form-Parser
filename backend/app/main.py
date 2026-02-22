import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    backend_dir = Path(__file__).resolve().parent.parent
    load_dotenv(backend_dir / ".env")
    load_dotenv(backend_dir.parent / ".env")
except ImportError:
    pass

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import GOOGLE_API_KEY
from app.extraction import (
    extract_from_passport_file,
    extract_from_g28_file,
    merge_extracted,
    validate_passport_file,
    validate_g28_file,
)
from app.form_filler import fill_form

app = FastAPI(title="Alma Document & Form Automation", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
}


def check_api_key():
    if not GOOGLE_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_API_KEY is not set. Set it in .env for document extraction.",
        )


@app.get("/health")
def health():
    return {"status": "ok"}


def _validation_error_response(validation_errors: dict) -> tuple[int, dict]:
    """Build status code and JSON body for validation failures so the user sees which documents are invalid."""
    messages = []
    if validation_errors.get("passport"):
        messages.append(f"Passport: {validation_errors['passport']}")
    if validation_errors.get("g28"):
        messages.append(f"G-28: {validation_errors['g28']}")
    detail_text = " ".join(messages) if messages else "The uploaded document(s) are not valid."
    body = {"detail": detail_text, "validation_errors": dict(validation_errors)}
    return 400, body


@app.post("/extract")
async def extract(
    passport: Optional[UploadFile] = File(None),
    g28: Optional[UploadFile] = File(None),
):
    check_api_key()
    if not passport and not g28:
        raise HTTPException(status_code=400, detail="Upload at least one file: passport or g28.")

    validation_errors: dict = {}
    passport_data: dict = {}
    g28_data: dict = {}

    if passport:
        ct = passport.content_type or ""
        if ct not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Passport file must be PDF or image (JPEG/PNG). Got: {ct}",
            )
        raw = await passport.read()
        val = await validate_passport_file(raw, ct)
        if not val.get("is_valid"):
            validation_errors["passport"] = val.get("reason") or "This document does not appear to be a passport."
        else:
            passport_data = await extract_from_passport_file(raw, ct)

    if g28:
        ct = g28.content_type or ""
        if ct not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"G-28 file must be PDF or image (JPEG/PNG). Got: {ct}",
            )
        raw = await g28.read()
        val = await validate_g28_file(raw, ct)
        if not val.get("is_valid"):
            validation_errors["g28"] = val.get("reason") or "This document does not appear to be Form G-28/A-28."
        else:
            g28_data = await extract_from_g28_file(raw, ct)

    if validation_errors:
        status, body = _validation_error_response(validation_errors)
        raise HTTPException(status_code=status, detail=body)

    merged = merge_extracted(passport_data, g28_data)
    return merged


@app.post("/fill-form")
async def fill_form_endpoint(
    form_url: str = Form(..., description="URL of the form to open and fill"),
    passport: Optional[UploadFile] = File(None),
    g28: Optional[UploadFile] = File(None),
):
    check_api_key()
    form_url = (form_url or "").strip()
    if not form_url:
        raise HTTPException(status_code=400, detail="form_url is required.")
    if not form_url.startswith("http://") and not form_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="form_url must be http or https.")
    if not passport and not g28:
        raise HTTPException(status_code=400, detail="Upload at least one file: passport or g28.")

    validation_errors = {}
    passport_data = {}
    g28_data = {}

    if passport:
        ct = passport.content_type or ""
        if ct not in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid passport file type: {ct}")
        raw = await passport.read()
        val = await validate_passport_file(raw, ct)
        if not val.get("is_valid"):
            validation_errors["passport"] = val.get("reason") or "This document does not appear to be a passport."
        else:
            passport_data = await extract_from_passport_file(raw, ct)

    if g28:
        ct = g28.content_type or ""
        if ct not in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid G-28 file type: {ct}")
        raw = await g28.read()
        val = await validate_g28_file(raw, ct)
        if not val.get("is_valid"):
            validation_errors["g28"] = val.get("reason") or "This document does not appear to be Form G-28/A-28."
        else:
            g28_data = await extract_from_g28_file(raw, ct)

    if validation_errors:
        status, body = _validation_error_response(validation_errors)
        raise HTTPException(status_code=status, detail=body)

    merged = merge_extracted(passport_data, g28_data)
    result = await fill_form(merged, form_url=form_url)
    return {
        "extracted": merged,
        "filled_fields": result["filled"],
        "errors": result["errors"],
        "form_url": result["url"],
        "opened_in_existing_browser": result.get("opened_in_existing_browser", False),
    }


def run():
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
