import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Upload, FileSearch, ScanText, Braces, Search,
  Sparkles, ArrowRightLeft, GitCompareArrows, Award,
  CheckCircle, Loader2, XCircle, Clock,
} from 'lucide-react'
import type { ProgressEvent, AnyAssessmentResult } from '../types/assessment'
import { PIPELINE_STAGES } from '../types/assessment'
import { assessmentApi } from '../api/assessment-api'

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

export const ProgressTracker = ({ taskId, onComplete, onError }: Props) => {
  const [currentStage, setCurrentStage] = useState<string | null>(null)
  const [completedStages, setCompletedStages] = useState<string[]>([])
  const [message, setMessage] = useState('')
  const [status, setStatus] = useState<'running' | 'completed' | 'error'>('running')
  const [errorMessage, setErrorMessage] = useState('')
  const [elapsed, setElapsed] = useState(0)
  const startTimeRef = useRef<number>(0)

  // Elapsed timer — startTime captured in ref on mount only
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
      // Exponential backoff: 1s, 1.5s, 2.25s … capped at 5s
      const delay = Math.min(1000 * 1.5 ** attempt, 5000)
      await new Promise((resolve) => setTimeout(resolve, delay))
    }
    throw new Error('Timed out waiting for the final result')
  }, [taskId, onComplete])

  useEffect(() => {
    const controller = new AbortController()
    const es = assessmentApi.createProgressStream(taskId)
    let taskCompleted = false
    let fallbackStarted = false

    const startPollingFallback = () => {
      if (fallbackStarted || controller.signal.aborted) return
      fallbackStarted = true
      setMessage('Realtime updates were interrupted. Waiting for the final result…')
      fetchResult(controller.signal).catch((err) => {
        if (!controller.signal.aborted) {
          setStatus('error')
          const nextError = err instanceof Error ? err.message : 'Failed to retrieve result'
          setErrorMessage(nextError)
          onError(nextError)
        }
      })
    }

    es.onmessage = (event) => {
      try {
        const data: ProgressEvent = JSON.parse(event.data)

        setCurrentStage(data.stage)
        setCompletedStages(data.completed_stages)
        setMessage(data.message)

        if (data.stage === 'completed') {
          taskCompleted = true
          es.close()
          startPollingFallback()
        }

        if (data.status === 'error') {
          taskCompleted = true
          setStatus('error')
          setErrorMessage(data.message)
          es.close()
          onError(data.message)
        }
      } catch {
        // ignore parse errors from non-JSON keepalive frames
      }
    }

    es.onerror = () => {
      es.close()
      // Only poll for result if the task wasn't already handled
      if (!taskCompleted) {
        startPollingFallback()
      }
    }

    return () => {
      controller.abort()
      es.close()
    }
  }, [taskId, fetchResult, onError])

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
