import { useCallback, useEffect, useMemo, useState } from 'react'
import './IntakeView.css'
import {
  createIntakeJob,
  getIntakeFields,
  getIntakeJob,
  intakeArtifactUrl,
  patchIntakeFields,
  promoteIntakeJob,
} from '../api/intakeApi'

function parseValueJson(s) {
  if (s == null) return ''
  try {
    const v = JSON.parse(s)
    if (v === null || v === undefined) return ''
    if (typeof v === 'object') return JSON.stringify(v)
    return String(v)
  } catch {
    return String(s)
  }
}

export function IntakeView({ onError, onBusy, onPromoted }) {
  const [passportFile, setPassportFile] = useState(null)
  const [g28File, setG28File] = useState(null)
  const [jobId, setJobId] = useState('')
  const [job, setJob] = useState(null)
  const [fields, setFields] = useState([])
  const [drafts, setDrafts] = useState({})
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  const terminal = job && (job.status === 'completed' || job.status === 'failed')

  const refreshJob = useCallback(async (jid) => {
    const j = await getIntakeJob(jid)
    setJob(j)
    if (j.status === 'completed' || j.status === 'failed') {
      const f = await getIntakeFields(jid)
      const rows = f.assertions || []
      setFields(rows)
      const d = {}
      for (const r of rows) {
        d[r.field_path] = parseValueJson(r.value_json)
      }
      setDrafts(d)
    }
    return j.status
  }, [])

  useEffect(() => {
    const jid = jobId.trim()
    if (!jid) return undefined
    let cancelled = false
    let timer
    const loop = async () => {
      while (!cancelled) {
        try {
          const st = await refreshJob(jid)
          if (st === 'completed' || st === 'failed') break
        } catch (e) {
          if (!cancelled) onError?.(e.message || String(e))
          break
        }
        await new Promise((resolve) => {
          timer = setTimeout(resolve, 900)
        })
      }
    }
    loop()
    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [jobId, refreshJob, onError])

  const pageLinks = useMemo(() => job?.page_image_links || [], [job])

  const handleCreate = async () => {
    if (!passportFile && !g28File) {
      onError?.('Select at least one file (passport or G-28).')
      return
    }
    setLoading(true)
    onBusy?.(true)
    onError?.(null)
    try {
      const created = await createIntakeJob({ passportFile, g28File })
      setJobId(created.id)
      setJob({ id: created.id, status: 'queued', stage: 'queued' })
    } catch (e) {
      onError?.(e.message || String(e))
    } finally {
      setLoading(false)
      onBusy?.(false)
    }
  }

  const handleSaveFields = async () => {
    if (!jobId.trim()) return
    const patches = []
    for (const row of fields) {
      const cur = parseValueJson(row.value_json)
      const next = drafts[row.field_path]
      if (next !== undefined && String(next) !== String(cur)) {
        patches.push({ field_path: row.field_path, value: next, reviewer_note: 'UI edit' })
      }
    }
    if (!patches.length) {
      onError?.('No field changes to save.')
      return
    }
    setSaving(true)
    onError?.(null)
    try {
      const out = await patchIntakeFields(jobId.trim(), patches)
      const rows = out.assertions || []
      setFields(rows)
      const d = { ...drafts }
      for (const r of rows) {
        d[r.field_path] = parseValueJson(r.value_json)
      }
      setDrafts(d)
    } catch (e) {
      onError?.(e.message || String(e))
    } finally {
      setSaving(false)
    }
  }

  const handlePromote = async () => {
    if (!jobId.trim()) return
    setLoading(true)
    onError?.(null)
    try {
      const out = await promoteIntakeJob(jobId.trim(), { title: `Intake ${jobId.slice(0, 8)}` })
      onPromoted?.(out)
    } catch (e) {
      onError?.(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="intake">
      <section className="upload">
        <h2 style={{ marginTop: 0 }}>Intake &amp; review</h2>
        <p style={{ color: '#555', marginTop: 0 }}>
          Upload identity documents. The server validates, renders review pages, extracts fields, and stores an audit
          trail. Save overrides, then promote to a saved session for form fill.
        </p>
        <div className="field">
          <label>Passport (PDF, JPEG, PNG)</label>
          <input
            type="file"
            accept=".pdf,image/jpeg,image/png,image/jpg"
            onChange={(e) => setPassportFile(e.target.files?.[0] || null)}
          />
        </div>
        <div className="field">
          <label>G-28 / A-28 (PDF, JPEG, PNG)</label>
          <input
            type="file"
            accept=".pdf,image/jpeg,image/png,image/jpg"
            onChange={(e) => setG28File(e.target.files?.[0] || null)}
          />
        </div>
        <div className="actions">
          <button type="button" onClick={handleCreate} disabled={loading} className="primary">
            {loading ? 'Starting…' : 'Start intake job'}
          </button>
        </div>
      </section>

      <div className="intake-toolbar">
        <label htmlFor="intake-job-id" style={{ fontWeight: 600 }}>
          Job ID
        </label>
        <input
          id="intake-job-id"
          type="text"
          placeholder="Paste job id after upload"
          value={jobId}
          onChange={(e) => setJobId(e.target.value)}
        />
        <button
          type="button"
          onClick={() => {
            refreshJob(jobId.trim()).catch((e) => onError?.(e.message || String(e)))
          }}
          disabled={!jobId.trim() || loading}
        >
          Refresh
        </button>
      </div>

      {job && (
        <div className="intake-meta">
          <strong>Status:</strong> {job.status}
          {job.stage ? (
            <>
              {' '}
              · <strong>Stage:</strong> {job.stage}
            </>
          ) : null}
          {job.error_message ? (
            <>
              {' '}
              · <span className="warn">{job.error_message}</span>
            </>
          ) : null}
        </div>
      )}

      {job?.audit?.length > 0 && (
        <div className="intake-audit">
          <strong>Recent audit</strong>
          <ul style={{ margin: '0.35rem 0 0 1rem', padding: 0 }}>
            {job.audit.slice(-12).map((ev) => (
              <li key={ev.id}>
                {ev.event_type}
                {ev.payload?.stage ? ` — ${ev.payload.stage}` : ''}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="intake-layout">
        <div className="intake-panel">
          <h3>Review pages</h3>
          {!pageLinks.length && <p className="muted">No page images yet (or job still running).</p>}
          <div className="intake-pages">
            {pageLinks.map((p) => (
              <figure key={`${p.artifact_id}-${p.page_index}`}>
                <figcaption>
                  {p.role} · page {p.page_index}
                </figcaption>
                <img src={intakeArtifactUrl(p.path)} alt={`${p.role} page ${p.page_index}`} loading="lazy" />
              </figure>
            ))}
          </div>
        </div>

        <div className="intake-panel intake-fields">
          <h3>Extracted fields</h3>
          {!fields.length && terminal && job?.status === 'completed' && (
            <p className="muted">No field assertions (empty extraction).</p>
          )}
          {!terminal && <p className="muted">Fields appear when the job completes.</p>}
          {fields.length > 0 && (
            <>
              <table>
                <thead>
                  <tr>
                    <th>Field</th>
                    <th>Value</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {fields.map((r) => (
                    <tr key={r.field_path}>
                      <td>
                        <code>{r.field_path}</code>
                      </td>
                      <td>
                        <input
                          type="text"
                          value={drafts[r.field_path] ?? ''}
                          onChange={(e) => setDrafts((d) => ({ ...d, [r.field_path]: e.target.value }))}
                          aria-label={r.field_path}
                        />
                      </td>
                      <td className="src">{r.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="intake-actions">
                <button type="button" onClick={handleSaveFields} disabled={saving || !jobId.trim()}>
                  {saving ? 'Saving…' : 'Save overrides'}
                </button>
                <button
                  type="button"
                  onClick={handlePromote}
                  disabled={loading || job?.status !== 'completed'}
                  className="primary"
                >
                  Promote to saved session
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
