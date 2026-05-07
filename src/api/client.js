const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function apiFetch(path, { token, ...opts } = {}) {
  const headers = { 'Content-Type': 'application/json', ...opts.headers }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${BASE}${path}`, { ...opts, headers })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail ?? `API error ${res.status}`)
  }
  if (res.status === 204 || res.headers.get('content-length') === '0') return null
  return res.json()
}
