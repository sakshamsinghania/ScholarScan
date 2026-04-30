import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Upload, FileSearch, ScanText, Braces, Search,
  Sparkles, ArrowRightLeft, GitCompareArrows, Award,
  CheckCircle, Loader2, XCircle, Clock, WifiOff,
} from 'lucide-react'
import type { AnyAssessmentResult } from '../types/assessment'
import { PIPELINE_STAGES } from '../types/assessment'
import { assessmentApi } from '../api/assessment-api'
import { streamProgress } from '../api/sse'
import { useAuth } from '../auth/useAuth'

const iconMap: Record<string, React.ElementType> = {
  Upload, FileSearch, ScanText, Braces, Search,
  Sparkles, ArrowRightLeft, GitCompare: GitCompareArrows,
  Award, CheckCircle,
}

interface Props {
  taskId: string
  onComplete: (result: AnyAssessmentResult) => void
  onError: (error: string) => void
}

type StepStatus = 'pending' | 'running' | 'completed' | 'error'
const MAX_RESULT_POLL_ATTEMPTS = 60
const HEARTBEAT_TIMEOUT_MS = 30_000

export const ProgressTracker = ({ taskId, onComplete, onError }: Props) => {
  const { accessToken } = useAuth()
  const [currentStage, setCurrentStage] = useState<string | null>(null)
  const [completedStages, setCompletedStages] = useState<string[]>([])
  const [message, setMessage] = useState('')
  const [status, setStatus] = useState<'running' | 'completed' | 'error'>('running')
  const [errorMessage, setErrorMessage] = useState('')
  const [elapsed, setElapsed] = useState(0)
  const [reconnecting, setReconnecting] = useState(false)
  const startTimeRef = useRef<number>(0)

  useEffect(() => {
    startTimeRef.current = Date.now()
  }, [])

  useEffect(() => {
    if (status !== 'running') return
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000))
    }, 1000)
    return () => clearInterval(interval)
  }, [status])

  const fetchResult = useCallback(async (signal: AbortSignal) => {
    for (let attempt = 0; attempt < MAX_RESULT_POLL_ATTEMPTS; attempt++) {
      if (signal.aborted) return
      const res = await assessmentApi.getTaskResult(taskId, signal)
      if (res.status === 200) {
        const result = await res.json()
        setStatus('completed')
        onComplete(result)
        return
      }
      if (res.status !== 202) {
        throw new Error(`Unexpected status ${res.status}`)
      }
      const delay = Math.min(1000 * 1.5 ** attempt, 5000)
      await new Promise((resolve) => setTimeout(resolve, delay))
    }
    throw new Error('Timed out waiting for the final result')
  }, [taskId, onComplete])

  useEffect(() => {
    const controller = new AbortController()
    let taskCompleted = false
    let retryCount = 0

    const startPollingFallback = () => {
      if (controller.signal.aborted) return
      setMessage('Realtime updates were interrupted. Waiting for the final result…')
      setReconnecting(false)
      fetchResult(controller.signal).catch((err) => {
        if (!controller.signal.aborted) {
          setStatus('error')
          const nextError = err instanceof Error ? err.message : 'Failed to retrieve result'
          setErrorMessage(nextError)
          onError(nextError)
        }
      })
    }

    const connectSSE = async () => {
      if (taskCompleted || controller.signal.aborted) return

      try {
        let lastEventTime = Date.now()
        const heartbeatCheck = setInterval(() => {
          if (Date.now() - lastEventTime > HEARTBEAT_TIMEOUT_MS && !taskCompleted) {
            clearInterval(heartbeatCheck)
            if (retryCount < 1) {
              retryCount++
              setReconnecting(true)
              setMessage('Lost connection, reconnecting…')
              connectSSE()
            } else {
              startPollingFallback()
            }
          }
        }, 5000)

        for await (const data of streamProgress(taskId, accessToken, controller.signal)) {
          lastEventTime = Date.now()
          setReconnecting(false)

          setCurrentStage(data.stage)
          setCompletedStages(data.completed_stages)
          setMessage(data.message)

          if (data.stage === 'completed') {
            taskCompleted = true
            clearInterval(heartbeatCheck)
            startPollingFallback()
            return
          }

          if (data.status === 'error') {
            taskCompleted = true
            clearInterval(heartbeatCheck)
            setStatus('error')
            setErrorMessage(data.message)
            onError(data.message)
            return
          }
        }

        clearInterval(heartbeatCheck)
        if (!taskCompleted) {
          startPollingFallback()
        }
      } catch (err) {
        if (controller.signal.aborted) return

        if (err instanceof Error && err.message === 'AUTH_EXPIRED') {
          if (typeof (window as unknown as Record<string, unknown>).__scholarscan_refresh === 'function') {
            try {
              await ((window as unknown as Record<string, unknown>).__scholarscan_refresh as () => Promise<string>)()
              connectSSE()
              return
            } catch {
              // refresh failed — fall through
            }
          }
          setStatus('error')
          setErrorMessage('Session expired')
          onError('Session expired')
          return
        }

        if (retryCount < 1 && !taskCompleted) {
          retryCount++
          setReconnecting(true)
          setMessage('Lost connection, reconnecting…')
          setTimeout(connectSSE, 2000)
        } else if (!taskCompleted) {
          startPollingFallback()
        }
      }
    }

    connectSSE()

    return () => {
      controller.abort()
    }
  }, [taskId, accessToken, fetchResult, onError])

  const getStepStatus = (stageKey: string): StepStatus => {
    if (completedStages.includes(stageKey)) return 'completed'
    if (stageKey === currentStage) {
      if (status === 'error') return 'error'
      return 'running'
    }
    return 'pending'
  }

  const formatTime = (s: number) => {
    const mins = Math.floor(s / 60)
    const secs = s % 60
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
  }

  return (
    <div className="surface-1 p-6 animate-fade-in" role="status" aria-live="polite">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2.5">
          {status === 'running' ? (
            <Loader2 size={16} className="animate-spin" style={{ color: 'var(--color-accent)' }} />
          ) : status === 'error' ? (
            <XCircle size={16} style={{ color: 'var(--color-error)' }} />
          ) : (
            <CheckCircle size={16} style={{ color: 'var(--color-success)' }} />
          )}
          <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
            {status === 'completed' ? 'Assessment complete' : status === 'error' ? 'Pipeline error' : 'Processing…'}
          </h3>
        </div>
        <div className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
          <Clock size={12} />
          {formatTime(elapsed)}
        </div>
      </div>

      {/* Reconnecting banner */}
      {reconnecting && (
        <div className="flex items-center gap-2 mb-4 px-3 py-2 rounded-lg text-xs animate-fade-in" style={{ background: 'rgba(224, 168, 75, 0.1)', border: '1px solid rgba(224, 168, 75, 0.2)', color: 'var(--color-warning)' }}>
          <WifiOff size={14} />
          Lost connection, reconnecting…
        </div>
      )}

      {/* Vertical stepper */}
      <div className="relative ml-0.5">
        {PIPELINE_STAGES.map((stage, i) => {
          const stepStatus = getStepStatus(stage.key)
          const Icon = iconMap[stage.icon] || CheckCircle
          const isLast = i === PIPELINE_STAGES.length - 1

          return (
            <div key={stage.key} className="flex gap-3.5 relative" style={{ minHeight: isLast ? 'auto' : '44px' }}>
              {/* Connector */}
              {!isLast && (
                <div
                  className="absolute left-[11px] top-[24px] w-px"
                  style={{
                    height: '24px',
                    background: stepStatus === 'completed'
                      ? 'var(--color-accent)'
                      : 'var(--color-border)',
                    transition: 'background 0.3s ease',
                  }}
                />
              )}

              {/* Dot */}
              <div className="relative z-10 flex-shrink-0">
                <StepDot status={stepStatus} Icon={Icon} />
              </div>

              {/* Label */}
              <div className="pb-2 pt-0.5 min-w-0">
                <p
                  className="text-sm transition-colors duration-200"
                  style={{
                    color: stepStatus === 'completed' ? 'var(--color-text-secondary)'
                      : stepStatus === 'running' ? 'var(--color-text-primary)'
                      : stepStatus === 'error' ? 'var(--color-error)'
                      : 'var(--color-text-disabled)',
                    fontWeight: stepStatus === 'running' ? 500 : 400,
                  }}
                >
                  {stage.label}
                </p>
                {stepStatus === 'running' && message && (
                  <p className="text-xs mt-0.5 animate-fade-in" style={{ color: 'var(--color-accent)' }}>
                    {message}
                  </p>
                )}
                {stepStatus === 'error' && errorMessage && (
                  <p className="text-xs mt-0.5" style={{ color: 'var(--color-error)' }}>
                    {errorMessage}
                  </p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ── Step dot ── */
const StepDot = ({ status, Icon }: { status: StepStatus; Icon: React.ElementType }) => {
  const size = 24

  if (status === 'completed') {
    return (
      <div
        className="rounded-full flex items-center justify-center step-enter"
        style={{
          width: size, height: size,
          background: 'var(--color-accent-subtle)',
          border: '1.5px solid var(--color-accent)',
        }}
      >
        <CheckCircle size={12} style={{ color: 'var(--color-accent)' }} />
      </div>
    )
  }

  if (status === 'running') {
    return (
      <div
        className="rounded-full flex items-center justify-center subtle-pulse"
        style={{
          width: size, height: size,
          background: 'var(--color-accent-subtle)',
          border: '1.5px solid var(--color-accent)',
        }}
      >
        <Icon size={12} style={{ color: 'var(--color-accent)' }} />
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div
        className="rounded-full flex items-center justify-center"
        style={{
          width: size, height: size,
          background: 'var(--color-error-subtle)',
          border: '1.5px solid var(--color-error)',
        }}
      >
        <XCircle size={12} style={{ color: 'var(--color-error)' }} />
      </div>
    )
  }

  // Pending
  return (
    <div
      className="rounded-full flex items-center justify-center"
      style={{
        width: size, height: size,
        background: 'var(--color-surface-2)',
        border: '1.5px solid var(--color-border)',
      }}
    >
      <Icon size={11} style={{ color: 'var(--color-text-disabled)' }} />
    </div>
  )
}
