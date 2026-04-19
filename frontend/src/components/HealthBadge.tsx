import { useEffect, useState, useCallback } from 'react'
import { Activity, CheckCircle, AlertTriangle, XCircle } from 'lucide-react'
import type { HealthStatus } from '../types/assessment'
import { assessmentApi, getUserFacingErrorMessage } from '../api/assessment-api'

type BadgeStatus = 'loading' | 'ready' | 'degraded' | 'unavailable'

const POLL_INTERVAL = 30_000

const capabilityLabels = [
  { key: 'ocr', label: 'OCR' },
  { key: 'semantic_similarity', label: 'Semantic' },
  { key: 'llm', label: 'LLM' },
  { key: 'pdf', label: 'PDF' },
] as const

export const HealthBadge = () => {
  const [badgeStatus, setBadgeStatus] = useState<BadgeStatus>('loading')
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [errorMessage, setErrorMessage] = useState('')

  const check = useCallback(() => {
    assessmentApi.getHealth()
      .then((nextHealth: HealthStatus) => {
        setHealth(nextHealth)
        setErrorMessage('')
        setBadgeStatus(nextHealth.status === 'healthy' ? 'ready' : 'degraded')
      })
      .catch((error) => {
        setHealth(null)
        setErrorMessage(getUserFacingErrorMessage(error))
        setBadgeStatus('unavailable')
      })
  }, [])

  useEffect(() => {
    check()
    const id = setInterval(check, POLL_INTERVAL)
    return () => clearInterval(id)
  }, [check])

  const config: Record<BadgeStatus, { icon: React.ElementType; label: string; color: string; pulse?: boolean }> = {
    loading:     { icon: Activity,      label: 'Checking...', color: 'var(--color-warning)', pulse: true },
    ready:       { icon: CheckCircle,   label: 'Ready',       color: 'var(--color-success)' },
    degraded:    { icon: AlertTriangle, label: 'Limited',     color: 'var(--color-warning)' },
    unavailable: { icon: XCircle,       label: 'API offline', color: 'var(--color-error)' },
  }

  const { icon: Icon, label, color, pulse } = config[badgeStatus]

  return (
    <button
      type="button"
      onClick={check}
      title={errorMessage || 'Click to recheck capabilities'}
      className="flex flex-col items-start gap-2 px-3 py-2 rounded-md text-xs cursor-pointer"
      style={{ background: 'var(--color-surface-2)', border: '1px solid var(--color-border)' }}
    >
      <div className="flex items-center gap-2">
        <Icon size={12} className={pulse ? 'subtle-pulse' : ''} style={{ color }} />
        <span style={{ color }}>{label}</span>
      </div>

      {health && (
        <div className="flex flex-wrap gap-1.5">
          {capabilityLabels.map(({ key, label: capabilityLabel }) => {
            const available = health.capabilities[key]
            return (
              <span
                key={key}
                className="px-2 py-0.5 rounded-md"
                style={{
                  color: available ? 'var(--color-success)' : 'var(--color-text-disabled)',
                  background: available ? 'var(--color-accent-subtle)' : 'var(--color-surface-3)',
                }}
              >
                {capabilityLabel}
              </span>
            )
          })}
        </div>
      )}
    </button>
  )
}
