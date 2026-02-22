import io
import pytest
from unittest.mock import patch, AsyncMock


class TestHealth:
    """GET /health"""

    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestExtract:
    """POST /extract"""

    def test_extract_without_api_key_returns_503(self, client):
        with patch("app.main.GOOGLE_API_KEY", ""):
            response = client.post("/extract")
        assert response.status_code == 503
        assert "GOOGLE_API_KEY" in response.json()["detail"]

    def test_extract_no_files_returns_400(self, client, mock_google_api_key):
        response = client.post("/extract")
        assert response.status_code == 400
        assert "at least one file" in response.json()["detail"].lower()

    def test_extract_invalid_passport_content_type_returns_400(
        self, client, mock_google_api_key
    ):
        response = client.post(
            "/extract",
            files={"passport": ("x.txt", io.BytesIO(b"x"), "text/plain")},
        )
        assert response.status_code == 400
        assert "PDF or image" in response.json()["detail"]

    def test_extract_passport_validation_fails_returns_400(
        self, client, mock_google_api_key, mock_extraction
    ):
        mock_extraction["validate_passport"].return_value = {
            "is_valid": False,
            "reason": "Not a passport image.",
        }
        response = client.post(
            "/extract",
            files={"passport": ("p.pdf", io.BytesIO(b"fake"), "application/pdf")},
        )
        assert response.status_code == 400
        body = response.json()
        assert "detail" in body
        assert "validation_errors" in body.get("detail", body)
        errors = body.get("detail", body).get("validation_errors", {})
        assert "passport" in errors

    def test_extract_passport_only_success_returns_merged(
        self, client, mock_google_api_key, mock_extraction
    ):
        response = client.post(
            "/extract",
            files={"passport": ("p.pdf", io.BytesIO(b"fake"), "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "passport" in data
        assert data["passport"].get("first_name") == "Jane"
        mock_extraction["extract_passport"].assert_called_once()
        mock_extraction["merge"].assert_called_once()

    def test_extract_g28_only_success_returns_merged(
        self, client, mock_google_api_key, mock_extraction
    ):
        response = client.post(
            "/extract",
            files={"g28": ("g.pdf", io.BytesIO(b"fake"), "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "attorney" in data
        mock_extraction["extract_g28"].assert_called_once()
        mock_extraction["merge"].assert_called_once()


class TestFillForm:
    """POST /fill-form"""

    def test_fill_form_without_api_key_returns_503(self, client):
        with patch("app.main.GOOGLE_API_KEY", ""):
            response = client.post(
                "/fill-form",
                data={"form_url": "https://example.com/form"},
            )
        assert response.status_code == 503

    def test_fill_form_missing_form_url_returns_400(
        self, client, mock_google_api_key
    ):
        response = client.post("/fill-form", data={"form_url": ""})
        assert response.status_code == 400
        assert "form_url" in response.json()["detail"].lower()

    def test_fill_form_invalid_url_scheme_returns_400(
        self, client, mock_google_api_key
    ):
        response = client.post(
            "/fill-form",
            data={"form_url": "ftp://example.com/form"},
        )
        assert response.status_code == 400
        assert "http" in response.json()["detail"].lower()

    def test_fill_form_no_files_returns_400(self, client, mock_google_api_key):
        response = client.post(
            "/fill-form",
            data={"form_url": "https://example.com/form"},
        )
        assert response.status_code == 400
        assert "at least one file" in response.json()["detail"].lower()

    def test_fill_form_success_returns_extracted_and_filled(
        self,
        client,
        mock_google_api_key,
        mock_extraction,
        mock_fill_form,
    ):
        response = client.post(
            "/fill-form",
            data={"form_url": "https://example.com/form"},
            files={"passport": ("p.pdf", io.BytesIO(b"fake"), "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "extracted" in data
        assert "filled_fields" in data
        assert "errors" in data
        assert data["filled_fields"] == ["passport.first_name", "passport.last_name"]
        mock_fill_form.assert_called_once()
        merged = mock_fill_form.call_args[0][0]
        assert mock_fill_form.call_args[1]["form_url"] == "https://example.com/form"
        assert "passport" in merged or "attorney" in merged

    def test_fill_form_validation_error_returns_400(
        self, client, mock_google_api_key, mock_extraction, mock_fill_form
    ):
        mock_extraction["validate_passport"].return_value = {
            "is_valid": False,
            "reason": "Unreadable.",
        }
        response = client.post(
            "/fill-form",
            data={"form_url": "https://example.com/form"},
            files={"passport": ("p.pdf", io.BytesIO(b"fake"), "application/pdf")},
        )
        assert response.status_code == 400
        mock_fill_form.assert_not_called()
