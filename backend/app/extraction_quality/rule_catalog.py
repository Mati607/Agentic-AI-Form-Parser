"""
Static metadata for readiness rule codes: titles, categories, remediation hints.

Used to power documentation endpoints and to enrich API responses for reviewers.
"""

from __future__ import annotations

from typing import Any, TypedDict


class RuleCatalogEntry(TypedDict, total=False):
    code: str
    title: str
    category: str
    default_severity: str
    summary: str
    remediation: str
    related_fields: list[str]
    references: list[str]


# Every code emitted by checks.py and checks_extended.py should have an entry here.
RULE_CATALOG: list[RuleCatalogEntry] = [
    {
        "code": "coverage.no_passport_data",
        "title": "Passport section empty",
        "category": "coverage",
        "default_severity": "info",
        "summary": "No passport fields were extracted or merged into the session.",
        "remediation": "Upload a passport image or PDF and re-run extraction, or paste structured passport data before filing.",
        "related_fields": ["passport"],
        "references": ["README: Main functionality / Data extraction"],
    },
    {
        "code": "coverage.no_attorney_data",
        "title": "Attorney section empty",
        "category": "coverage",
        "default_severity": "info",
        "summary": "No G-28 / representative fields are present in the merged payload.",
        "remediation": "Upload Form G-28 (or equivalent representative form) and extract representative contact details.",
        "related_fields": ["attorney"],
        "references": ["README: Main functionality / Data extraction"],
    },
    {
        "code": "passport.missing_field",
        "title": "Passport core field missing",
        "category": "passport.identity",
        "default_severity": "warn",
        "summary": "A high-value passport field expected for downstream forms is blank.",
        "remediation": "Compare the scan to the extracted JSON; correct OCR or manual typos for the flagged key.",
        "related_fields": [
            "passport.last_name",
            "passport.first_name",
            "passport.passport_number",
            "passport.date_of_birth",
            "passport.date_of_expiration",
        ],
        "references": ["ICAO 9303 (travel document data elements)"],
    },
    {
        "code": "passport.expiry_unparsed",
        "title": "Passport expiration not parsed",
        "category": "passport.dates",
        "default_severity": "warn",
        "summary": "The expiration string could not be normalized to a calendar date.",
        "remediation": "Re-type the expiration using ISO YYYY-MM-DD or a clear DD Mon YYYY style.",
        "related_fields": ["passport.date_of_expiration"],
        "references": [],
    },
    {
        "code": "passport.expired",
        "title": "Passport appears expired",
        "category": "passport.dates",
        "default_severity": "error",
        "summary": "Parsed expiration date is before today (UTC).",
        "remediation": "Confirm the document is current; renew the passport before submission if required.",
        "related_fields": ["passport.date_of_expiration"],
        "references": [],
    },
    {
        "code": "passport.expiring_soon",
        "title": "Passport expiring within six months",
        "category": "passport.dates",
        "default_severity": "warn",
        "summary": "Many filing contexts require additional validity beyond the travel date.",
        "remediation": "Check program-specific validity rules and renew early if needed.",
        "related_fields": ["passport.date_of_expiration"],
        "references": [],
    },
    {
        "code": "passport.dob_unparsed",
        "title": "Date of birth not parsed",
        "category": "passport.dates",
        "default_severity": "info",
        "summary": "Birth date text did not parse to a concrete date.",
        "remediation": "Normalize to an unambiguous format and verify against the physical document.",
        "related_fields": ["passport.date_of_birth"],
        "references": [],
    },
    {
        "code": "passport.dob_future",
        "title": "Date of birth in the future",
        "category": "passport.dates",
        "default_severity": "error",
        "summary": "Parsed DOB is after today's date, which is almost always a data error.",
        "remediation": "Fix digit transposition or month/day swap from OCR.",
        "related_fields": ["passport.date_of_birth"],
        "references": [],
    },
    {
        "code": "passport.issue_after_expiry",
        "title": "Issue date after expiration",
        "category": "passport.dates",
        "default_severity": "warn",
        "summary": "Issue and expiration ordering is inconsistent with typical travel documents.",
        "remediation": "Re-read both dates from the MRZ or printed fields; one may be misread.",
        "related_fields": ["passport.date_of_issue", "passport.date_of_expiration"],
        "references": [],
    },
    {
        "code": "passport.sex_nonstandard",
        "title": "Sex marker not M/F/X",
        "category": "passport.demographics",
        "default_severity": "info",
        "summary": "The extracted sex value is not one of the common single-letter markers.",
        "remediation": "Map the issuing authority's encoding to the form's allowed values.",
        "related_fields": ["passport.sex"],
        "references": [],
    },
    {
        "code": "attorney.no_contact",
        "title": "No attorney email or phone",
        "category": "attorney.contact",
        "default_severity": "warn",
        "summary": "USCIS and many agencies require at least one reliable contact channel.",
        "remediation": "Add a daytime phone or email from the signed G-28 block.",
        "related_fields": ["attorney.email", "attorney.daytime_telephone", "attorney.mobile_telephone"],
        "references": [],
    },
    {
        "code": "attorney.email_suspicious",
        "title": "Email missing @",
        "category": "attorney.contact",
        "default_severity": "warn",
        "summary": "The attorney email string does not look like a standard address.",
        "remediation": "Correct OCR artifacts (e.g., spaces) and ensure a full mailbox@domain form.",
        "related_fields": ["attorney.email"],
        "references": [],
    },
    {
        "code": "attorney.phone_short",
        "title": "Telephone has very few digits",
        "category": "attorney.contact",
        "default_severity": "info",
        "summary": "After stripping formatting, the phone has fewer than seven digits.",
        "remediation": "Include country/area codes as printed; avoid truncating leading zeros.",
        "related_fields": ["attorney.daytime_telephone", "attorney.mobile_telephone"],
        "references": [],
    },
    {
        "code": "attorney.missing_family_name",
        "title": "Attorney family name missing",
        "category": "attorney.identity",
        "default_severity": "warn",
        "summary": "Representative last name is required on most signed representative forms.",
        "remediation": "Transcribe the attorney block carefully; confirm spelling against the bar card.",
        "related_fields": ["attorney.family_name"],
        "references": [],
    },
    {
        "code": "attorney.missing_given_name",
        "title": "Attorney given name missing",
        "category": "attorney.identity",
        "default_severity": "info",
        "summary": "First name is blank while other representative data exists.",
        "remediation": "Add the given name as it appears on the G-28 signature line.",
        "related_fields": ["attorney.given_name"],
        "references": [],
    },
    {
        "code": "attorney.bar_or_authority",
        "title": "Bar number and licensing authority both missing",
        "category": "attorney.credentials",
        "default_severity": "info",
        "summary": "No licensing identifiers were captured from the representative form.",
        "remediation": "If visible on the uploaded G-28, add bar number and issuing authority.",
        "related_fields": ["attorney.bar_number", "attorney.licensing_authority"],
        "references": [],
    },
    {
        "code": "passport.passport_number_suspicious",
        "title": "Passport number format unusual",
        "category": "passport.identity",
        "default_severity": "info",
        "summary": "The passport number is extremely short, long, or contains unexpected characters.",
        "remediation": "Re-read the document number from the data page; remove stray punctuation from OCR.",
        "related_fields": ["passport.passport_number"],
        "references": [],
    },
    {
        "code": "passport.name_too_short",
        "title": "Passport name token very short",
        "category": "passport.identity",
        "default_severity": "info",
        "summary": "A legal name part is a single character or empty after extraction.",
        "remediation": "Confirm initials vs. full names; expand abbreviations if the form requires full legal names.",
        "related_fields": ["passport.first_name", "passport.last_name", "passport.middle_name"],
        "references": [],
    },
    {
        "code": "passport.nationality_missing",
        "title": "Nationality not provided",
        "category": "passport.demographics",
        "default_severity": "info",
        "summary": "Nationality/citizenship field is blank while other passport data exists.",
        "remediation": "Copy the nationality exactly as printed; do not infer from place of birth alone.",
        "related_fields": ["passport.nationality"],
        "references": [],
    },
    {
        "code": "passport.country_issue_missing",
        "title": "Country of issue missing",
        "category": "passport.identity",
        "default_severity": "info",
        "summary": "Issuing country is blank while passport number or dates are present.",
        "remediation": "Add the issuing state authority printed on the data page.",
        "related_fields": ["passport.country_of_issue"],
        "references": [],
    },
    {
        "code": "passport.place_of_birth_missing",
        "title": "Place of birth missing",
        "category": "passport.demographics",
        "default_severity": "info",
        "summary": "Place of birth is empty while other biographic fields are filled.",
        "remediation": "Transcribe city/region as shown; include country if printed.",
        "related_fields": ["passport.place_of_birth"],
        "references": [],
    },
    {
        "code": "passport.nationality_place_mismatch",
        "title": "Nationality and place of birth look inconsistent",
        "category": "passport.consistency",
        "default_severity": "info",
        "summary": "Heuristic: nationality country token does not appear in place of birth text.",
        "remediation": "This can be legitimate (dual citizenship, born abroad); verify visually on the scan.",
        "related_fields": ["passport.nationality", "passport.place_of_birth"],
        "references": [],
    },
    {
        "code": "passport.placeholder_value",
        "title": "Placeholder text in passport field",
        "category": "passport.quality",
        "default_severity": "warn",
        "summary": "A field contains common dummy tokens such as N/A, TBD, or unknown.",
        "remediation": "Replace placeholders with real extracted values or leave the field empty.",
        "related_fields": ["passport.first_name", "passport.last_name", "passport.passport_number"],
        "references": [],
    },
    {
        "code": "attorney.placeholder_value",
        "title": "Placeholder text in attorney field",
        "category": "attorney.quality",
        "default_severity": "warn",
        "summary": "Representative data includes dummy or template strings.",
        "remediation": "Remove template text and use values from the signed PDF/image.",
        "related_fields": ["attorney.family_name", "attorney.given_name", "attorney.email"],
        "references": [],
    },
    {
        "code": "attorney.address_incomplete",
        "title": "Mailing address incomplete",
        "category": "attorney.address",
        "default_severity": "info",
        "summary": "Some address lines are filled while city, state, or postal code is missing.",
        "remediation": "Complete the full mailing address block from the G-28.",
        "related_fields": [
            "attorney.street_number_and_name",
            "attorney.city",
            "attorney.state",
            "attorney.zip_code",
            "attorney.country",
        ],
        "references": [],
    },
    {
        "code": "attorney.zip_non_numeric",
        "title": "ZIP/postal code has few digits",
        "category": "attorney.address",
        "default_severity": "info",
        "summary": "ZIP code (US-style) appears too short after digit extraction.",
        "remediation": "Include ZIP+4 if present; verify country-specific postal formats.",
        "related_fields": ["attorney.zip_code", "attorney.country"],
        "references": [],
    },
    {
        "code": "attorney.state_suspicious",
        "title": "State/province token unusual",
        "category": "attorney.address",
        "default_severity": "info",
        "summary": "For US-looking addresses, the state is not a 2-letter code or full name match.",
        "remediation": "Normalize to the form's expected state encoding.",
        "related_fields": ["attorney.state", "attorney.country"],
        "references": [],
    },
    {
        "code": "attorney.firm_without_name",
        "title": "Law firm present but attorney name incomplete",
        "category": "attorney.identity",
        "default_severity": "info",
        "summary": "Organization name is filled while both personal names are thin or missing.",
        "remediation": "Ensure individual attorney names are captured for signature blocks.",
        "related_fields": ["attorney.law_firm_or_organization", "attorney.family_name", "attorney.given_name"],
        "references": [],
    },
    {
        "code": "attorney.duplicate_phones",
        "title": "Daytime and mobile numbers identical",
        "category": "attorney.contact",
        "default_severity": "info",
        "summary": "Both phone fields normalize to the same digit sequence.",
        "remediation": "If intentional, ignore; otherwise capture distinct contact numbers.",
        "related_fields": ["attorney.daytime_telephone", "attorney.mobile_telephone"],
        "references": [],
    },
    {
        "code": "passport.all_caps_name",
        "title": "Passport name all capitals",
        "category": "passport.presentation",
        "default_severity": "info",
        "summary": "Name fields are entirely uppercase, which may differ from form casing expectations.",
        "remediation": "Adjust casing to match how the beneficiary signs other paperwork if required.",
        "related_fields": ["passport.first_name", "passport.last_name"],
        "references": [],
    },
    {
        "code": "attorney.all_caps_name",
        "title": "Attorney name all capitals",
        "category": "attorney.presentation",
        "default_severity": "info",
        "summary": "Representative names are all uppercase.",
        "remediation": "Normalize presentation if the target form is case-sensitive in review.",
        "related_fields": ["attorney.family_name", "attorney.given_name"],
        "references": [],
    },
    {
        "code": "passport.middle_initial_only",
        "title": "Middle name looks like initial only",
        "category": "passport.demographics",
        "default_severity": "info",
        "summary": "Middle name is a single letter with optional punctuation.",
        "remediation": "Expand to full middle name if the passport shows more than an initial.",
        "related_fields": ["passport.middle_name"],
        "references": [],
    },
    {
        "code": "passport.country_mismatch_issue_nationality",
        "title": "Issuing country differs from nationality",
        "category": "passport.consistency",
        "default_severity": "info",
        "summary": "Country of issue and nationality strings differ; may indicate dual nationality or data noise.",
        "remediation": "Verify both fields independently against the document; do not assume error.",
        "related_fields": ["passport.country_of_issue", "passport.nationality"],
        "references": [],
    },
    {
        "code": "attorney.email_public_domain",
        "title": "Attorney email uses public provider",
        "category": "attorney.contact",
        "default_severity": "info",
        "summary": "Email domain is a common consumer mailbox provider.",
        "remediation": "Firm policy may require firm-domain email for notices; confirm with attorney.",
        "related_fields": ["attorney.email"],
        "references": [],
    },
    {
        "code": "passport.expiry_long_horizon",
        "title": "Passport validity longer than 12 years",
        "category": "passport.dates",
        "default_severity": "info",
        "summary": "Parsed span between issue and expiration exceeds a typical adult passport duration.",
        "remediation": "Double-check child passports or special issuance types; may still be valid.",
        "related_fields": ["passport.date_of_issue", "passport.date_of_expiration"],
        "references": [],
    },
    {
        "code": "passport.minor_age_hint",
        "title": "Beneficiary may be a minor",
        "category": "passport.demographics",
        "default_severity": "info",
        "summary": "Parsed age from DOB is under 18.",
        "remediation": "Ensure guardianship and filing rules for minors are satisfied.",
        "related_fields": ["passport.date_of_birth"],
        "references": [],
    },
    {
        "code": "attorney.online_account_present",
        "title": "Online account number captured",
        "category": "attorney.account",
        "default_severity": "info",
        "summary": "USCIS online account number is non-empty; verify it matches the attorney profile.",
        "remediation": "Cross-check against the representative's USCIS account dashboard if used for e-notice.",
        "related_fields": ["attorney.online_account_number"],
        "references": [],
    },
]


