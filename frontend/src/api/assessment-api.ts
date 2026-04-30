import type { AnyAssessmentResult, HealthStatus, ResultsResponse, TaskStartResponse } from '../types/assessment'

const trimTrailingSlash = (value: string) => value.replace(/\/+$/, '')
const DEFAULT_LOCAL_API_PORT = '5050'
const LOCAL_DEV_HOSTS = new Set(['localhost', '127.0.0.1'])

const resolveApiBase = () => {
  const configuredBase = import.meta.env.VITE_API_BASE_URL?.trim()
  if (configuredBase) {
    return trimTrailingSlash(configuredBase)
  }

  if (
    typeof window !== 'undefined'
    && import.meta.env.DEV
    && LOCAL_DEV_HOSTS.has(window.location.hostname)
  ) {
    const apiPort = import.meta.env.VITE_API_PORT?.trim() || DEFAULT_LOCAL_API_PORT
    return `${window.location.protocol}//${window.location.hostname}:${apiPort}/api`
  }

  return '/api'
}

const API_BASE = resolveApiBase()
const DEFAULT_REQUEST_TIMEOUT_MS = 15_000
const POLL_REQUEST_TIMEOUT_MS = 10_000

const MAX_FILE_SIZE = 16 * 1024 * 1024 // 16 MB

const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf'] as const

if (import.meta.env.PROD && !import.meta.env.VITE_API_BASE_URL) {
  console.warn('[ScholarScan] VITE_API_BASE_URL not set in production build — falling back to /api')
}

type ApiErrorKind = 'transport' | 'timeout' | 'response' | 'rate_limited' | 'forbidden'

export class ApiError extends Error {
  kind: ApiErrorKind
  status?: number
  url: string
  code?: string
  retryAfterSec?: number

  constructor(message: string, options: { kind: ApiErrorKind; url: string; status?: number; code?: string; retryAfterSec?: number }) {
    super(message)
    this.name = 'ApiError'
    this.kind = options.kind
    this.url = options.url
    this.status = options.status
    this.code = options.code
    this.retryAfterSec = options.retryAfterSec
  }
}

// -- Auth wiring (set by AuthContext) --

let _getToken: () => string | null = () => null
let _onAuthFailure: () => void = () => {}

export function setAuthTokenGetter(getter: () => string | null) {
  _getToken = getter
}

export function setOnAuthFailure(handler: () => void) {
  _onAuthFailure = handler
}

