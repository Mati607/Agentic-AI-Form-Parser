"""
Best-effort parsing of human-entered dates from OCR / LLM extraction output.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone


def _strip_noise(s: str) -> str:
    t = s.strip()
    t = re.sub(r"\s+", " ", t)
    return t


def parse_date_fuzzy(value: str | None) -> date | None:
    """
    Parse a date string into a date, or None if parsing fails.

    Supports common ISO and locale-like patterns; avoids extra dependencies.
    """
    if value is None:
        return None
    raw = _strip_noise(str(value))
    if not raw:
        return None

    # Leading YYYY-MM-DD or YYYY/MM/DD (take first 10 chars if longer)
    for sep in ("-", "/"):
        m = re.match(r"^(\d{4})" + re.escape(sep) + r"(\d{1,2})" + re.escape(sep) + r"(\d{1,2})", raw)
        if m:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                return date(y, mo, d)
            except ValueError:
                return None

    # DD/MM/YYYY or MM/DD/YYYY (prefer day-first for international passports)
    m = re.match(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})$", raw)
    if m:
        a, b, y_raw = int(m.group(1)), int(m.group(2)), m.group(3)
        y = int(y_raw) if len(y_raw) == 4 else 2000 + int(y_raw) if int(y_raw) < 70 else 1900 + int(y_raw)
        # If first part > 12, it must be day-first
        if a > 12:
            try:
                return date(y, b, a)
            except ValueError:
                return None
        if b > 12:
            try:
                return date(y, a, b)
            except ValueError:
                return None
        # Ambiguous: assume DD/MM/YYYY (common outside US)
        try:
            return date(y, b, a)
        except ValueError:
            try:
                return date(y, a, b)
            except ValueError:
                return None

    return None


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def days_from_today(d: date) -> int:
    return (d - utc_today()).days
