import type { UserPublic } from '../types/auth'

const STORAGE_KEY = 'scholarscan.auth'

interface StoredAuth {
  user: UserPublic
  accessToken: string
  refreshToken: string
}

export function loadAuth(): StoredAuth | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed.accessToken || !parsed.refreshToken || !parsed.user) return null
    return parsed as StoredAuth
  } catch {
    return null
  }
}

export function saveAuth(auth: StoredAuth): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(auth))
}

export function clearAuth(): void {
  localStorage.removeItem(STORAGE_KEY)
}

export function decodeTokenExp(token: string): number | null {
  try {
    const payload = token.split('.')[1]
    const decoded = JSON.parse(atob(payload))
    return typeof decoded.exp === 'number' ? decoded.exp : null
  } catch {
    return null
  }
}