function getAuthHeaders(): Record<string, string> {
  const token = _getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// -- Refresh interceptor (single-flight) --

async function refreshAndRetry<T>(
  input: RequestInfo,
  init: RequestInit | undefined,
  timeoutMs: number,
): Promise<T> {
  const refreshFn = (window as unknown as Record<string, unknown>).__scholarscan_refresh as
    | (() => Promise<string>)
    | undefined

  if (!refreshFn) {
    _onAuthFailure()
    throw new ApiError('Session expired', { kind: 'response', url: getInputUrl(input), status: 401 })
  }

  let newToken: string
  try {
    newToken = await refreshFn()
  } catch {
    _onAuthFailure()
    throw new ApiError('Session expired', { kind: 'response', url: getInputUrl(input), status: 401 })
  }

  if (!newToken) {
    _onAuthFailure()
    throw new ApiError('Session expired', { kind: 'response', url: getInputUrl(input), status: 401 })
  }

  const retryHeaders = { ...(init?.headers as Record<string, string> || {}), Authorization: `Bearer ${newToken}` }
  return requestJson<T>(input, { ...init, headers: retryHeaders }, timeoutMs, false)
}

const getErrorMessage = (data: unknown, status: number) => {
  if (data && typeof data === 'object' && 'error' in data && typeof data.error === 'string') {
    return data.error
  }

  if (status >= 500) {
    return 'The assessment API returned an internal error. Check the backend logs and try again.'
  }

  return `Request failed (${status})`
}

const getErrorCode = (data: unknown): string | undefined => {
  if (data && typeof data === 'object' && 'code' in data) {
    return String((data as Record<string, unknown>).code)
  }
  return undefined
}

const parseJson = (text: string) => {
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

const getInputUrl = (input: RequestInfo) => typeof input === 'string' ? input : input.url

const getTransportMessage = (kind: ApiErrorKind) => {
  if (kind === 'timeout') {
    return 'The assessment API took too long to respond. Check that the backend is running, then try again.'
  }

  return "Couldn't reach the assessment API. Make sure the backend is running and the dev proxy or API base URL is configured correctly."
}

const toApiError = (input: RequestInfo, error: unknown) => {
  const kind: ApiErrorKind = error instanceof DOMException && error.name === 'AbortError'
    ? 'timeout'
    : 'transport'

  return new ApiError(getTransportMessage(kind), {
    kind,
    url: getInputUrl(input),
  })
}

export const isApiOutageError = (error: unknown): error is ApiError => {
  return error instanceof ApiError && (error.kind === 'transport' || error.kind === 'timeout')
}

export const isRateLimitError = (error: unknown): error is ApiError => {
  return error instanceof ApiError && error.kind === 'rate_limited'
}

export const getUserFacingErrorMessage = (error: unknown) => {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return 'Unexpected error'
}

const withTimeout = (timeoutMs: number, signal?: AbortSignal | null) => {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)
  const abortFromParent = () => controller.abort()

  if (signal) {
    if (signal.aborted) {
      controller.abort()
    } else {
      signal.addEventListener('abort', abortFromParent, { once: true })
    }
  }

  return {
    signal: controller.signal,
    cleanup: () => {
      window.clearTimeout(timeoutId)
      signal?.removeEventListener('abort', abortFromParent)
    },
  }
}

async function requestJson<T>(
  input: RequestInfo,
  init?: RequestInit,
  timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS,
  allowRefreshRetry = true,
): Promise<T> {
  const authHeaders = getAuthHeaders()
  const mergedHeaders = { ...authHeaders, ...(init?.headers as Record<string, string> || {}) }
  const mergedInit = { ...init, headers: mergedHeaders }

  const { signal, cleanup } = withTimeout(timeoutMs, init?.signal)

  let res: Response
  try {
    res = await fetch(input, { ...mergedInit, signal })
  } catch (error) {
    cleanup()
    console.error('[assessmentApi] request failed', { input: getInputUrl(input), error })
    throw toApiError(input, error)
  }

  const text = await res.text()
  cleanup()
  const data = parseJson(text)

  if (res.status === 401 && allowRefreshRetry) {
    return refreshAndRetry<T>(input, init, timeoutMs)
  }

  if (res.status === 403) {
    throw new ApiError(
      getErrorMessage(data, res.status) || "You don't have access to this resource",
      { kind: 'forbidden', url: getInputUrl(input), status: 403, code: getErrorCode(data) },
    )
  }

  if (res.status === 429) {
    const retryAfter = res.headers.get('Retry-After')
    const retryAfterSec = retryAfter ? parseInt(retryAfter, 10) : undefined
    throw new ApiError(
      retryAfterSec
        ? `Too many requests. Try again in ${retryAfterSec}s`
        : 'Too many requests. Please slow down.',
      { kind: 'rate_limited', url: getInputUrl(input), status: 429, retryAfterSec },
    )
  }

  if (!res.ok) {
    console.error('[assessmentApi] non-ok response', { input: getInputUrl(input), status: res.status, data })
    throw new ApiError(getErrorMessage(data, res.status), {
      kind: 'response',
      status: res.status,
      url: getInputUrl(input),
      code: getErrorCode(data),
    })
  }

  return data as T
}

export const getApiUrl = (path: string) => `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`

export function validateFile(file: File): string | null {
  if (!ALLOWED_MIME_TYPES.includes(file.type as typeof ALLOWED_MIME_TYPES[number])) {
    return 'Please upload a JPG, PNG, or PDF file'
  }
  if (file.size > MAX_FILE_SIZE) {
    return `File exceeds the ${MAX_FILE_SIZE / 1024 / 1024} MB limit`
  }
  return null
}

export const assessmentApi = {
  submitManualAssessment: async (
    imageFile: File,
    modelAnswer: string,
    options?: { studentId?: string; maxMarks?: number }
  ): Promise<AnyAssessmentResult> => {
    const formData = new FormData()
    formData.append('image', imageFile)
    formData.append('model_answer', modelAnswer)

    if (options?.studentId) formData.append('student_id', options.studentId)
    if (options?.maxMarks) formData.append('max_marks', String(options.maxMarks))

    return requestJson<AnyAssessmentResult>(getApiUrl('/assess'), {
      method: 'POST',
      body: formData,
    })
  },

  submitDocumentAssessment: async (
    answerFile: File,
    options?: { questionFile?: File; questionId?: string; studentId?: string; maxMarks?: number }
  ): Promise<TaskStartResponse> => {
    const formData = new FormData()
    formData.append('answer_file', answerFile)

    if (options?.questionFile) formData.append('question_file', options.questionFile)
    if (options?.questionId) formData.append('question_id', options.questionId)
    if (options?.studentId) formData.append('student_id', options.studentId)
    if (options?.maxMarks) formData.append('max_marks', String(options.maxMarks))

    return requestJson<TaskStartResponse>(getApiUrl('/assess'), {
      method: 'POST',
      body: formData,
    })
  },

  getTaskResult: async (taskId: string, signal?: AbortSignal): Promise<Response> => {
    const url = getApiUrl(`/task/${taskId}/result`)
    const authHeaders = getAuthHeaders()
    const timeout = withTimeout(POLL_REQUEST_TIMEOUT_MS, signal)

    let res: Response
    try {
      res = await fetch(url, { signal: timeout.signal, headers: authHeaders })
    } catch (error) {
      console.error('[assessmentApi] task result request failed', { url, error })
      throw toApiError(url, error)
    }

    if (res.status === 401) {
      timeout.cleanup()
      const refreshFn = (window as unknown as Record<string, unknown>).__scholarscan_refresh as
        | (() => Promise<string>)
        | undefined
      if (refreshFn) {
        try {
          const newToken = await refreshFn()
          const retryTimeout = withTimeout(POLL_REQUEST_TIMEOUT_MS, signal)
          const retryRes = await fetch(url, { signal: retryTimeout.signal, headers: { Authorization: `Bearer ${newToken}` } })
          retryTimeout.cleanup()
          return retryRes
        } catch {
          _onAuthFailure()
          throw new ApiError('Session expired', { kind: 'response', url, status: 401 })
        }
      }
      _onAuthFailure()
      throw new ApiError('Session expired', { kind: 'response', url, status: 401 })
    }

    if (res.status === 200 || res.status === 202) {
      timeout.cleanup()
      return res
    }

    const text = await res.text()
    timeout.cleanup()
    const data = parseJson(text)
    console.error('[assessmentApi] unexpected task result response', { url, status: res.status, data })

    if (res.status === 429) {
      const retryAfter = res.headers.get('Retry-After')
      const retryAfterSec = retryAfter ? parseInt(retryAfter, 10) : undefined
      throw new ApiError('Too many requests', { kind: 'rate_limited', url, status: 429, retryAfterSec })
    }

    throw new ApiError(getErrorMessage(data, res.status), {
      kind: res.status === 403 ? 'forbidden' : 'response',
      status: res.status,
      url,
      code: getErrorCode(data),
    })
  },

  getResults: async (filters?: {
    studentId?: string
    questionId?: string
  }): Promise<ResultsResponse> => {
    const params = new URLSearchParams()
    if (filters?.studentId) params.set('student_id', filters.studentId)
    if (filters?.questionId) params.set('question_id', filters.questionId)

    const url = `${getApiUrl('/results')}${params.toString() ? `?${params}` : ''}`
    return requestJson<ResultsResponse>(url)
  },

  getHealth: async (): Promise<HealthStatus> => {
    return requestJson<HealthStatus>(getApiUrl('/health'), undefined, DEFAULT_REQUEST_TIMEOUT_MS, false)
  },
}

export const isTaskStart = (
  res: AnyAssessmentResult | TaskStartResponse
): res is TaskStartResponse => {
  return 'task_id' in res && 'status' in res && (res as TaskStartResponse).status === 'processing'
}
