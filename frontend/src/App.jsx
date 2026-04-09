import { useCallback, useEffect, useState } from 'react'
import './App.css'
import { API_BASE } from './config'
import { createExtractionSession, fetchExtractionReadiness, formatApiError } from './api/extractionApi'
import { ExtractionHistoryPanel } from './ExtractionHistoryPanel'
import { FillPreviewModal } from './FillPreviewModal'
import { ReadinessReportPanel } from './ReadinessReportPanel'

const DEFAULT_FORM_URL = 'https://mendrika-alma.github.io/form-submission/'

function App() {
  const [formUrl, setFormUrl] = useState(DEFAULT_FORM_URL)
  const [passportFile, setPassportFile] = useState(null)
  const [g28File, setG28File] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [historyRefresh, setHistoryRefresh] = useState(0)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [saveTitle, setSaveTitle] = useState('')
  const [loadedSession, setLoadedSession] = useState(null)
  const [saving, setSaving] = useState(false)
  const [readinessReport, setReadinessReport] = useState(null)

  const bumpHistory = useCallback(() => {
    setHistoryRefresh((n) => n + 1)
  }, [])

  const buildFormData = (includeFormUrl = false) => {
    const form = new FormData()
    if (includeFormUrl && formUrl) form.append('form_url', formUrl.trim())
    if (passportFile) form.append('passport', passportFile)
    if (g28File) form.append('g28', g28File)
    return form
  }

  useEffect(() => {
    const extracted = result?.extracted
    if (!extracted) {
      setReadinessReport(null)
      return
    }
    let cancelled = false
    fetchExtractionReadiness(extracted)
      .then((rep) => {
        if (!cancelled) setReadinessReport(rep)
      })
      .catch(() => {
        if (!cancelled) setReadinessReport(null)
      })
    return () => {
      cancelled = true
    }
  }, [result?.extracted])

  const handleExtract = async () => {
    const form = buildFormData(false)
    if (form.get('passport') || form.get('g28')) {
      setError(null)
      setResult(null)
      setLoadedSession(null)
      setLoading(true)
      try {
        const r = await fetch(`${API_BASE}/extract`, {
          method: 'POST',
          body: form,
        })
        if (!r.ok) {
          const err = await r.json().catch(() => ({ detail: r.statusText }))
          throw new Error(formatApiError(err))
        }
        const data = await r.json()
        setResult({ extracted: data, filled_fields: null, errors: null })
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    } else {
      setError('Upload at least one file (passport or G-28).')
    }
  }

  const handleFillForm = async () => {
    const url = formUrl?.trim()
    if (!url) {
      setError('Enter the form URL to fill.')
      return
    }
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      setError('Form URL must start with http:// or https://')
      return
    }
    const form = buildFormData(true)
    if (form.get('passport') || form.get('g28')) {
      setError(null)
      setResult(null)
      setLoadedSession(null)
      setLoading(true)
      try {
        const r = await fetch(`${API_BASE}/fill-form`, {
          method: 'POST',
          body: form,
        })
        if (!r.ok) {
          const err = await r.json().catch(() => ({ detail: r.statusText }))
          throw new Error(formatApiError(err))
        }
        const data = await r.json()
        setResult({
          extracted: data.extracted,
          filled_fields: data.filled_fields,
          errors: data.errors,
          form_url: data.form_url,
          opened_in_existing_browser: data.opened_in_existing_browser,
        })
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    } else {
      setError('Upload at least one file (passport or G-28).')
    }
  }

  const handleSaveExtraction = async () => {
    const extracted = result?.extracted
    if (!extracted) {
      setError('Run extract first to save data.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const saved = await createExtractionSession({
        extracted,
        title: saveTitle.trim() || undefined,
        passport_filename: passportFile?.name || undefined,
        g28_filename: g28File?.name || undefined,
        default_form_url: formUrl?.trim() || undefined,
      })
      if (saved?.readiness) setReadinessReport(saved.readiness)
      setSaveTitle('')
      bumpHistory()
    } catch (e) {
      setError(e.message || 'Save failed.')
    } finally {
      setSaving(false)
    }
  }

  const handleLoadFromHistory = (extracted, meta) => {
    setLoadedSession(meta)
    setResult({
      extracted,
      filled_fields: null,
      errors: null,
    })
    setError(null)
    if (meta?.default_form_url) setFormUrl(meta.default_form_url)
    if (meta?.readiness) setReadinessReport(meta.readiness)
  }

  const handleFillResultFromHistory = (data) => {
    setResult({
      extracted: data.extracted,
      filled_fields: data.filled_fields,
      errors: data.errors,
      form_url: data.form_url,
      opened_in_existing_browser: data.opened_in_existing_browser,
    })
    setLoadedSession((prev) => (data.session_id ? { id: data.session_id } : prev))
    setError(null)
  }

  const previewExtracted = result?.extracted || null

  return (
    <div className="app">
      <header className="header">
        <h1>Document & Form Automation</h1>
        <p>
          Upload passport and/or G-28 (PDF or image). Extract data, review readiness, preview mapped fields, save sessions,
          and fill the form.
        </p>
      </header>

      <div className="app-layout">
        <div className="app-main">
          <section className="upload">
            <div className="field">
              <label>Form URL (link to the form to fill)</label>
              <input
                type="url"
                value={formUrl}
                onChange={(e) => setFormUrl(e.target.value)}
                placeholder="https://example.com/form"
              />
            </div>
            <div className="field">
              <label>Passport (PDF, JPEG, PNG)</label>
              <input
                type="file"
                accept=".pdf,image/jpeg,image/png,image/jpg"
                onChange={(e) => setPassportFile(e.target.files?.[0] || null)}
              />
            </div>
            <div className="field">
              <label>G-28 / Form A-28 (PDF, JPEG, PNG)</label>
              <input
                type="file"
                accept=".pdf,image/jpeg,image/png,image/jpg"
                onChange={(e) => setG28File(e.target.files?.[0] || null)}
              />
            </div>
            <div className="actions">
              <button onClick={handleExtract} disabled={loading}>
                {loading ? 'Processing…' : 'Extract only'}
              </button>
              <button onClick={handleFillForm} disabled={loading} className="primary">
                {loading ? 'Processing…' : 'Extract & fill form'}
              </button>
            </div>
          </section>

          {error && <div className="message error">{error}</div>}

          {result && (
            <section className="result">
              <h2>Result</h2>
              {loadedSession && (
                <p className="session-banner">
                  Loaded from saved session
                  {loadedSession.title ? `: ${loadedSession.title}` : ''}.
                </p>
              )}
              {result.opened_in_existing_browser != null && (
                <>
                  {result.opened_in_existing_browser ? (
                    <p className="filled">
                      Original form opened and filled in a Chrome tab. The tab remains open for you to review/edit.
                    </p>
                  ) : (
                    <p className="warn">
                      Could not open/fill in your existing Chrome tab. Start Chrome with remote debugging first:{' '}
                      <code>
                        /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
                      </code>
                    </p>
                  )}
                </>
              )}
              {result.filled_fields?.length > 0 && (
                <p className="filled">Filled fields: {result.filled_fields.join(', ')}</p>
              )}
              {result.errors?.length > 0 && <p className="warn">Warnings: {result.errors.join('; ')}</p>}
              <ReadinessReportPanel report={readinessReport} />
              <div className="result-toolbar">
                <button type="button" onClick={() => setPreviewOpen(true)} disabled={!previewExtracted}>
                  Preview fill mapping
                </button>
                <div className="save-row">
                  <input
                    type="text"
                    placeholder="Optional title for save"
                    value={saveTitle}
                    onChange={(e) => setSaveTitle(e.target.value)}
                    aria-label="Session title"
                  />
                  <button type="button" onClick={handleSaveExtraction} disabled={saving || !previewExtracted}>
                    {saving ? 'Saving…' : 'Save extraction'}
                  </button>
                </div>
              </div>
              <pre className="json">{JSON.stringify(result.extracted, null, 2)}</pre>
            </section>
          )}
        </div>

        <aside className="app-aside">
          <ExtractionHistoryPanel
            refreshToken={historyRefresh}
            formUrl={formUrl}
            onLoadExtracted={handleLoadFromHistory}
            onFillResult={handleFillResultFromHistory}
            onError={setError}
            onBusy={setLoading}
          />
        </aside>
      </div>

      <FillPreviewModal
        open={previewOpen}
        extracted={previewExtracted}
        onClose={() => setPreviewOpen(false)}
        onError={setError}
      />
    </div>
  )
}

export default App
