"""Tests for extraction readiness (dates, checks, report, HTTP)."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.extraction_quality.dates import parse_date_fuzzy, utc_today
from app.extraction_quality.report import build_readiness_report
from app.main import app


class TestParseDateFuzzy:
    def test_iso_dash(self):
        assert parse_date_fuzzy("2019-04-05") == date(2019, 4, 5)

    def test_iso_slash(self):
        assert parse_date_fuzzy("2019/12/01") == date(2019, 12, 1)

    def test_empty(self):
        assert parse_date_fuzzy(None) is None
        assert parse_date_fuzzy("  ") is None


class TestReadinessReport:
    def test_clean_passport_and_attorney_high_score(self):
        exp = (utc_today() + timedelta(days=400)).isoformat()
        rep = build_readiness_report(
            {
                "passport": {
                    "last_name": "Doe",
                    "first_name": "Jane",
                    "passport_number": "X123",
                    "date_of_birth": "1990-01-01",
                    "date_of_expiration": exp,
                    "sex": "F",
                },
                "attorney": {
                    "family_name": "Smith",
                    "given_name": "John",
                    "email": "a@law.com",
                    "bar_number": "12345",
                },
            }
        )
        assert rep["score"] >= 85
        assert rep["grade"] in ("A", "B")
        assert rep["counts"]["by_severity"]["error"] == 0

    def test_expired_passport_error(self):
        past = (utc_today() - timedelta(days=30)).isoformat()
        rep = build_readiness_report(
            {
                "passport": {
                    "last_name": "Doe",
                    "first_name": "Jane",
                    "passport_number": "X",
                    "date_of_birth": "1990-01-01",
                    "date_of_expiration": past,
                },
                "attorney": {"email": "x@y.z", "family_name": "A"},
            }
        )
        codes = {f["code"] for f in rep["findings"]}
        assert "passport.expired" in codes
        assert rep["counts"]["by_severity"]["error"] >= 1

    def test_empty_sections_info(self):
        rep = build_readiness_report({"passport": {}, "attorney": {}})
        codes = {f["code"] for f in rep["findings"]}
        assert "coverage.no_passport_data" in codes
        assert "coverage.no_attorney_data" in codes


class TestExtractionReadinessHttp:
    def test_endpoint_returns_report(self):
        client = TestClient(app)
        r = client.post(
            "/extraction-readiness",
            json={
                "passport": {"first_name": "A", "last_name": "B"},
                "attorney": {},
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "score" in data and "findings" in data
        assert isinstance(data["findings"], list)
