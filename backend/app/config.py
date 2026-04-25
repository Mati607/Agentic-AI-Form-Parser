import os
from pathlib import Path

def get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()

FORM_URL = get_env("FORM_URL", "https://mendrika-alma.github.io/form-submission/")

CHROME_CDP_URL = get_env("CHROME_CDP_URL", "http://127.0.0.1:9222")
CHROME_CDP_PORT = get_env("CHROME_CDP_PORT", "9222")
CHROME_CDP_PROFILE_DIR = get_env("CHROME_CDP_PROFILE_DIR", "/tmp/alma-chrome-cdp")

GOOGLE_API_KEY = get_env("GOOGLE_API_KEY")

HEADLESS = get_env("HEADLESS", "true").lower() in ("1", "true", "yes")

# SQLite store for saved extraction sessions (server-side history).
_backend_root = Path(__file__).resolve().parent.parent
_default_db = _backend_root / "data" / "extraction_sessions.db"
EXTRACTION_DB_PATH = Path(get_env("EXTRACTION_DB_PATH", str(_default_db)))

# Intake pipeline: stored uploads and rendered page images (PII — secure your host).
_default_intake = _backend_root / "data" / "intake"
INTAKE_STORAGE_DIR = Path(get_env("INTAKE_STORAGE_DIR", str(_default_intake)))
INTAKE_RETENTION_DAYS = int(get_env("INTAKE_RETENTION_DAYS", "30") or "30")
# HMAC secret for short-lived artifact download URLs (set in production).
INTAKE_SIGNING_SECRET = get_env("INTAKE_SIGNING_SECRET", "change-me-in-production")

# Comma-separated origins for CORS; if empty, only local Vite defaults are used in main.py
ALLOWED_ORIGINS = get_env("ALLOWED_ORIGINS", "")
