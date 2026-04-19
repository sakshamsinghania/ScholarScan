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

type ApiErrorKind = 'transport' | 'timeout' | 'response'

export class ApiError extends Error {
  kind: ApiErrorKind
  status?: number
  url: string

  constructor(message: string, options: { kind: ApiErrorKind; url: string; status?: number }) {
    super(message)
    this.name = 'ApiError'
    this.kind = options.kind
    this.url = options.url
    this.status = options.status
  }
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

const toResponseError = (input: RequestInfo, status: number, data: unknown) => {
  return new ApiError(getErrorMessage(data, status), {
    kind: 'response',
    status,
    url: getInputUrl(input),
  })
}

export const isApiOutageError = (error: unknown): error is ApiError => {
  return error instanceof ApiError && (error.kind === 'transport' || error.kind === 'timeout')
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
): Promise<T> {
  const { signal, cleanup } = withTimeout(timeoutMs, init?.signal)

  let res: Response
  try {
    res = await fetch(input, { ...init, signal })
  } catch (error) {
    cleanup()
    console.error('[assessmentApi] request failed', { input: getInputUrl(input), error })
    throw toApiError(input, error)
  }

  const text = await res.text()
  cleanup()
  const data = parseJson(text)

  if (!res.ok) {
    console.error('[assessmentApi] non-ok response', { input: getInputUrl(input), status: res.status, data })
    throw toResponseError(input, res.status, data)
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
    const timeout = withTimeout(POLL_REQUEST_TIMEOUT_MS, signal)

    let res: Response
    try {
      res = await fetch(url, { signal: timeout.signal })
    } catch (error) {
      console.error('[assessmentApi] task result request failed', { url, error })
      throw toApiError(url, error)
    }

    if (res.status === 200 || res.status === 202) {
      timeout.cleanup()
      return res
    }

    const text = await res.text()
    timeout.cleanup()
    const data = parseJson(text)
    console.error('[assessmentApi] unexpected task result response', { url, status: res.status, data })
    throw toResponseError(url, res.status, data)
  },

  createProgressStream: (taskId: string): EventSource => {
    return new EventSource(getApiUrl(`/progress/stream/${taskId}`))
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
    return requestJson<HealthStatus>(getApiUrl('/health'))
  },
}

export const isTaskStart = (
  res: AnyAssessmentResult | TaskStartResponse
): res is TaskStartResponse => {
  return 'task_id' in res && 'status' in res && (res as TaskStartResponse).status === 'processing'
}
