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
