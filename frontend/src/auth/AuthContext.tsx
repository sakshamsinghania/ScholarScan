import { createContext, useState, useEffect, useCallback, useRef, type ReactNode } from 'react'
import type { UserPublic, AuthStatus } from '../types/auth'
import { loadAuth, saveAuth, clearAuth, decodeTokenExp } from './tokenStorage'
import { authApi } from '../api/auth-api'
import { setAuthTokenGetter, setOnAuthFailure } from '../api/assessment-api'

export interface AuthContextValue {
  user: UserPublic | null
  status: AuthStatus
  accessToken: string | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, role?: string) => Promise<void>
  logout: () => void
}

// eslint-disable-next-line react-refresh/only-export-components
export const AuthContext = createContext<AuthContextValue | null>(null)

const AUTH_DISABLED = import.meta.env.VITE_AUTH_REQUIRED === 'false'
const REFRESH_LEEWAY_SEC = parseInt(import.meta.env.VITE_REFRESH_LEEWAY_SEC || '60', 10)

const ANON_USER: UserPublic = {
  id: 'anon',
  email: 'dev@localhost',
  role: 'teacher',
  created_at: new Date().toISOString(),
}

const _initial = AUTH_DISABLED ? { user: ANON_USER, status: 'authed' as AuthStatus } : (() => {
  const stored = loadAuth()
  return stored ? { user: stored.user, status: 'authed' as AuthStatus } : { user: null, status: 'anon' as AuthStatus }
})()

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<UserPublic | null>(_initial.user)
  const [accessToken, setAccessToken] = useState<string | null>(AUTH_DISABLED ? null : (loadAuth()?.accessToken ?? null))
  const [refreshToken, setRefreshToken] = useState<string | null>(AUTH_DISABLED ? null : (loadAuth()?.refreshToken ?? null))
  const [status, setStatus] = useState<AuthStatus>(_initial.status)
  const refreshTimerRef = useRef<number>(0)
  const refreshPromiseRef = useRef<Promise<string> | null>(null)
  const scheduleRefreshRef = useRef<(token: string, rt: string) => void>(() => {})

  const doLogout = useCallback(() => {
    clearAuth()
    setUser(null)
    setAccessToken(null)
    setRefreshToken(null)
    setStatus('anon')
    window.clearTimeout(refreshTimerRef.current)
    refreshPromiseRef.current = null
  }, [])

  useEffect(() => {
    scheduleRefreshRef.current = (token: string, rt: string) => {
      window.clearTimeout(refreshTimerRef.current)
      const exp = decodeTokenExp(token)
      if (!exp) return

      const msUntilRefresh = (exp - REFRESH_LEEWAY_SEC) * 1000 - Date.now()
      if (msUntilRefresh <= 0) {
        authApi.refresh(rt)
          .then((res) => {
            setAccessToken(res.access_token)
            const stored = loadAuth()
            if (stored) saveAuth({ ...stored, accessToken: res.access_token })
            scheduleRefreshRef.current(res.access_token, rt)
          })
          .catch(() => doLogout())
        return
      }

      refreshTimerRef.current = window.setTimeout(() => {
        if (!refreshPromiseRef.current) {
          refreshPromiseRef.current = authApi.refresh(rt)
            .then((res) => {
              setAccessToken(res.access_token)
              const stored = loadAuth()
              if (stored) saveAuth({ ...stored, accessToken: res.access_token })
              refreshPromiseRef.current = null
              scheduleRefreshRef.current(res.access_token, rt)
              return res.access_token
            })
            .catch(() => {
              refreshPromiseRef.current = null
              doLogout()
              return ''
            })
        }
      }, msUntilRefresh)
    }
  }, [doLogout])

  const scheduleRefresh = useCallback((token: string, rt: string) => {
    scheduleRefreshRef.current(token, rt)
  }, [])

  const setAuthed = useCallback((u: UserPublic, at: string, rt: string) => {
    setUser(u)
    setAccessToken(at)
    setRefreshToken(rt)
    setStatus('authed')
    saveAuth({ user: u, accessToken: at, refreshToken: rt })
    scheduleRefresh(at, rt)
  }, [scheduleRefresh])

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login(email, password)
    setAuthed(res.user, res.access_token, res.refresh_token)
  }, [setAuthed])

  const register = useCallback(async (email: string, password: string, role?: string) => {
    const res = await authApi.register(email, password, role)
    setAuthed(res.user, res.access_token, res.refresh_token)
  }, [setAuthed])

  // Schedule refresh on mount if already authed
  useEffect(() => {
    if (AUTH_DISABLED) return
    const stored = loadAuth()
    if (stored) {
      scheduleRefresh(stored.accessToken, stored.refreshToken)
    }
  }, [scheduleRefresh])

  // Wire token getter for assessment-api
  useEffect(() => {
    setAuthTokenGetter(() => accessToken)
    setOnAuthFailure(doLogout)
  }, [accessToken, doLogout])

  // Expose refresh promise for API interceptor
  useEffect(() => {
    const handler = () => {
      if (!refreshToken) return Promise.reject(new Error('No refresh token'))
      if (refreshPromiseRef.current) return refreshPromiseRef.current
      refreshPromiseRef.current = authApi.refresh(refreshToken)
        .then((res) => {
          setAccessToken(res.access_token)
          const stored = loadAuth()
          if (stored) saveAuth({ ...stored, accessToken: res.access_token })
          refreshPromiseRef.current = null
          scheduleRefresh(res.access_token, refreshToken)
          return res.access_token
        })
        .catch((err) => {
          refreshPromiseRef.current = null
          doLogout()
          throw err
        })
      return refreshPromiseRef.current
    }
    (window as unknown as Record<string, unknown>).__scholarscan_refresh = handler
  }, [refreshToken, doLogout, scheduleRefresh])

  return (
    <AuthContext.Provider value={{ user, status, accessToken, login, register, logout: doLogout }}>
      {children}
    </AuthContext.Provider>
  )
}
