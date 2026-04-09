"""Unit tests for app.field_mappings."""

import pytest

from app.field_mappings import (
    FIELD_MAPPINGS,
    get_mapped_value,
    labels_for_field,
    list_sections_and_keys,
)


def test_field_mappings_non_empty():
    assert len(FIELD_MAPPINGS) >= 10
    for section, key, labels in FIELD_MAPPINGS:
        assert section in ("passport", "attorney")
        assert key
        assert isinstance(labels, list) and labels


def test_get_mapped_value_exact_key():
    extracted = {"passport": {"first_name": "  Ana  "}, "attorney": {}}
    assert get_mapped_value(extracted, "passport", "first_name") == "Ana"


def test_get_mapped_value_title_case_fallback():
    extracted = {"passport": {"First Name": "Bob"}, "attorney": {}}
    assert get_mapped_value(extracted, "passport", "first_name") == "Bob"


def test_get_mapped_value_missing_section():
    assert get_mapped_value({"passport": {}}, "attorney", "email") is None


def test_get_mapped_value_blank_becomes_none():
    extracted = {"attorney": {"email": "   "}, "passport": {}}
    assert get_mapped_value(extracted, "attorney", "email") is None


def test_labels_for_field_known():
    labs = labels_for_field("passport", "passport_number")
    assert "Passport Number" in " ".join(labs)


def test_labels_for_field_unknown():
    assert labels_for_field("passport", "not_a_real_key") == []


def test_list_sections_and_keys_matches_mappings():
    pairs = list_sections_and_keys()
    assert len(pairs) == len(FIELD_MAPPINGS)
    assert pairs[0] == (FIELD_MAPPINGS[0][0], FIELD_MAPPINGS[0][1])


@pytest.mark.parametrize(
    "bad",
    [None, {}, {"passport": "x"}, {"passport": None}],
)
def test_get_mapped_value_resilient(bad):
    assert get_mapped_value(bad, "passport", "last_name") is None
