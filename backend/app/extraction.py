import base64
from typing import Any

from baml_py import Image
from baml_client import b


def _to_dict(obj: Any) -> dict:
    if obj is None:
        return {}
    if hasattr(obj, "model_dump"):
        d = obj.model_dump()
    elif hasattr(obj, "dict"):
        d = obj.dict()
    elif hasattr(obj, "__dict__"):
        d = obj.__dict__
    else:
        d = dict(obj) if hasattr(obj, "keys") else {}
    out = {}
    for k, v in d.items():
        if v is None or v == "":
            continue
        if hasattr(v, "model_dump"):
            out[k] = _to_dict(v)
        elif isinstance(v, dict):
            out[k] = {kk: vv for kk, vv in v.items() if vv not in (None, "")}
        else:
            out[k] = v
    return out


def _content_to_image(content: bytes, content_type: str) -> Image:
    b64 = base64.b64encode(content).decode("ascii")
    if content_type == "application/pdf":
        mime = "application/pdf"
    elif "jpeg" in content_type or "jpg" in content_type:
        mime = "image/jpeg"
    else:
        mime = "image/png"
    return Image.from_base64(mime, b64)


async def validate_passport_file(content: bytes, content_type: str) -> dict:
    try:
        img = _content_to_image(content, content_type)
        result_obj = await b.ValidatePassport(doc=img)
        result = {
            "is_valid": getattr(result_obj, "is_valid", False),
            "reason": getattr(result_obj, "reason", None) or None,
        }
        is_valid = result["is_valid"] is True
        reason = result.get("reason") or (
            None if is_valid else "This document does not appear to be a passport."
        )
        return {"is_valid": is_valid, "reason": reason}
    except Exception:
        return {
            "is_valid": False,
            "reason": "Could not validate document. Please upload a clear image or PDF of a passport.",
        }


async def validate_g28_file(content: bytes, content_type: str) -> dict:
    try:
        img = _content_to_image(content, content_type)
        result_obj = await b.ValidateG28(doc=img)
        result = {
            "is_valid": getattr(result_obj, "is_valid", False),
            "reason": getattr(result_obj, "reason", None) or None,
        }
        is_valid = result["is_valid"] is True
        reason = result.get("reason") or (
            None if is_valid else "This document does not appear to be Form G-28/A-28."
        )
        return {"is_valid": is_valid, "reason": reason}
    except Exception:
        return {
            "is_valid": False,
            "reason": "Could not validate document. Please upload a clear image or PDF of Form G-28 or A-28.",
        }


async def extract_from_passport_file(content: bytes, content_type: str) -> dict:
    img = _content_to_image(content, content_type)
    result = await b.ExtractPassport(doc=img)
    return _to_dict(result)


async def extract_from_g28_file(content: bytes, content_type: str) -> dict:
    img = _content_to_image(content, content_type)
    result = await b.ExtractG28(doc=img)
    return _to_dict(result)


def merge_extracted(passport_data: dict, g28_data: dict) -> dict:
    passport = dict(passport_data or {})
    if g28_data.get("passport"):
        passport.update(g28_data["passport"])
    attorney = dict(g28_data.get("attorney") or {})
    return {
        "passport": passport,
        "attorney": attorney,
    }
