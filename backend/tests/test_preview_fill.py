"""Tests for preview_fill normalization and preview rows."""

from app.preview_fill import build_fill_preview, normalize_merged_extracted


def test_normalize_empty():
    assert normalize_merged_extracted(None) == {"passport": {}, "attorney": {}}
    assert normalize_merged_extracted({}) == {"passport": {}, "attorney": {}}


def test_normalize_coerces_non_dict_sections():
    raw = {"passport": "nope", "attorney": [1, 2]}
    assert normalize_merged_extracted(raw) == {"passport": {}, "attorney": {}}


def test_normalize_keeps_dicts():
    raw = {
        "passport": {"first_name": "X"},
        "attorney": {"email": "a@b.co"},
        "extra": 1,
    }
    out = normalize_merged_extracted(raw)
    assert out["passport"] == {"first_name": "X"}
    assert out["attorney"] == {"email": "a@b.co"}
    assert "extra" not in out


def test_build_fill_preview_stats():
    extracted = {
        "passport": {"first_name": "Jane", "last_name": "Doe"},
        "attorney": {"family_name": "Smith", "email": "e@example.com"},
    }
    preview = build_fill_preview(extracted)
    assert "rows" in preview and "stats" in preview and "extracted" in preview
    stats = preview["stats"]
    assert stats["mapped_total"] == len(preview["rows"])
    assert stats["mapped_with_value"] >= 4
    assert stats["by_section"]["passport"] >= 2
    assert stats["by_section"]["attorney"] >= 2


def test_build_fill_preview_row_shape():
    preview = build_fill_preview({"passport": {"sex": "M"}, "attorney": {}})
    row = next(r for r in preview["rows"] if r["key"] == "sex")
    assert row["section"] == "passport"
    assert row["would_attempt_fill"] is True
    assert row["value"] == "M"
    assert row["field_id"] == "passport.sex"
