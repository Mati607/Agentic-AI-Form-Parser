"""Tests for readiness rule catalog and catalog-enriched API responses."""

from datetime import date, timedelta

from app.extraction_quality.rule_catalog import (
    catalog_by_code,
    enrich_findings,
    export_catalog_payload,
    get_rule_entry,
    list_categories,
)
from app.extraction_quality.report import build_readiness_report
from fastapi.testclient import TestClient

from app.main import app


class TestRuleCatalogIntegrity:
    def test_all_codes_unique(self):
        codes = [e["code"] for e in catalog_by_code().values()]
        assert len(codes) == len(set(codes))

    def test_get_rule_entry_known(self):
        row = get_rule_entry("passport.expired")
        assert row is not None
        assert row.get("title")

    def test_export_payload_shape(self):
        payload = export_catalog_payload()
        assert payload["schema_version"] == 1
        assert isinstance(payload["rules"], list)
        assert isinstance(payload["categories"], list)
        assert isinstance(payload["index"], dict)

    def test_categories_count_matches_rules(self):
        payload = export_catalog_payload()
        total = sum(c["rule_count"] for c in payload["categories"])
        assert total == len(payload["rules"])


class TestEnrichFindings:
    def test_enrich_adds_catalog_block(self):
        raw = [{"severity": "error", "code": "passport.expired", "field": "x", "message": "m"}]
        enriched = enrich_findings(raw)
        assert enriched[0].get("catalog") is not None
        assert enriched[0]["catalog"].get("remediation")

    def test_unknown_code_gets_null_catalog(self):
        raw = [{"severity": "info", "code": "not.a.real.code", "message": "x"}]
        enriched = enrich_findings(raw)
        assert enriched[0].get("catalog") is None


class TestExtendedChecksIntegrate:
    def test_placeholder_lowers_score(self):
        rep = build_readiness_report(
            {
                "passport": {
                    "last_name": "Doe",
                    "first_name": "N/A",
                    "passport_number": "AB1234567",
                    "date_of_birth": "1990-01-01",
                    "date_of_expiration": (date.today() + timedelta(days=400)).isoformat(),
                },
                "attorney": {"family_name": "Smith", "email": "a@law.com"},
            }
        )
        codes = {f["code"] for f in rep["findings"]}
        assert "passport.placeholder_value" in codes

    def test_public_email_finding(self):
        rep = build_readiness_report(
            {
                "passport": {},
                "attorney": {"family_name": "Smith", "email": "x@gmail.com"},
            }
        )
        codes = {f["code"] for f in rep["findings"]}
        assert "attorney.email_public_domain" in codes


class TestExtractionQualityRulesHttp:
    def test_get_rules(self):
        client = TestClient(app)
        r = client.get("/extraction-quality/rules")
        assert r.status_code == 200
        data = r.json()
        assert "rules" in data and len(data["rules"]) > 10

    def test_readiness_with_catalog_query(self):
        client = TestClient(app)
        r = client.post(
            "/extraction-readiness?catalog=true",
            json={"passport": {"last_name": "A"}, "attorney": {}},
        )
        assert r.status_code == 200
        findings = r.json().get("findings") or []
        assert findings
        assert any(isinstance(f.get("catalog"), dict) for f in findings if isinstance(f, dict))
