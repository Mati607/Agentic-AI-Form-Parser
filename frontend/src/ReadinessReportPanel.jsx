import './ReadinessReportPanel.css'

function severityClass(sev) {
  if (sev === 'error') return 'readiness-sev-error'
  if (sev === 'warn') return 'readiness-sev-warn'
  return 'readiness-sev-info'
}

/**
 * Displays rule-based extraction readiness (score, grade, findings).
 */
export function ReadinessReportPanel({ report }) {
  if (!report) return null

  const { score, grade, summary, findings = [], counts, generated_at: generatedAt } = report

  return (
    <section className="readiness-panel" aria-labelledby="readiness-heading">
      <h2 id="readiness-heading">Extraction readiness</h2>
      <p className="readiness-lead">
        Automated checks on passport and attorney fields (no extra AI call). Use as a QA hint before saving or filling.
      </p>
      <div className="readiness-score-row">
        <span className={`readiness-grade readiness-grade-${(grade || '?').toLowerCase()}`}>{grade || '—'}</span>
        <span className="readiness-score">{score ?? '—'}</span>
        <span className="readiness-score-label">/ 100</span>
        {counts?.findings_total != null && (
          <span className="readiness-counts">
            {counts.by_severity?.error ?? 0} errors · {counts.by_severity?.warn ?? 0} warnings ·{' '}
            {counts.by_severity?.info ?? 0} info
          </span>
        )}
      </div>
      <p className="readiness-summary">{summary}</p>
      {generatedAt && <p className="readiness-generated">Generated {generatedAt}</p>}
      {findings.length > 0 && (
        <ul className="readiness-findings">
          {findings.map((f, i) => (
            <li key={`${f.code || 'finding'}-${i}`} className="readiness-finding">
              <span className={severityClass(f.severity)}>{f.severity}</span>
              <div className="readiness-finding-body">
                <span className="readiness-finding-msg">{f.message}</span>
                {f.field && <code className="readiness-field">{f.field}</code>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
