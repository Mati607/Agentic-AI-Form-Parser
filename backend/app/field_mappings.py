"""
Single source of truth for mapping extracted passport / attorney data to HTML form labels.

Used by Playwright form filling and by the preview API so the UI can show exactly which
values would be sent to the browser.
"""

from __future__ import annotations

from typing import Any

# (section, field_key, list of label / placeholder hints tried in order)
FIELD_MAPPINGS: list[tuple[str, str, list[str]]] = [
    # Part 1 - Attorney
    ("attorney", "online_account_number", ["Online Account Number", "1. Online Account Number"]),
    ("attorney", "family_name", ["2.a. Family Name", "Family Name (Last Name)"]),
    ("attorney", "given_name", ["2.b. Given Name", "Given Name (First Name)"]),
    ("attorney", "middle_name", ["2.c. Middle Name", "Middle Name"]),
    ("attorney", "street_number_and_name", ["3.a. Street Number and Name", "Street Number and Name"]),
    ("attorney", "apt_ste_flr", ["Apt. Ste. Flr.", "Apt"]),
    ("attorney", "city", ["3.c. City", "City"]),
    ("attorney", "state", ["3.d. State", "State"]),
    ("attorney", "zip_code", ["3.e. ZIP Code", "ZIP Code"]),
    ("attorney", "country", ["3.f. Country", "Country"]),
    ("attorney", "daytime_telephone", ["4. Daytime Telephone Number", "Daytime Telephone"]),
    ("attorney", "mobile_telephone", ["5. Mobile Telephone Number", "Mobile Telephone"]),
    ("attorney", "email", ["6. Email Address", "Email Address"]),
    ("attorney", "licensing_authority", ["Licensing Authority"]),
    ("attorney", "bar_number", ["1.b. Bar Number", "Bar Number"]),
    ("attorney", "law_firm_or_organization", ["1.d. Name of Law Firm or Organization", "Law Firm"]),
    # Part 3 - Passport (beneficiary)
    ("passport", "last_name", ["1.a. Last Name", "Last Name"]),
    ("passport", "first_name", ["1.b. First Name(s)", "First Name"]),
    ("passport", "middle_name", ["1.c. Middle Name(s)", "Middle Name(s)"]),
    ("passport", "passport_number", ["2. Passport Number", "Passport Number"]),
    ("passport", "country_of_issue", ["3. Country of Issue", "Country of Issue"]),
    ("passport", "nationality", ["4. Nationality", "Nationality"]),
    ("passport", "date_of_birth", ["5.a. Date of Birth", "Date of Birth"]),
    ("passport", "place_of_birth", ["5.b. Place of Birth", "Place of Birth"]),
    ("passport", "sex", ["6. Sex", "Sex"]),
    ("passport", "date_of_issue", ["7.a. Date of Issue", "Date of Issue"]),
    ("passport", "date_of_expiration", ["7.b. Date of Expiration", "Date of Expiration"]),
]


def _title_case_key(key: str) -> str:
    """Turn snake_case into Title Case With Spaces (rough match for legacy dict keys)."""
    return key.replace("_", " ").title()


def get_mapped_value(extracted: dict[str, Any] | None, section: str, key: str) -> str | None:
    """
    Resolve a field value from merged extraction output.

    Tries exact key, then a title-cased variant, mirroring Playwright fill behavior.
    Returns None if missing or blank after strip.
    """
    if not extracted:
        return None
    section_data = extracted.get(section)
    if not isinstance(section_data, dict):
        return None
    raw = section_data.get(key)
    if raw is None:
        raw = section_data.get(_title_case_key(key))
    if raw is None:
        return None
    text = str(raw).strip()
    return text if text else None


def list_sections_and_keys() -> list[tuple[str, str]]:
    """Stable list of (section, key) pairs in mapping order."""
    return [(section, key) for section, key, _ in FIELD_MAPPINGS]


def labels_for_field(section: str, key: str) -> list[str]:
    """Return label hints for a section/key, or empty list if unmapped."""
    for s, k, labels in FIELD_MAPPINGS:
        if s == section and k == key:
            return list(labels)
    return []
