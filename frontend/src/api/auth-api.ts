import type { AuthResponse, RefreshResponse } from '../types/auth'
import { getApiUrl } from './assessment-api'

async function postJson<T>(url: string, body: Record<string, unknown>, headers?: Record<string, string>): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(body),
  })

  const text = await res.text()
  const data = text ? JSON.parse(text) : null

  if (!res.ok) {
    const message = data?.error || `Request failed (${res.status})`
    const err = new Error(message) as Error & { status: number }
    err.status = res.status
    throw err
  }

  return data as T
}

export const authApi = {
  register: (email: string, password: string, role?: string): Promise<AuthResponse> => {
    return postJson<AuthResponse>(getApiUrl('/auth/register'), { email, password, role: role || 'teacher' })
  },

  login: (email: string, password: string): Promise<AuthResponse> => {
    return postJson<AuthResponse>(getApiUrl('/auth/login'), { email, password })
  },

  refresh: (refreshToken: string): Promise<RefreshResponse> => {
    return postJson<RefreshResponse>(
      getApiUrl('/auth/refresh'),
      {},
      { Authorization: `Bearer ${refreshToken}` },
    )
  },
}
