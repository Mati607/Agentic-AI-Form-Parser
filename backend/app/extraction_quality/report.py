"""
Assemble a readiness report with score, grade, and structured findings.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.extraction_quality.checks import run_all_checks


def _score_from_findings(findings: list[dict[str, Any]]) -> int:
    score = 100
    for f in findings:
        sev = f.get("severity")
        if sev == "error":
            score -= 18
        elif sev == "warn":
            score -= 8
        elif sev == "info":
            score -= 3
    return max(0, min(100, score))


def _grade_from_score(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 55:
        return "D"
    return "F"


def _summary_line(findings: list[dict[str, Any]], score: int, grade: str) -> str:
    errors = sum(1 for f in findings if f.get("severity") == "error")
    warns = sum(1 for f in findings if f.get("severity") == "warn")
    if not findings:
        return f"Readiness score {score} ({grade}). No automated issues detected."
    parts = [f"Readiness score {score} ({grade})."]
    if errors:
        parts.append(f"{errors} error(s).")
    if warns:
        parts.append(f"{warns} warning(s).")
    parts.append("Review findings below.")
    return " ".join(parts)


def build_readiness_report(extracted: dict[str, Any]) -> dict[str, Any]:
    """
    Build a JSON-serializable readiness report for merged extraction input.

    Expects keys passport and attorney (dicts). Unknown keys are ignored.
    """
    passport = extracted.get("passport") if isinstance(extracted.get("passport"), dict) else {}
    attorney = extracted.get("attorney") if isinstance(extracted.get("attorney"), dict) else {}

    findings = run_all_checks(passport, attorney)
    score = _score_from_findings(findings)
    grade = _grade_from_score(score)
    by_severity = {"error": 0, "warn": 0, "info": 0}
    for f in findings:
        s = f.get("severity")
        if s in by_severity:
            by_severity[s] += 1

    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    return {
        "schema_version": 1,
        "score": score,
        "grade": grade,
        "summary": _summary_line(findings, score, grade),
        "findings": findings,
        "counts": {
            "findings_total": len(findings),
            "by_severity": by_severity,
        },
        "generated_at": generated,
    }
