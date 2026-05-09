"""
Additional heuristic readiness checks beyond checks.py (placeholders, address completeness, etc.).
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Literal

from app.extraction_quality.dates import parse_date_fuzzy, utc_today

Severity = Literal["error", "warn", "info"]
Finding = dict[str, Any]

_PLACEHOLDER_RE = re.compile(
    r"^\s*(n/?a|tbd|todo|unknown|none|null|test|sample|xxx+|\-{3,})\s*$",
    re.IGNORECASE,
)
_DUMMY_EMAIL_RE = re.compile(r"test@test|example\.com|user@user|yourname@|email@email", re.IGNORECASE)

_US_STATES = {
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
    "DC",
}

_PUBLIC_EMAIL_DOMAINS = (
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "icloud.com",
    "aol.com",
    "protonmail.com",
    "live.com",
    "msn.com",
)


def _non_empty(v: Any) -> bool:
    if v is None:
        return False
    return bool(str(v).strip())


def _digits_only(s: str) -> str:
    return re.sub(r"\D+", "", s)


def _is_placeholder_text(v: Any) -> bool:
    if v is None:
        return False
    t = str(v).strip()
    if not t:
        return False
    if _PLACEHOLDER_RE.match(t):
        return True
    if _DUMMY_EMAIL_RE.search(t):
        return True
    return False


def _all_caps_words(s: str) -> bool:
    letters = [c for c in s if c.isalpha()]
    if len(letters) < 3:
        return False
    return all(c.isupper() for c in letters)


def check_passport_number_format(passport: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not passport:
        return findings
    raw = passport.get("passport_number")
    if not _non_empty(raw):
        return findings
    s = str(raw).strip()
    alnum = re.sub(r"[^A-Za-z0-9]", "", s)
    if len(alnum) < 4 or len(alnum) > 20:
        findings.append(
            {
                "severity": "info",
                "code": "passport.passport_number_suspicious",
                "field": "passport.passport_number",
                "message": "Passport number length or charset looks unusual; verify against the data page.",
            }
        )
    return findings


def check_passport_name_lengths(passport: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not passport:
        return findings
    for key, label in (
        ("first_name", "passport.first_name"),
        ("last_name", "passport.last_name"),
        ("middle_name", "passport.middle_name"),
    ):
        v = passport.get(key)
        if not _non_empty(v):
            continue
        t = str(v).strip()
        if len(t) == 1:
            findings.append(
                {
                    "severity": "info",
                    "code": "passport.name_too_short",
                    "field": label,
                    "message": f"{label.split('.')[-1].replace('_', ' ')} is a single character; confirm against the document.",
                }
            )
    return findings


def check_passport_supporting_demographics(passport: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not passport or not any(_non_empty(passport.get(k)) for k in passport):
        return findings
    has_core = any(
        _non_empty(passport.get(k)) for k in ("passport_number", "date_of_birth", "last_name", "first_name")
    )
    if not has_core:
        return findings
    if not _non_empty(passport.get("nationality")):
        findings.append(
            {
                "severity": "info",
                "code": "passport.nationality_missing",
                "field": "passport.nationality",
                "message": "Nationality is missing while other passport fields are present.",
            }
        )
    if not _non_empty(passport.get("country_of_issue")):
        findings.append(
            {
                "severity": "info",
                "code": "passport.country_issue_missing",
                "field": "passport.country_of_issue",
                "message": "Country of issue is missing while other passport fields are present.",
            }
        )
    if not _non_empty(passport.get("place_of_birth")):
        findings.append(
            {
                "severity": "info",
                "code": "passport.place_of_birth_missing",
                "field": "passport.place_of_birth",
                "message": "Place of birth is missing while other passport fields are present.",
            }
        )
    return findings


def check_passport_nationality_place_consistency(passport: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not passport:
        return findings
    nat = passport.get("nationality")
    pob = passport.get("place_of_birth")
    if not _non_empty(nat) or not _non_empty(pob):
        return findings
    nat_t = str(nat).strip().lower()
    pob_t = str(pob).strip().lower()
    tokens = re.findall(r"[a-z]{3,}", nat_t)
    if not tokens:
        return findings
    if not any(tok in pob_t for tok in tokens):
        findings.append(
            {
                "severity": "info",
                "code": "passport.nationality_place_mismatch",
                "field": "passport.nationality",
                "message": "Nationality token does not appear in place of birth; verify both fields on the scan.",
            }
        )
    return findings


def check_passport_issue_vs_nationality(passport: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not passport:
        return findings
    iss = passport.get("country_of_issue")
    nat = passport.get("nationality")
    if not _non_empty(iss) or not _non_empty(nat):
        return findings
    a = re.sub(r"[^a-z0-9]+", "", str(iss).lower())
    b = re.sub(r"[^a-z0-9]+", "", str(nat).lower())
    if len(a) < 3 or len(b) < 3:
        return findings
    if a not in b and b not in a:
        findings.append(
            {
                "severity": "info",
                "code": "passport.country_mismatch_issue_nationality",
                "field": "passport.country_of_issue",
                "message": "Issuing country and nationality strings differ; confirm both against the document.",
            }
        )
    return findings


def check_placeholders_passport(passport: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not passport:
        return findings
    for key in list(passport.keys()):
        if _is_placeholder_text(passport.get(key)):
            findings.append(
                {
                    "severity": "warn",
                    "code": "passport.placeholder_value",
                    "field": f"passport.{key}",
                    "message": f'Passport field "{key}" looks like a placeholder or dummy value.',
                }
            )
    return findings


def check_placeholders_attorney(attorney: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not attorney:
        return findings
    for key in list(attorney.keys()):
        if _is_placeholder_text(attorney.get(key)):
            findings.append(
                {
                    "severity": "warn",
                    "code": "attorney.placeholder_value",
                    "field": f"attorney.{key}",
                    "message": f'Attorney field "{key}" looks like a placeholder or dummy value.',
                }
            )
    return findings


def check_attorney_address_block(attorney: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not attorney:
        return findings
    street = attorney.get("street_number_and_name")
    city = attorney.get("city")
    state = attorney.get("state")
    z = attorney.get("zip_code")
    country = attorney.get("country")
    any_addr = any(_non_empty(x) for x in (street, city, state, z, country))
    if not any_addr:
        return findings
    partial = []
    if _non_empty(street) and not _non_empty(city):
        partial.append("city")
    if _non_empty(street) and _non_empty(city) and not _non_empty(z):
        partial.append("postal code")
    if _non_empty(street) and _non_empty(city) and not _non_empty(state):
        partial.append("state/province")
    if partial:
        findings.append(
            {
                "severity": "info",
                "code": "attorney.address_incomplete",
                "field": "attorney.street_number_and_name",
                "message": "Attorney mailing address looks incomplete (" + ", ".join(partial) + " missing).",
            }
        )

    country_l = str(country).strip().lower() if _non_empty(country) else ""
    usish = not country_l or "u.s" in country_l or country_l in ("us", "usa", "united states")
    if usish and _non_empty(z):
        d = _digits_only(str(z))
        if len(d) > 0 and len(d) < 5:
            findings.append(
                {
                    "severity": "info",
                    "code": "attorney.zip_non_numeric",
                    "field": "attorney.zip_code",
                    "message": "ZIP/postal code has very few digits for a US-style address.",
                }
            )

    if usish and _non_empty(state):
        st = str(state).strip().upper()
        if len(st) == 2 and st not in _US_STATES:
            findings.append(
                {
                    "severity": "info",
                    "code": "attorney.state_suspicious",
                    "field": "attorney.state",
                    "message": f'State code "{state}" is not a recognized US postal abbreviation.',
                }
            )
    return findings


def check_attorney_firm_vs_name(attorney: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not attorney:
        return findings
    firm = attorney.get("law_firm_or_organization")
    fam = attorney.get("family_name")
    given = attorney.get("given_name")
    if not _non_empty(firm):
        return findings
    if (not _non_empty(fam) or len(str(fam).strip()) < 2) and (not _non_empty(given) or len(str(given).strip()) < 2):
        findings.append(
            {
                "severity": "info",
                "code": "attorney.firm_without_name",
                "field": "attorney.law_firm_or_organization",
                "message": "Law firm or organization is set but attorney personal names look incomplete.",
            }
        )
    return findings


def check_attorney_duplicate_phones(attorney: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not attorney:
        return findings
    d1 = attorney.get("daytime_telephone")
    d2 = attorney.get("mobile_telephone")
    if not _non_empty(d1) or not _non_empty(d2):
        return findings
    if _digits_only(str(d1)) == _digits_only(str(d2)) and len(_digits_only(str(d1))) >= 7:
        findings.append(
            {
                "severity": "info",
                "code": "attorney.duplicate_phones",
                "field": "attorney.daytime_telephone",
                "message": "Daytime and mobile telephone numbers are identical after normalization.",
            }
        )
    return findings


def check_name_casing_passport(passport: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not passport:
        return findings
    for key in ("first_name", "last_name"):
        v = passport.get(key)
        if _non_empty(v) and _all_caps_words(str(v)):
            findings.append(
                {
                    "severity": "info",
                    "code": "passport.all_caps_name",
                    "field": f"passport.{key}",
                    "message": "Passport name appears entirely in uppercase.",
                }
            )
            break
    return findings


def check_name_casing_attorney(attorney: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not attorney:
        return findings
    for key in ("family_name", "given_name"):
        v = attorney.get(key)
        if _non_empty(v) and _all_caps_words(str(v)):
            findings.append(
                {
                    "severity": "info",
                    "code": "attorney.all_caps_name",
                    "field": f"attorney.{key}",
                    "message": "Attorney name appears entirely in uppercase.",
                }
            )
            break
    return findings


def check_middle_initial_passport(passport: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not passport:
        return findings
    mid = passport.get("middle_name")
    if not _non_empty(mid):
        return findings
    t = str(mid).strip()
    if re.match(r"^[A-Za-z]\.?$", t):
        findings.append(
            {
                "severity": "info",
                "code": "passport.middle_initial_only",
                "field": "passport.middle_name",
                "message": "Middle name is a single initial; expand if the passport shows a full middle name.",
            }
        )
    return findings


def check_passport_validity_span(passport: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not passport:
        return findings
    issue = parse_date_fuzzy(str(passport.get("date_of_issue") or ""))
    exp = parse_date_fuzzy(str(passport.get("date_of_expiration") or ""))
    if issue and exp and exp > issue:
        years = (exp - issue).days / 365.25
        if years > 12:
            findings.append(
                {
                    "severity": "info",
                    "code": "passport.expiry_long_horizon",
                    "field": "passport.date_of_expiration",
                    "message": "Validity window is longer than 12 years; confirm issue and expiration dates.",
                }
            )
    return findings


def check_minor_hint(passport: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not passport:
        return findings
    dob = parse_date_fuzzy(str(passport.get("date_of_birth") or ""))
    if not dob:
        return findings
    today = utc_today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < 18:
        findings.append(
            {
                "severity": "info",
                "code": "passport.minor_age_hint",
                "field": "passport.date_of_birth",
                "message": "Beneficiary appears under 18 based on extracted date of birth; verify minor-specific requirements.",
            }
        )
    return findings


def check_attorney_public_email(attorney: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not attorney:
        return findings
    em = attorney.get("email")
    if not _non_empty(em) or "@" not in str(em):
        return findings
    lower = str(em).strip().lower()
    domain = lower.split("@", 1)[-1].strip()
    if domain in _PUBLIC_EMAIL_DOMAINS:
        findings.append(
            {
                "severity": "info",
                "code": "attorney.email_public_domain",
                "field": "attorney.email",
                "message": "Attorney email uses a public mailbox domain; confirm if a firm address is required.",
            }
        )
    return findings


def check_online_account_note(attorney: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not attorney:
        return findings
    acct = attorney.get("online_account_number")
    if _non_empty(acct):
        findings.append(
            {
                "severity": "info",
                "code": "attorney.online_account_present",
                "field": "attorney.online_account_number",
                "message": "USCIS online account number is populated; verify it matches the filing attorney profile.",
            }
        )
    return findings


def run_extended_checks(passport: dict[str, Any], attorney: dict[str, Any]) -> list[Finding]:
    out: list[Finding] = []
    out.extend(check_passport_number_format(passport))
    out.extend(check_passport_name_lengths(passport))
    out.extend(check_passport_supporting_demographics(passport))
    out.extend(check_passport_nationality_place_consistency(passport))
    out.extend(check_passport_issue_vs_nationality(passport))
    out.extend(check_placeholders_passport(passport))
    out.extend(check_placeholders_attorney(attorney))
    out.extend(check_attorney_address_block(attorney))
    out.extend(check_attorney_firm_vs_name(attorney))
    out.extend(check_attorney_duplicate_phones(attorney))
    out.extend(check_name_casing_passport(passport))
    out.extend(check_name_casing_attorney(attorney))
    out.extend(check_middle_initial_passport(passport))
    out.extend(check_passport_validity_span(passport))
    out.extend(check_minor_hint(passport))
    out.extend(check_attorney_public_email(attorney))
    out.extend(check_online_account_note(attorney))
    return out
