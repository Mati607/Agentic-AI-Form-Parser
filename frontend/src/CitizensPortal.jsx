import { useCallback, useEffect, useState } from 'react'
import {
  createCitizen,
  deleteCitizen,
  getCitizen,
  listCitizens,
  patchCitizen,
} from './api/citizensApi'
import './CitizensPortal.css'

function formatWhen(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return iso
  }
}

const STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'lead', label: 'Lead' },
  { value: 'archived', label: 'Archived' },
]

/**
 * Citizen registry: create profiles, attach extraction sessions from the sidebar, and review linked dossiers.
 */
export function CitizensPortal({ onError, onBusy, refreshToken }) {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [searchDraft, setSearchDraft] = useState('')
  const [searchApplied, setSearchApplied] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)

  const [createName, setCreateName] = useState('')
  const [createEmail, setCreateEmail] = useState('')
  const [createRef, setCreateRef] = useState('')

  const [editName, setEditName] = useState('')
  const [editEmail, setEditEmail] = useState('')
  const [editPhone, setEditPhone] = useState('')
  const [editRef, setEditRef] = useState('')
  const [editStatus, setEditStatus] = useState('active')
  const [editNotes, setEditNotes] = useState('')

  const loadList = useCallback(async () => {
    onBusy?.(true)
    try {
      const data = await listCitizens({ q: searchApplied || undefined, limit: 120, offset: 0 })
      setItems(data.items || [])
      setTotal(data.total ?? 0)
    } catch (e) {
      onError?.(e.message || 'Could not load citizens.')
      setItems([])
      setTotal(0)
    } finally {
      onBusy?.(false)
    }
  }, [onBusy, onError, searchApplied])

  useEffect(() => {
    loadList()
  }, [loadList, refreshToken])

  const openDetail = async (id) => {
    setSelectedId(id)
    setDetail(null)
    setDetailLoading(true)
    onBusy?.(true)
    try {
      const row = await getCitizen(id, { includeSessions: true })
      setDetail(row)
      setEditName(row.display_name || '')
      setEditEmail(row.email || '')
      setEditPhone(row.phone || '')
      setEditRef(row.case_reference || '')
      setEditStatus(row.status || 'active')
      setEditNotes(row.notes || '')
    } catch (e) {
      onError?.(e.message || 'Could not load citizen.')
      setSelectedId(null)
    } finally {
      setDetailLoading(false)
      onBusy?.(false)
    }
  }

  const handleSearch = () => {
    setSearchApplied(searchDraft.trim())
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    const name = createName.trim()
    if (!name) {
      onError?.('Display name is required.')
      return
    }
    onBusy?.(true)
    try {
      await createCitizen({
        display_name: name,
        email: createEmail.trim() || undefined,
        case_reference: createRef.trim() || undefined,
        status: 'active',
      })
      setCreateName('')
      setCreateEmail('')
      setCreateRef('')
      await loadList()
    } catch (err) {
      onError?.(err.message || 'Create failed.')
    } finally {
      onBusy?.(false)
    }
  }

  const handleSaveDetail = async (e) => {
    e.preventDefault()
    if (!selectedId) return
    onBusy?.(true)
    try {
      const row = await patchCitizen(selectedId, {
        display_name: editName.trim() || 'Unnamed',
        email: editEmail.trim(),
        phone: editPhone.trim(),
        case_reference: editRef.trim(),
        status: editStatus,
        notes: editNotes,
      })
      setDetail(row)
      await loadList()
    } catch (err) {
      onError?.(err.message || 'Save failed.')
    } finally {
      onBusy?.(false)
    }
  }

  const handleDelete = async () => {
    if (!selectedId) return
    if (!window.confirm('Delete this citizen and unlink all extraction sessions?')) return
    onBusy?.(true)
    try {
      await deleteCitizen(selectedId)
      setSelectedId(null)
      setDetail(null)
      await loadList()
    } catch (err) {
      onError?.(err.message || 'Delete failed.')
    } finally {
      onBusy?.(false)
    }
  }

  return (
    <div className="citizens-portal">
      <div className="citizens-intro">
        <h2>Citizens &amp; cases</h2>
        <p>
          Central profiles for people you serve. Link saved extractions from the workspace sidebar to build a lightweight
          dossier per citizen.
        </p>
      </div>

      <form className="citizens-create" onSubmit={handleCreate}>
        <h3>New citizen</h3>
        <div className="citizens-create-grid">
          <label>
            Display name *
            <input
              value={createName}
              onChange={(e) => setCreateName(e.target.value)}
              placeholder="e.g. Maria Santos"
              required
              autoComplete="name"
            />
          </label>
          <label>
            Email
            <input
              type="email"
              value={createEmail}
              onChange={(e) => setCreateEmail(e.target.value)}
              placeholder="optional"
              autoComplete="email"
            />
          </label>
          <label>
            Case / file reference
            <input
              value={createRef}
              onChange={(e) => setCreateRef(e.target.value)}
              placeholder="optional"
              autoComplete="off"
            />
          </label>
        </div>
        <button type="submit" className="citizens-btn-primary">
          Add citizen
        </button>
      </form>

      <div className="citizens-toolbar">
        <label className="citizens-search">
          <span className="sr-only">Search citizens</span>
          <input
            type="search"
            value={searchDraft}
            onChange={(e) => setSearchDraft(e.target.value)}
            placeholder="Search name, email, reference…"
          />
        </label>
        <button type="button" className="citizens-btn" onClick={handleSearch}>
          Search
        </button>
        <button
          type="button"
          className="citizens-btn"
          onClick={() => {
            setSearchDraft('')
            setSearchApplied('')
          }}
        >
          Clear
        </button>
      </div>

      <div className="citizens-split">
        <div className="citizens-list-panel">
          <h3>Directory ({total})</h3>
          {items.length === 0 ? (
            <p className="citizens-muted">No citizens yet. Add one above.</p>
          ) : (
            <ul className="citizens-list">
              {items.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    className={`citizens-list-item ${selectedId === c.id ? 'active' : ''}`}
                    onClick={() => openDetail(c.id)}
                  >
                    <span className="citizens-list-name">{c.display_name}</span>
                    <span className="citizens-list-meta">
                      {c.session_count ?? 0} session(s) · {c.status}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="citizens-detail-panel">
          {!selectedId && <p className="citizens-muted">Select a citizen to view details and linked sessions.</p>}
          {selectedId && detailLoading && <p className="citizens-muted">Loading…</p>}
          {detail && !detailLoading && (
            <>
              <div className="citizens-detail-head">
                <h3>Profile</h3>
                <button type="button" className="citizens-btn-danger" onClick={handleDelete}>
                  Delete
                </button>
              </div>
              <form className="citizens-detail-form" onSubmit={handleSaveDetail}>
                <label>
                  Display name
                  <input value={editName} onChange={(e) => setEditName(e.target.value)} required />
                </label>
                <label>
                  Email
                  <input type="email" value={editEmail} onChange={(e) => setEditEmail(e.target.value)} />
                </label>
                <label>
                  Phone
                  <input value={editPhone} onChange={(e) => setEditPhone(e.target.value)} />
                </label>
                <label>
                  Case reference
                  <input value={editRef} onChange={(e) => setEditRef(e.target.value)} />
                </label>
                <label>
                  Status
                  <select value={editStatus} onChange={(e) => setEditStatus(e.target.value)}>
                    {STATUS_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="citizens-notes">
                  Notes
                  <textarea value={editNotes} onChange={(e) => setEditNotes(e.target.value)} rows={4} />
                </label>
                <button type="submit" className="citizens-btn-primary">
                  Save changes
                </button>
              </form>

              <h4 className="citizens-sessions-title">Linked extraction sessions</h4>
              {(detail.sessions || []).length === 0 ? (
                <p className="citizens-muted">
                  None yet. Go to <strong>Workspace</strong> and assign a saved extraction to this citizen from the
                  sidebar.
                </p>
              ) : (
                <ul className="citizens-sessions">
                  {(detail.sessions || []).map((s) => (
                    <li key={s.id}>
                      <span className="citizens-session-title">{s.title || 'Untitled'}</span>
                      <span className="citizens-session-when">{formatWhen(s.created_at)}</span>
                      {s.readiness_grade != null && s.readiness_score != null && (
                        <span className="citizens-session-grade">
                          {s.readiness_grade} ({s.readiness_score})
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
