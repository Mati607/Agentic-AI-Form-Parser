"""
Render a self-contained HTML dossier for a saved extraction session (print-friendly).
"""

from __future__ import annotations

import html
from typing import Any

from app.field_mappings import FIELD_MAPPINGS


_CSS = """
:root {
  color-scheme: light dark;
  --bg: #0f1419;
  --card: #151b22;
  --text: #e6edf3;
  --muted: #8b949e;
  --border: #30363d;
  --accent: #58a6ff;
  --warn: #d29922;
  --err: #f85149;
  --ok: #3fb950;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
  background: var(--bg);
  color: var(--text);
  line-height: 1.45;
}
.wrap { max-width: 1100px; margin: 0 auto; padding: 28px 20px 64px; }
header {
  border-bottom: 1px solid var(--border);
  padding-bottom: 18px;
  margin-bottom: 22px;
}
h1 { font-size: 1.55rem; margin: 0 0 6px; letter-spacing: -0.02em; }
.sub { color: var(--muted); font-size: 0.95rem; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
}
.card h2 {
  margin: 0 0 10px;
  font-size: 1.05rem;
  color: var(--accent);
}
table { width: 100%; border-collapse: collapse; font-size: 0.92rem; }
th, td {
  border-bottom: 1px solid var(--border);
  padding: 8px 6px;
  vertical-align: top;
  text-align: left;
}
th { color: var(--muted); font-weight: 600; width: 34%; }
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid var(--border);
  font-size: 0.78rem;
  color: var(--muted);
}
.score { font-size: 2rem; font-weight: 700; letter-spacing: -0.03em; }
.grade { font-size: 1.1rem; color: var(--muted); margin-left: 8px; }
.finding {
  border-left: 3px solid var(--border);
  padding: 8px 10px;
  margin: 8px 0;
  background: rgba(255,255,255,0.02);
  border-radius: 6px;
}
.finding.error { border-left-color: var(--err); }
.finding.warn { border-left-color: var(--warn); }
.finding.info { border-left-color: var(--muted); }
.small { font-size: 0.85rem; color: var(--muted); }
footer {
  margin-top: 28px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.85rem;
}
@media print {
  body { background: #fff; color: #111; }
  .card { border-color: #ccc; background: #fafafa; }
  :root { --text: #111; --muted: #444; --border: #ddd; --accent: #0366d6; }
}
"""


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def _findings_html(readiness: dict[str, Any]) -> str:
    findings = readiness.get("findings") if isinstance(readiness.get("findings"), list) else []
    if not findings:
        return "<p class='small'>No automated findings recorded.</p>"
    parts: list[str] = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        sev = str(f.get("severity") or "info").lower()
        code = _esc(f.get("code"))
        field = _esc(f.get("field"))
        msg = _esc(f.get("message"))
        parts.append(
            f"<div class='finding {sev}'><div><strong>{sev.upper()}</strong>"
            f"{f' <span class=\"small\">({code})</span>' if code else ''}"
            f"{f' — <span class=\"small\">{field}</span>' if field else ''}</div>"
            f"<div>{msg}</div></div>"
        )
    return "\n".join(parts)


def session_to_html(row: dict[str, Any]) -> str:
    """Return a full HTML document as a string."""
    rid = _esc(row.get("id"))
    title = row.get("title") if isinstance(row.get("title"), str) and row.get("title") else "Extraction session"
    title_esc = _esc(title)

    extracted = row.get("extracted") if isinstance(row.get("extracted"), dict) else {}
    passport = extracted.get("passport") if isinstance(extracted.get("passport"), dict) else {}
    attorney = extracted.get("attorney") if isinstance(extracted.get("attorney"), dict) else {}
    readiness = row.get("readiness") if isinstance(row.get("readiness"), dict) else {}

    score = readiness.get("score")
    grade = readiness.get("grade")
    summary = readiness.get("summary")

    meta_rows = [
        ("Session ID", rid),
        ("Created", _esc(row.get("created_at"))),
        ("Updated", _esc(row.get("updated_at"))),
        ("Passport file", _esc(row.get("passport_filename"))),
        ("G-28 file", _esc(row.get("g28_filename"))),
        ("Default form URL", _esc(row.get("default_form_url"))),
        ("Notes", _esc(row.get("notes"))),
    ]
    meta_html = "".join(
        f"<tr><th>{k}</th><td>{v if v else '—'}</td></tr>" for k, v in meta_rows
    )

    mapping_rows: list[str] = []
    for section, key, labels in FIELD_MAPPINGS:
        src = passport if section == "passport" else attorney
        val = src.get(key)
        primary = labels[0] if labels else key
        mapping_rows.append(
            "<tr>"
            f"<th>{_esc(section)}.{_esc(key)}<div class='small'>{_esc(primary)}</div></th>"
            f"<td>{_esc(val) if val is not None and str(val).strip() else '—'}</td>"
            "</tr>"
        )

    score_block = ""
    if score is not None or grade:
        score_block = (
            f"<div class='card'><h2>Readiness</h2>"
            f"<div><span class='score'>{_esc(score)}</span>"
            f"<span class='grade'>Grade {_esc(grade)}</span></div>"
            f"<p class='small'>{_esc(summary)}</p>"
            f"{_findings_html(readiness)}"
            f"</div>"
        )

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title_esc}</title>
  <style>{_CSS}</style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>{title_esc}</h1>
      <div class="sub">IDParse extraction dossier · <span class="badge">session</span></div>
    </header>

    <div class="grid">
      <div class="card">
        <h2>Metadata</h2>
        <table>{meta_html}</table>
      </div>
      {score_block}
    </div>

    <div class="card" style="margin-top:14px">
      <h2>Mapped fields</h2>
      <p class="small">Values as stored in the session (same keys used for Playwright label matching).</p>
      <table>
        <thead><tr><th>Field</th><th>Value</th></tr></thead>
        <tbody>
        {''.join(mapping_rows)}
        </tbody>
      </table>
    </div>

    <footer>
      Generated by IDParse export. This HTML is a static snapshot for review only; it does not submit forms.
    </footer>
  </div>
</body>
</html>
"""
    return doc
