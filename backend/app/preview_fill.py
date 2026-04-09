"""
Server-side preview of which mapped fields would receive values during Playwright fill.

Does not open a browser or call any LLM; useful for QA and for the UI before running fill.
"""

from __future__ import annotations

from typing import Any

from app.field_mappings import FIELD_MAPPINGS, get_mapped_value


def normalize_merged_extracted(raw: dict[str, Any] | None) -> dict[str, Any]:
    """
    Ensure merged extraction shape { passport: dict, attorney: dict }.

    Unknown top-level keys are ignored; non-dict passport/attorney become empty dicts.
    """
    if not raw or not isinstance(raw, dict):
        return {"passport": {}, "attorney": {}}
    p = raw.get("passport")
    a = raw.get("attorney")
    return {
        "passport": dict(p) if isinstance(p, dict) else {},
        "attorney": dict(a) if isinstance(a, dict) else {},
    }


def build_fill_preview(extracted: dict[str, Any]) -> dict[str, Any]:
    """
    Build a row per FIELD_MAPPINGS entry plus aggregate stats.

    Returns:
      rows: list of dicts with section, key, primary_label, label_hints, value, would_attempt_fill
      stats: mapped_with_value, mapped_total, sections: { attorney: n, passport: n } counts with values
    """
    normalized = normalize_merged_extracted(extracted)
    rows: list[dict[str, Any]] = []
    section_counts: dict[str, int] = {"attorney": 0, "passport": 0}

    for section, key, labels in FIELD_MAPPINGS:
        value = get_mapped_value(normalized, section, key)
        would = bool(value)
        if would:
            section_counts[section] = section_counts.get(section, 0) + 1
        rows.append(
            {
                "section": section,
                "key": key,
                "field_id": f"{section}.{key}",
                "primary_label": labels[0] if labels else key,
                "label_hints": list(labels),
                "value": value,
                "would_attempt_fill": would,
            }
        )

    with_value = sum(1 for r in rows if r["would_attempt_fill"])
    return {
        "rows": rows,
        "stats": {
            "mapped_with_value": with_value,
            "mapped_total": len(rows),
            "by_section": section_counts,
        },
        "extracted": normalized,
    }
