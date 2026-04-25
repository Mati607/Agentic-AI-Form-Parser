from __future__ import annotations

import base64
import hashlib
import hmac
import time


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def sign_artifact_download(artifact_id: int, exp_unix: int, secret: str) -> str:
    msg = f"{artifact_id}:{exp_unix}".encode("utf-8")
    mac = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).digest()
    return _b64url(mac)


def verify_artifact_download(artifact_id: int, exp_unix: int, sig: str, secret: str) -> bool:
    if exp_unix < int(time.time()):
        return False
    try:
        expected = sign_artifact_download(artifact_id, exp_unix, secret)
        return hmac.compare_digest(expected, sig)
    except Exception:
        return False
