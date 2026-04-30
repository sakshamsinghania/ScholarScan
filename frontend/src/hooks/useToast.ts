import { useCallback, useSyncExternalStore } from 'react'

export type ToastVariant = 'info' | 'warning' | 'error'

interface Toast {
  id: number
  message: string
  variant: ToastVariant
  expiresAt: number
}

let nextId = 0
let toasts: Toast[] = []
const listeners = new Set<() => void>()

function notify() {
  listeners.forEach((l) => l())
}

function addToast(message: string, variant: ToastVariant, durationMs = 5000) {
  const toast: Toast = { id: ++nextId, message, variant, expiresAt: Date.now() + durationMs }
  toasts = [...toasts, toast]
  notify()
  setTimeout(() => {
    toasts = toasts.filter((t) => t.id !== toast.id)
    notify()
  }, durationMs)
}

function dismissToast(id: number) {
  toasts = toasts.filter((t) => t.id !== id)
  notify()
}

function subscribe(cb: () => void) {
  listeners.add(cb)
  return () => { listeners.delete(cb) }
}

function getSnapshot() {
  return toasts
}

export function useToast() {
  const current = useSyncExternalStore(subscribe, getSnapshot)

  const info = useCallback((msg: string, duration?: number) => addToast(msg, 'info', duration), [])
  const warning = useCallback((msg: string, duration?: number) => addToast(msg, 'warning', duration), [])
  const error = useCallback((msg: string, duration?: number) => addToast(msg, 'error', duration), [])
  const dismiss = useCallback((id: number) => dismissToast(id), [])

  return { toasts: current, info, warning, error, dismiss }
}

export { addToast }
