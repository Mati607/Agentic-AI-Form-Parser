import { useCallback, useEffect, useMemo, useState } from 'react'
import { extractionSessionsSchemaUrl, fetchExtractionQualityRules } from './api/extractionApi'
import './QualityRulesPanel.css'

function norm(s) {
  return (s || '').toString().toLowerCase()
}

/**
 * Browse static readiness rule metadata from GET /extraction-quality/rules.
 */
export function QualityRulesPanel({ onError }) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [rules, setRules] = useState([])
  const [query, setQuery] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchExtractionQualityRules()
      setRules(Array.isArray(data.rules) ? data.rules : [])
    } catch (e) {
      onError?.(e.message || 'Could not load quality rules.')
      setRules([])
    } finally {
      setLoading(false)
    }
  }, [onError])

  useEffect(() => {
    if (open && rules.length === 0 && !loading) {
      load()
    }
  }, [open, rules.length, loading, load])

  const filtered = useMemo(() => {
    const q = norm(query).trim()
    if (!q) return rules
    return rules.filter((r) => {
      const hay = [r.code, r.title, r.category, r.summary, r.remediation].map(norm).join(' ')
      return hay.includes(q)
    })
  }, [rules, query])

  const byCategory = useMemo(() => {
    const m = new Map()
    for (const r of filtered) {
      const c = r.category || 'general'
      if (!m.has(c)) m.set(c, [])
      m.get(c).push(r)
    }
    return Array.from(m.entries()).sort((a, b) => a[0].localeCompare(b[0]))
  }, [filtered])

  return (
    <section className="quality-rules" aria-labelledby="quality-rules-heading">
      <div className="quality-rules-header">
        <h2 id="quality-rules-heading">Readiness rules</h2>
        <button type="button" className="quality-rules-toggle" onClick={() => setOpen((v) => !v)}>
          {open ? 'Hide' : 'Show'} catalog
        </button>
      </div>
      <p className="quality-rules-hint">
        Static checklist used by the readiness scorer.{' '}
        <a href={extractionSessionsSchemaUrl()} target="_blank" rel="noreferrer">
          JSON Schema bundle
        </a>
      </p>
      {open && (
        <div className="quality-rules-body">
          <div className="quality-rules-toolbar">
            <input
              type="search"
              placeholder="Filter by code, title, text…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Filter rules"
            />
            <button type="button" onClick={load} disabled={loading}>
              {loading ? 'Loading…' : 'Reload'}
            </button>
          </div>
          {loading && rules.length === 0 ? (
            <p className="quality-rules-empty">Loading catalog…</p>
          ) : (
            <div className="quality-rules-scroll">
              {byCategory.map(([cat, items]) => (
                <details key={cat} className="quality-rules-cat" open>
                  <summary>
                    {cat}{' '}
                    <span className="quality-rules-count">
                      {items.length} rule{items.length === 1 ? '' : 's'}
                    </span>
                  </summary>
                  <ul className="quality-rules-list">
                    {items.map((r) => (
                      <li key={r.code} className="quality-rules-item">
                        <div className="quality-rules-item-top">
                          <code className="quality-rules-code">{r.code}</code>
                          <span className={`quality-rules-sev quality-rules-sev-${r.default_severity || 'info'}`}>
                            {r.default_severity || 'info'}
                          </span>
                        </div>
                        <div className="quality-rules-title">{r.title}</div>
                        {r.summary && <p className="quality-rules-summary">{r.summary}</p>}
                        {r.remediation && <p className="quality-rules-remediation">{r.remediation}</p>}
                      </li>
                    ))}
                  </ul>
                </details>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
