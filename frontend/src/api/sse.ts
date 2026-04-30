import type { ProgressEvent } from '../types/assessment'
import { getApiUrl } from './assessment-api'

export async function* streamProgress(
  taskId: string,
  token: string | null,
  signal: AbortSignal,
): AsyncGenerator<ProgressEvent> {
  const url = getApiUrl(`/progress/stream/${taskId}`)
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(url, { headers, signal })

  if (res.status === 401) {
    throw new Error('AUTH_EXPIRED')
  }

  if (!res.ok) {
    throw new Error(`SSE connection failed (${res.status})`)
  }

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() || ''

    for (const block of blocks) {
      const lines = block.split('\n')
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const payload = line.slice(6).trim()
          if (!payload || payload === '__done') continue
          try {
            yield JSON.parse(payload) as ProgressEvent
          } catch {
            // skip non-JSON keepalive frames
          }
        }
      }
    }
  }

  // Process any remaining buffer
  if (buffer.trim()) {
    const lines = buffer.split('\n')
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const payload = line.slice(6).trim()
        if (!payload || payload === '__done') continue
        try {
          yield JSON.parse(payload) as ProgressEvent
        } catch {
          // skip
        }
      }
    }
  }
}
