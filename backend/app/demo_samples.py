"""
Demo-friendly sample payloads that do not require any external API keys.
"""

from __future__ import annotations

from typing import Any


def sample_merged_extraction(*, variant: str = "good") -> dict[str, Any]:
    """
    Return a merged extraction shaped like POST /extract output.

    Variants:
      - good: mostly complete, should grade well
      - messy: intentionally incomplete/suspicious to demonstrate readiness findings
    """
    v = (variant or "good").strip().lower()

    if v == "messy":
        return {
            "passport": {
                "first_name": "ALEX",
                "last_name": "",
                "passport_number": "P 12O45",  # contains letter O to look suspicious
                "date_of_birth": "31/02/2010",  # invalid date
                "date_of_issue": "2029-01-01",
                "date_of_expiration": "2024-01-01",  # expired
                "sex": "Unknown",
                "nationality": "N/A",
            },
            "attorney": {
                "given_name": "",
                "family_name": "",
                "email": "not-an-email",
                "daytime_telephone": "555",
                "bar_number": "",
                "licensing_authority": "",
            },
        }

    # Default: "good"
    return {
        "passport": {
            "first_name": "ALEX",
            "last_name": "RIVERA",
            "passport_number": "X1234567",
            "date_of_birth": "1994-06-02",
            "date_of_issue": "2019-04-11",
            "date_of_expiration": "2030-04-10",
            "sex": "X",
            "nationality": "Exampleland",
        },
        "attorney": {
            "given_name": "MAYA",
            "family_name": "CHEN",
            "email": "maya.chen@example.com",
            "daytime_telephone": "+1 (415) 555-0123",
            "bar_number": "CA-123456",
            "licensing_authority": "State Bar of California",
        },
    }

