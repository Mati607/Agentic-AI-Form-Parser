import os

def get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()

FORM_URL = get_env("FORM_URL", "https://mendrika-alma.github.io/form-submission/")

CHROME_CDP_URL = get_env("CHROME_CDP_URL", "http://127.0.0.1:9222")
CHROME_CDP_PORT = get_env("CHROME_CDP_PORT", "9222")
CHROME_CDP_PROFILE_DIR = get_env("CHROME_CDP_PROFILE_DIR", "/tmp/alma-chrome-cdp")

GOOGLE_API_KEY = get_env("GOOGLE_API_KEY")

HEADLESS = get_env("HEADLESS", "true").lower() in ("1", "true", "yes")
