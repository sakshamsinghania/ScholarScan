import { X, Info, AlertTriangle, XCircle } from 'lucide-react'
import { useToast, type ToastVariant } from '../hooks/useToast'

const variantConfig: Record<ToastVariant, { icon: React.ElementType; bg: string; color: string; border: string }> = {
  info: {
    icon: Info,
    bg: 'var(--color-accent-subtle)',
    color: 'var(--color-accent)',
    border: 'var(--color-accent-border)',
  },
  warning: {
    icon: AlertTriangle,
    bg: 'rgba(224, 168, 75, 0.1)',
    color: 'var(--color-warning)',
    border: 'rgba(224, 168, 75, 0.2)',
  },
  error: {
    icon: XCircle,
    bg: 'var(--color-error-subtle)',
    color: 'var(--color-error)',
    border: 'rgba(217, 83, 79, 0.2)',
  },
}

export const ToastHost = () => {
  const { toasts, dismiss } = useToast()

  if (toasts.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((toast) => {
        const cfg = variantConfig[toast.variant]
        const Icon = cfg.icon
        return (
          <div
            key={toast.id}
            className="flex items-start gap-2.5 px-4 py-3 rounded-lg text-sm animate-fade-in"
            style={{ background: cfg.bg, border: `1px solid ${cfg.border}`, color: cfg.color }}
            role="alert"
          >
            <Icon size={16} className="mt-0.5 flex-shrink-0" />
            <span className="flex-1" style={{ color: 'var(--color-text-primary)' }}>{toast.message}</span>
            <button
              type="button"
              onClick={() => dismiss(toast.id)}
              className="p-0.5 rounded hover-surface-3 flex-shrink-0"
              style={{ color: 'var(--color-text-tertiary)' }}
            >
              <X size={14} />
            </button>
          </div>
        )
      })}
    </div>
  )
}
