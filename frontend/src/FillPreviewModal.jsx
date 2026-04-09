import { useEffect, useState } from 'react'
import { previewFill } from './api/extractionApi'
import './FillPreviewModal.css'

/**
 * Modal: fetch /preview-fill and show mapped rows (what Playwright would try to fill).
 */
export function FillPreviewModal({ open, extracted, onClose, onError }) {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState(null)

  useEffect(() => {
    if (!open || !extracted) {
      setData(null)
      return
    }
    let cancelled = false
    setLoading(true)
    previewFill(extracted)
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch((e) => {
        if (!cancelled) {
          setData(null)
          onError?.(e.message || 'Preview request failed.')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- avoid re-fetch when parent passes new onError each render
  }, [open, extracted])

  if (!open) return null

  const stats = data?.stats
  const rows = data?.rows || []

  return (
    <div className="preview-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="preview-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="preview-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="preview-modal-header">
          <h2 id="preview-modal-title">Fill preview</h2>
          <button type="button" className="preview-modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>
        <p className="preview-modal-lead">
          Fields the backend would attempt to fill via label/placeholder matching (no browser opened).
        </p>
        {loading && <p className="preview-modal-status">Computing preview…</p>}
        {!loading && stats && (
          <div className="preview-stats">
            <span>
              <strong>{stats.mapped_with_value}</strong> of {stats.mapped_total} mapped fields have values
            </span>
            <span className="preview-stats-sub">
              Attorney: {stats.by_section?.attorney ?? 0} · Passport: {stats.by_section?.passport ?? 0}
            </span>
          </div>
        )}
        {!loading && data && (
          <div className="preview-table-wrap">
            <table className="preview-table">
              <thead>
                <tr>
                  <th>Section</th>
                  <th>Field</th>
                  <th>Primary label</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr
                    key={r.field_id}
                    className={r.would_attempt_fill ? 'preview-row-fill' : 'preview-row-skip'}
                  >
                    <td>{r.section}</td>
                    <td><code>{r.key}</code></td>
                    <td>{r.primary_label}</td>
                    <td>{r.value ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <footer className="preview-modal-footer">
          <button type="button" onClick={onClose}>
            Close
          </button>
        </footer>
      </div>
    </div>
  )
}