def catalog_by_code() -> dict[str, RuleCatalogEntry]:
    out: dict[str, RuleCatalogEntry] = {}
    for entry in RULE_CATALOG:
        code = entry.get("code")
        if isinstance(code, str) and code:
            out[code] = entry
    return out


_BY_CODE: dict[str, RuleCatalogEntry] | None = None


def get_rule_entry(code: str | None) -> RuleCatalogEntry | None:
    global _BY_CODE
    if not code:
        return None
    if _BY_CODE is None:
        _BY_CODE = catalog_by_code()
    return _BY_CODE.get(code)


def enrich_finding(finding: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of finding with optional catalog metadata under ``catalog``."""
    if not isinstance(finding, dict):
        return finding
    code = finding.get("code")
    entry = get_rule_entry(str(code) if code is not None else None)
    out = dict(finding)
    if entry:
        out["catalog"] = {k: v for k, v in entry.items() if k != "code"}
    else:
        out["catalog"] = None
    return out


def enrich_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [enrich_finding(f) for f in findings if isinstance(f, dict)]


def list_categories() -> list[dict[str, Any]]:
    cats: dict[str, dict[str, Any]] = {}
    for e in RULE_CATALOG:
        c = str(e.get("category") or "general")
        bucket = cats.setdefault(c, {"category": c, "rule_count": 0, "codes": []})
        bucket["rule_count"] += 1
        code = e.get("code")
        if isinstance(code, str):
            bucket["codes"].append(code)
    return sorted(cats.values(), key=lambda x: x["category"])


def export_catalog_payload() -> dict[str, Any]:
    """JSON-serializable bundle for GET /extraction-quality/rules."""
    return {
        "schema_version": 1,
        "rules": list(RULE_CATALOG),
        "categories": list_categories(),
        "index": {e["code"]: e for e in RULE_CATALOG if e.get("code")},
    }
