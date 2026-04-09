import { API_BASE } from '../config'

/**
 * Normalize FastAPI error payloads (string detail or validation_errors object).
 */
export function formatApiError(err) {
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

async function parseJsonOrThrow(res) {
  if (res.ok) {
    if (res.status === 204) return null
    const ct = res.headers.get('content-type') || ''
    if (ct.includes('application/json')) return res.json()
    return res.text()
  }
  const err = await res.json().catch(() => ({ detail: res.statusText }))
  throw new Error(formatApiError(err))
}

export async function fetchExtractionReadiness(extracted) {
  const res = await fetch(`${API_BASE}/extraction-readiness`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(extracted),
  })
  return parseJsonOrThrow(res)
}

export async function previewFill(extracted) {
  const res = await fetch(`${API_BASE}/preview-fill`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(extracted),
  })
  return parseJsonOrThrow(res)
}

export async function listExtractionSessions(limit = 50, offset = 0) {
  const res = await fetch(`${API_BASE}/extraction-sessions?limit=${limit}&offset=${offset}`)
  return parseJsonOrThrow(res)
}

export async function createExtractionSession(payload) {
  const res = await fetch(`${API_BASE}/extraction-sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return parseJsonOrThrow(res)
}

export async function getExtractionSession(id) {
  const res = await fetch(`${API_BASE}/extraction-sessions/${id}`)
  return parseJsonOrThrow(res)
}

export async function deleteExtractionSession(id) {
  const res = await fetch(`${API_BASE}/extraction-sessions/${id}`, { method: 'DELETE' })
  return parseJsonOrThrow(res)
}

export function extractionSessionExportUrl(id) {
  return `${API_BASE}/extraction-sessions/${id}/export`
}

export async function fillFormFromSession(id, formUrl) {
  const res = await fetch(`${API_BASE}/extraction-sessions/${id}/fill-form`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ form_url: formUrl.trim() }),
  })
  return parseJsonOrThrow(res)
}
