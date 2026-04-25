from __future__ import annotations

import json
from typing import Any


def merged_to_field_assertions(merged: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Flatten { passport: {...}, attorney: {...} } into field_path rows for review UI.
    """
    out: list[dict[str, Any]] = []
    if not isinstance(merged, dict):
        return out
    for section in ("passport", "attorney"):
        block = merged.get(section)
        if not isinstance(block, dict):
            continue
        for key, val in block.items():
            if val is None or val == "":
                continue
            fp = f"{section}.{key}"
            try:
                vjson = json.dumps(val, ensure_ascii=False)
            except (TypeError, ValueError):
                vjson = json.dumps(str(val), ensure_ascii=False)
            out.append(
                {
                    "field_path": fp,
                    "value_json": vjson,
                    "confidence": 0.85,
                    "source": "baml",
                    "reviewer_note": None,
                }
            )
    out.sort(key=lambda r: r["field_path"])
    return out


def parse_value_json(value_json: str) -> Any:
    try:
        return json.loads(value_json)
    except json.JSONDecodeError:
        return value_json
