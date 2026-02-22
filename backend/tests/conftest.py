import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_google_api_key():
    """Ensure GOOGLE_API_KEY is set so endpoints don't return 503."""
    with patch("app.main.GOOGLE_API_KEY", "test-key"):
        yield


@pytest.fixture
def mock_extraction():
    """Stub extraction module: validation and extract functions return success + sample data."""
    with patch("app.main.validate_passport_file", new_callable=AsyncMock) as m_validate_passport, \
         patch("app.main.validate_g28_file", new_callable=AsyncMock) as m_validate_g28, \
         patch("app.main.extract_from_passport_file", new_callable=AsyncMock) as m_extract_passport, \
         patch("app.main.extract_from_g28_file", new_callable=AsyncMock) as m_extract_g28, \
         patch("app.main.merge_extracted") as m_merge:
        m_validate_passport.return_value = {"is_valid": True}
        m_validate_g28.return_value = {"is_valid": True}
        m_extract_passport.return_value = {"first_name": "Jane", "last_name": "Doe", "passport_number": "AB123"}
        m_extract_g28.return_value = {"attorney": {"family_name": "Smith", "given_name": "John"}}
        m_merge.return_value = {
            "passport": {"first_name": "Jane", "last_name": "Doe", "passport_number": "AB123"},
            "attorney": {"family_name": "Smith", "given_name": "John"},
        }
        yield {
            "validate_passport": m_validate_passport,
            "validate_g28": m_validate_g28,
            "extract_passport": m_extract_passport,
            "extract_g28": m_extract_g28,
            "merge": m_merge,
        }


@pytest.fixture
def mock_fill_form():
    """Stub form_filler.fill_form to avoid Playwright/browser."""
    with patch("app.main.fill_form", new_callable=AsyncMock) as m_fill:
        m_fill.return_value = {
            "filled": ["passport.first_name", "passport.last_name"],
            "errors": [],
            "url": "https://example.com/form",
            "opened_in_existing_browser": False,
        }
        yield m_fill
