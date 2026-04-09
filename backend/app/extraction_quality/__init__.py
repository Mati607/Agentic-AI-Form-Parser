"""
Rule-based readiness checks for merged passport + attorney extraction payloads.

Used by HTTP APIs and optional persistence on saved extraction sessions.
"""

from app.extraction_quality.report import build_readiness_report

__all__ = ["build_readiness_report"]
