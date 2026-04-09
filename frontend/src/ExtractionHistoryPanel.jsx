import { useCallback, useEffect, useState } from 'react'
import {
  deleteExtractionSession,
  extractionSessionExportUrl,
  fillFormFromSession,
  getExtractionSession,
  listExtractionSessions,
} from './api/extractionApi'
import './ExtractionHistoryPanel.css'

function formatWhen(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return d.toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
  } catch {
    return iso
  }
}

/**
 * Sidebar list of server-stored extraction sessions: load, export, delete, re-fill.
 */
export function ExtractionHistoryPanel({
  refreshToken,
  formUrl,
  onLoadExtracted,
  onFillResult,
  onError,
  onBusy,
}) {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [workingId, setWorkingId] = useState(null)

  const loadList = useCallback(async () => {
    setLoading(true)
    onBusy?.(true)
    try {
      const data = await listExtractionSessions(40, 0)
      setItems(data.items || [])
      setTotal(data.total ?? 0)
    } catch (e) {
      onError?.(e.message || 'Could not load saved sessions.')
      setItems([])
      setTotal(0)
    } finally {
      setLoading(false)
      onBusy?.(false)
    }
  }, [onBusy, onError])

  useEffect(() => {
    loadList()
  }, [loadList, refreshToken])

  const handleLoad = async (id) => {
    setWorkingId(id)
    onBusy?.(true)
    try {
      const row = await getExtractionSession(id)
      onLoadExtracted?.(row.extracted, {
        id: row.id,
        title: row.title,
        default_form_url: row.default_form_url,
      })
    } catch (e) {
      onError?.(e.message || 'Failed to load session.')
    } finally {
      setWorkingId(null)
      onBusy?.(false)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this saved extraction from the server?')) return
    setWorkingId(id)
    onBusy?.(true)
    try {
      await deleteExtractionSession(id)
      await loadList()
    } catch (e) {
      onError?.(e.message || 'Delete failed.')
    } finally {
      setWorkingId(null)
      onBusy?.(false)
    }
  }

  const handleFill = async (id) => {
    const url = formUrl?.trim()
    if (!url) {
      onError?.('Enter the form URL above before filling from a saved session.')
      return
    }
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      onError?.('Form URL must start with http:// or https://')
      return
    }
    setWorkingId(id)
    onBusy?.(true)
    try {
      const data = await fillFormFromSession(id, url)
      onFillResult?.(data)
    } catch (e) {
      onError?.(e.message || 'Fill from session failed.')
    } finally {
      setWorkingId(null)
      onBusy?.(false)
    }
  }

  return (
    <section className="history-panel" aria-labelledby="history-heading">
      <div className="history-panel-header">
        <h2 id="history-heading">Saved extractions</h2>
        <button type="button" className="history-refresh" onClick={loadList} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>
      <p className="history-panel-hint">
        Stored on the server (SQLite). Load JSON into the result area or run Playwright fill without re-uploading files.
      </p>
      {loading && items.length === 0 ? (
        <p className="history-empty">Loading sessions…</p>
      ) : items.length === 0 ? (
        <p className="history-empty">No sessions yet. Use &quot;Save extraction&quot; after a successful extract.</p>
      ) : (
        <ul className="history-list">
          {items.map((row) => (
            <li key={row.id} className="history-item">
              <div className="history-item-top">
                <span className="history-title">{row.title || 'Untitled session'}</span>
                <span className="history-date">{formatWhen(row.created_at)}</span>
              </div>
              <div className="history-meta">
                P:{row.field_counts?.passport ?? 0} · A:{row.field_counts?.attorney ?? 0}
                {row.has_last_fill ? ' · last fill saved' : ''}
              </div>
              <div className="history-actions">
                <button
                  type="button"
                  onClick={() => handleLoad(row.id)}
                  disabled={workingId === row.id}
                >
                  Load
                </button>
                <button
                  type="button"
                  onClick={() => handleFill(row.id)}
                  disabled={workingId === row.id}
                  className="history-primary"
                >
                  Fill form
                </button>
                <a
                  className="history-link"
                  href={extractionSessionExportUrl(row.id)}
                  download
                  target="_blank"
                  rel="noreferrer"
                >
                  Export JSON
                </a>
                <button
                  type="button"
                  className="history-danger"
                  onClick={() => handleDelete(row.id)}
                  disabled={workingId === row.id}
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <p className="history-footer">{total} session(s) total</p>
    </section>
  )
}
