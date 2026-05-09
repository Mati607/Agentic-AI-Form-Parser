"""
Flatten a saved extraction session into a CSV suitable for spreadsheets and mail merge.
"""

from __future__ import annotations

import csv
import io
from typing import Any

from app.field_mappings import list_sections_and_keys


def _cell(v: Any) -> str:
    if v is None:
        return ""
    return str(v).replace("\r\n", " ").replace("\n", " ").strip()


def session_to_csv_text(row: dict[str, Any]) -> str:
    """
    Build UTF-8 CSV text with a metadata header section and one column per mapped field.

    The first rows are session metadata; remaining rows pair field_id with value.
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["section", "key", "field_id", "value"])

    extracted = row.get("extracted") if isinstance(row.get("extracted"), dict) else {}
    passport = extracted.get("passport") if isinstance(extracted.get("passport"), dict) else {}
    attorney = extracted.get("attorney") if isinstance(extracted.get("attorney"), dict) else {}

    for section, key in list_sections_and_keys():
        src = passport if section == "passport" else attorney
        val = src.get(key)
        writer.writerow([section, key, f"{section}.{key}", _cell(val)])

    readiness = row.get("readiness") if isinstance(row.get("readiness"), dict) else {}
    writer.writerow([])
    writer.writerow(["__meta__", "session_id", "id", _cell(row.get("id"))])
    writer.writerow(["__meta__", "title", "title", _cell(row.get("title"))])
    writer.writerow(["__meta__", "created_at", "created_at", _cell(row.get("created_at"))])
    writer.writerow(["__meta__", "updated_at", "updated_at", _cell(row.get("updated_at"))])
    writer.writerow(["__meta__", "passport_filename", "passport_filename", _cell(row.get("passport_filename"))])
    writer.writerow(["__meta__", "g28_filename", "g28_filename", _cell(row.get("g28_filename"))])
    writer.writerow(["__meta__", "default_form_url", "default_form_url", _cell(row.get("default_form_url"))])
    writer.writerow(["__meta__", "readiness_score", "readiness.score", _cell(readiness.get("score"))])
    writer.writerow(["__meta__", "readiness_grade", "readiness.grade", _cell(readiness.get("grade"))])
    writer.writerow(["__meta__", "readiness_summary", "readiness.summary", _cell(readiness.get("summary"))])

    return buf.getvalue()
