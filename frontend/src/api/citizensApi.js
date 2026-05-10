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

export async function listCitizens({ limit = 80, offset = 0, q, status } = {}) {
  const sp = new URLSearchParams()
  sp.set('limit', String(limit))
  sp.set('offset', String(offset))
  if (q?.trim()) sp.set('q', q.trim())
  if (status?.trim()) sp.set('status', status.trim())
  const res = await fetch(`${API_BASE}/citizens?${sp.toString()}`)
  return parseJsonOrThrow(res)
}

export async function createCitizen(body) {
  const res = await fetch(`${API_BASE}/citizens`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrow(res)
}

export async function getCitizen(id, { includeSessions = false } = {}) {
  const sp = new URLSearchParams()
  if (includeSessions) {
    sp.set('include_sessions', 'true')
    sp.set('session_limit', '40')
  }
  const q = sp.toString()
  const res = await fetch(`${API_BASE}/citizens/${id}${q ? `?${q}` : ''}`)
  return parseJsonOrThrow(res)
}

export async function patchCitizen(id, body) {
  const res = await fetch(`${API_BASE}/citizens/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrow(res)
}

export async function deleteCitizen(id) {
  const res = await fetch(`${API_BASE}/citizens/${id}`, { method: 'DELETE' })
  return parseJsonOrThrow(res)
}
