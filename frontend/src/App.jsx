import { useState } from 'react'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const DEFAULT_FORM_URL = 'https://mendrika-alma.github.io/form-submission/'

function App() {
  const [formUrl, setFormUrl] = useState(DEFAULT_FORM_URL)
  const [passportFile, setPassportFile] = useState(null)
  const [g28File, setG28File] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const buildFormData = (includeFormUrl = false) => {
    const form = new FormData()
    if (includeFormUrl && formUrl) form.append('form_url', formUrl.trim())
    if (passportFile) form.append('passport', passportFile)
    if (g28File) form.append('g28', g28File)
    return form
  }

  const formatApiError = (err) => {
    const d = err?.detail
    if (typeof d === 'string') return d
    if (d && typeof d === 'object' && d.validation_errors) {
      const parts = []
      if (d.validation_errors.passport) parts.push(`Passport: ${d.validation_errors.passport}`)
      if (d.validation_errors.g28) parts.push(`G-28: ${d.validation_errors.g28}`)
      if (parts.length) return `The uploaded document(s) are not valid. ${parts.join(' ')}`
      return d.detail || 'Document validation failed. Please upload a valid passport and/or G-28 form.'
    }
    return (d && d.detail) || (typeof d === 'string' ? d : null) || JSON.stringify(err?.detail ?? err) || 'Request failed'
  }

  const handleExtract = async () => {
    const form = buildFormData(false)
    if (form.get('passport') || form.get('g28')) {
      setError(null)
      setResult(null)
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

  return (
    <div className="app">
      <header className="header">
        <h1>Document & Form Automation</h1>
        <p>Upload passport and/or G-28 (PDF or image). Extract data and optionally fill the form.</p>
      </header>

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

      {error && (
        <div className="message error">
          {error}
        </div>
      )}

      {result && (
        <section className="result">
          <h2>Result</h2>
          {result.opened_in_existing_browser ? (
            <p className="filled">Original form opened and filled in a Chrome tab. The tab remains open for you to review/edit.</p>
          ) : (
            <p className="warn">
              Could not open/fill in your existing Chrome tab. Start Chrome with remote debugging first:
              {' '}
              <code>/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222</code>
            </p>
          )}
          {result.filled_fields?.length > 0 && (
            <p className="filled">Filled fields: {result.filled_fields.join(', ')}</p>
          )}
          {result.errors?.length > 0 && (
            <p className="warn">Warnings: {result.errors.join('; ')}</p>
          )}
          <pre className="json">{JSON.stringify(result.extracted, null, 2)}</pre>
        </section>
      )}
    </div>
  )
}

export default App
