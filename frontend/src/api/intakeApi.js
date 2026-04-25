import { API_BASE } from '../config'
import { formatApiError } from './extractionApi'

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

export async function createIntakeJob({ passportFile, g28File }) {
  const form = new FormData()
  if (passportFile) form.append('passport', passportFile)
  if (g28File) form.append('g28', g28File)
  const res = await fetch(`${API_BASE}/intake/jobs`, { method: 'POST', body: form })
  return parseJsonOrThrow(res)
}

export async function getIntakeJob(jobId) {
  const res = await fetch(`${API_BASE}/intake/jobs/${encodeURIComponent(jobId)}`)
  return parseJsonOrThrow(res)
}

export async function getIntakeFields(jobId) {
  const res = await fetch(`${API_BASE}/intake/jobs/${encodeURIComponent(jobId)}/fields`)
  return parseJsonOrThrow(res)
}

export async function patchIntakeFields(jobId, patches) {
  const res = await fetch(`${API_BASE}/intake/jobs/${encodeURIComponent(jobId)}/fields`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ patches }),
  })
  return parseJsonOrThrow(res)
}

export async function promoteIntakeJob(jobId, payload = {}) {
  const res = await fetch(`${API_BASE}/intake/jobs/${encodeURIComponent(jobId)}/promote-to-session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return parseJsonOrThrow(res)
}

export function intakeArtifactUrl(pathWithQuery) {
  if (!pathWithQuery) return ''
  if (pathWithQuery.startsWith('http')) return pathWithQuery
  return `${API_BASE}${pathWithQuery}`
}
