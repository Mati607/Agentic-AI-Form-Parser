"""
Individual readiness checks over normalized passport and attorney dicts.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from app.extraction_quality.dates import days_from_today, parse_date_fuzzy, utc_today

Severity = Literal["error", "warn", "info"]

Finding = dict[str, Any]


def _non_empty(v: Any) -> bool:
    if v is None:
        return False
    return bool(str(v).strip())


def check_passport_core(passport: dict[str, Any]) -> list[Finding]:
    """Require key identity and travel-document fields when passport section has any data."""
    findings: list[Finding] = []
    if not passport:
        return findings

    required = [
        ("last_name", "passport.last_name", "Passport: last name is missing."),
        ("first_name", "passport.first_name", "Passport: first name is missing."),
        ("passport_number", "passport.passport_number", "Passport: passport number is missing."),
        ("date_of_birth", "passport.date_of_birth", "Passport: date of birth is missing."),
        ("date_of_expiration", "passport.date_of_expiration", "Passport: expiration date is missing."),
    ]
    for key, field_id, msg in required:
        if not _non_empty(passport.get(key)):
            findings.append(
                {
                    "severity": "warn",
                    "code": "passport.missing_field",
                    "field": field_id,
                    "message": msg,
                }
            )
    return findings


def check_passport_dates(passport: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not passport:
        return findings

    exp_raw = passport.get("date_of_expiration")
    exp = parse_date_fuzzy(str(exp_raw) if exp_raw is not None else None)
    if _non_empty(exp_raw) and exp is None:
        findings.append(
            {
                "severity": "warn",
                "code": "passport.expiry_unparsed",
                "field": "passport.date_of_expiration",
                "message": "Passport: expiration date could not be parsed; verify format.",
            }
        )
    elif exp is not None:
        if exp < utc_today():
            findings.append(
                {
                    "severity": "error",
                    "code": "passport.expired",
                    "field": "passport.date_of_expiration",
                    "message": "Passport appears expired based on the extracted expiration date.",
                }
            )
        elif days_from_today(exp) <= 180:
            findings.append(
                {
                    "severity": "warn",
                    "code": "passport.expiring_soon",
                    "field": "passport.date_of_expiration",
                    "message": "Passport expires within six months; many jurisdictions require more validity.",
                }
            )

    dob_raw = passport.get("date_of_birth")
    dob = parse_date_fuzzy(str(dob_raw) if dob_raw is not None else None)
    if _non_empty(dob_raw) and dob is None:
        findings.append(
            {
                "severity": "info",
                "code": "passport.dob_unparsed",
                "field": "passport.date_of_birth",
                "message": "Date of birth could not be parsed; double-check against the scan.",
            }
        )
    elif dob is not None and dob > utc_today():
        findings.append(
            {
                "severity": "error",
                "code": "passport.dob_future",
                "field": "passport.date_of_birth",
                "message": "Date of birth is in the future; likely an extraction or format error.",
            }
        )

    issue_raw = passport.get("date_of_issue")
    issue = parse_date_fuzzy(str(issue_raw) if issue_raw is not None else None)
    if issue and exp and issue > exp:
        findings.append(
            {
                "severity": "warn",
                "code": "passport.issue_after_expiry",
                "field": "passport.date_of_issue",
                "message": "Issue date is after expiration date; verify extracted values.",
            }
        )

    return findings


def check_passport_sex(passport: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not passport:
        return findings
    sex = passport.get("sex")
    if not _non_empty(sex):
        return findings
    normalized = str(sex).strip().upper()[:1]
    if normalized not in ("M", "F", "X"):
        findings.append(
            {
                "severity": "info",
                "code": "passport.sex_nonstandard",
                "field": "passport.sex",
                "message": f'Sex value "{sex}" is not M, F, or X; confirm against the document.',
            }
        )
    return findings


def _digits_only(s: str) -> str:
    return re.sub(r"\D+", "", s)


def check_attorney_contact(attorney: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not attorney:
        return findings

    email = attorney.get("email")
    phone = attorney.get("daytime_telephone") or attorney.get("mobile_telephone")
    if not _non_empty(email) and not _non_empty(phone):
        findings.append(
            {
                "severity": "warn",
                "code": "attorney.no_contact",
                "field": "attorney.email",
                "message": "Attorney: add at least one email or telephone number for USCIS contact.",
            }
        )

    if _non_empty(email) and "@" not in str(email):
        findings.append(
            {
                "severity": "warn",
                "code": "attorney.email_suspicious",
                "field": "attorney.email",
                "message": "Attorney email does not contain @; verify the extracted address.",
            }
        )

    if _non_empty(phone) and len(_digits_only(str(phone))) < 7:
        findings.append(
            {
                "severity": "info",
                "code": "attorney.phone_short",
                "field": "attorney.daytime_telephone",
                "message": "Telephone number has very few digits; confirm country code and formatting.",
            }
        )

    return findings


def check_attorney_identity(attorney: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if not attorney:
        return findings

    if not _non_empty(attorney.get("family_name")):
        findings.append(
            {
                "severity": "warn",
                "code": "attorney.missing_family_name",
                "field": "attorney.family_name",
                "message": "Attorney family (last) name is missing.",
            }
        )
    if not _non_empty(attorney.get("given_name")):
        findings.append(
            {
                "severity": "info",
                "code": "attorney.missing_given_name",
                "field": "attorney.given_name",
                "message": "Attorney given (first) name is missing.",
            }
        )

    bar = attorney.get("bar_number")
    lic = attorney.get("licensing_authority")
    if not _non_empty(bar) and not _non_empty(lic):
        findings.append(
            {
                "severity": "info",
                "code": "attorney.bar_or_authority",
                "field": "attorney.bar_number",
                "message": "Neither bar number nor licensing authority is present; add if visible on G-28.",
            }
        )

    return findings


def check_coverage(passport: dict[str, Any], attorney: dict[str, Any]) -> list[Finding]:
    """Nudge when an entire section is empty (user may have skipped a document)."""
    findings: list[Finding] = []
    if not passport or not any(_non_empty(passport.get(k)) for k in passport):
        findings.append(
            {
                "severity": "info",
                "code": "coverage.no_passport_data",
                "field": "passport",
                "message": "Passport section is empty; upload or extract passport data for beneficiary fields.",
            }
        )
    if not attorney or not any(_non_empty(attorney.get(k)) for k in attorney):
        findings.append(
            {
                "severity": "info",
                "code": "coverage.no_attorney_data",
                "field": "attorney",
                "message": "Attorney section is empty; upload or extract G-28 for representative fields.",
            }
        )
    return findings


def run_all_checks(passport: dict[str, Any], attorney: dict[str, Any]) -> list[Finding]:
    out: list[Finding] = []
    out.extend(check_coverage(passport, attorney))
    out.extend(check_passport_core(passport))
    out.extend(check_passport_dates(passport))
    out.extend(check_passport_sex(passport))
    out.extend(check_attorney_identity(attorney))
    out.extend(check_attorney_contact(attorney))
    return out
