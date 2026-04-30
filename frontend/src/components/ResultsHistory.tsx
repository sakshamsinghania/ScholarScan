import { useEffect, useState, useCallback } from 'react'
import { Users, AlertTriangle, RefreshCw, Clock3, XCircle } from 'lucide-react'
import type { HistoryResult, ResultsResponse } from '../types/assessment'
import { assessmentApi, getUserFacingErrorMessage, isApiOutageError } from '../api/assessment-api'

interface Props {
  refreshToken: number
}

type Status = 'loading' | 'ready' | 'empty' | 'error'
type Filter = 'all' | 'completed' | 'failed'

const formatDateTime = (value: string) => {
  return new Date(value).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

const getResultScore = (result: HistoryResult) => {
  if (result.result_type === 'failed') return '—'
  if (result.result_type === 'multi_question') {
    return `${Math.round(result.average_score_ratio * 100)}% avg`
  }
  return `${Math.round(result.score_ratio * 100)}%`
}

const getResultSummary = (result: HistoryResult) => {
  if (result.result_type === 'failed') return result.error_message
  if (result.result_type === 'multi_question') {
    return `${result.total_score}/${result.max_total_score} across ${result.total_questions} questions`
  }
  return `${result.marks}/${result.max_marks} - ${result.grade}`
}

const isFailed = (result: HistoryResult) => result.result_type === 'failed'

export const ResultsHistory = ({ refreshToken }: Props) => {
  const [data, setData] = useState<ResultsResponse | null>(null)
  const [status, setStatus] = useState<Status>('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [isOutage, setIsOutage] = useState(false)
  const [filter, setFilter] = useState<Filter>('all')

  const loadHistory = useCallback(async () => {
    setStatus('loading')
    setErrorMessage('')
    setIsOutage(false)

    try {
      const nextData = await assessmentApi.getResults()
      setData(nextData)
      setStatus(!nextData || nextData.count === 0 ? 'empty' : 'ready')
    } catch (error) {
      setData(null)
      setIsOutage(isApiOutageError(error))
      setErrorMessage(getUserFacingErrorMessage(error))
      setStatus('error')
    }
  }, [])

  const refresh = useCallback(() => {
    void loadHistory()
  }, [loadHistory])

  useEffect(() => {
    queueMicrotask(() => {
      void loadHistory()
    })
  }, [loadHistory, refreshToken])

  if (status === 'loading') {
    return (
      <div className="surface-1 p-6 text-center">
        <p className="text-sm subtle-pulse" style={{ color: 'var(--color-text-tertiary)' }}>Loading history...</p>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="surface-1 p-6 text-center space-y-3">
        <div className="flex items-center justify-center gap-2">
          <AlertTriangle size={16} style={{ color: 'var(--color-warning)' }} />
          <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
            {isOutage ? 'Assessment API offline' : 'History is temporarily unavailable'}
          </p>
        </div>
        <p className="text-xs max-w-md mx-auto" style={{ color: 'var(--color-text-disabled)' }}>
          {errorMessage}
        </p>
        <button
          onClick={refresh}
          className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md hover-accent-subtle"
          style={{ color: 'var(--color-accent)' }}
        >
          <RefreshCw size={12} />
          Retry
        </button>
      </div>
    )
  }

  if (status === 'empty' || !data) {
    return (
      <div className="surface-1 p-6 text-center space-y-2">
        <div className="flex items-center justify-center gap-2">
          <Clock3 size={16} style={{ color: 'var(--color-text-disabled)' }} />
          <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
            No assessments yet
          </p>
        </div>
        <p className="text-xs" style={{ color: 'var(--color-text-disabled)' }}>
          Your completed grading runs will appear here.
        </p>
      </div>
    )
  }

  const filtered = data.results.filter((r) => {
    if (filter === 'completed') return !isFailed(r)
    if (filter === 'failed') return isFailed(r)
    return true
  })

  const failedCount = data.results.filter(isFailed).length

  return (
    <div className="surface-1 overflow-hidden">
      <div className="p-5 flex items-center justify-between" style={{ borderBottom: '1px solid var(--color-border)' }}>
        <div className="flex items-center gap-2">
          <Users size={16} style={{ color: 'var(--color-accent)' }} />
          <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>My Recent Results</h3>
          <span className="text-xs px-2 py-0.5 rounded-md" style={{
            background: 'var(--color-surface-3)', color: 'var(--color-text-tertiary)',
          }}>
            {data.count}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {failedCount > 0 && (
            <div className="flex gap-1">
              {(['all', 'completed', 'failed'] as const).map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setFilter(f)}
                  className="text-xs px-2.5 py-1 rounded-md capitalize transition-colors"
                  style={{
                    background: filter === f ? 'var(--color-accent-subtle)' : 'transparent',
                    color: filter === f ? 'var(--color-accent)' : 'var(--color-text-disabled)',
                    border: filter === f ? '1px solid var(--color-accent-border)' : '1px solid transparent',
                  }}
                >
                  {f}
                </button>
              ))}
            </div>
          )}
          <button
            onClick={refresh}
            className="text-xs px-3 py-1.5 rounded-md hover-accent-subtle"
            style={{ color: 'var(--color-accent)' }}
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr style={{ background: 'var(--color-surface-2)' }}>
              {['Student', 'Type', 'Scope', 'Score', 'Result', 'Time'].map((heading) => (
                <th
                  key={heading}
                  className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider"
                  style={{ color: 'var(--color-text-disabled)' }}
                >
                  {heading}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((result) => (
              <tr
                key={result.id}
                className="hover-surface-2"
                style={{ borderBottom: '1px solid var(--color-border)' }}
              >
                <td className="px-4 py-3 font-medium" style={{ color: isFailed(result) ? 'var(--color-text-tertiary)' : 'var(--color-text-primary)' }}>
                  {result.student_id}
                </td>
                <td className="px-4 py-3" style={{ color: 'var(--color-text-tertiary)' }}>
                  {isFailed(result) ? (
                    <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-md" style={{ background: 'var(--color-error-subtle)', color: 'var(--color-error)' }}>
                      <XCircle size={10} />
                      Failed
                    </span>
                  ) : result.result_type === 'multi_question' ? 'Multi-question' : 'Single question'}
                </td>
                <td className="px-4 py-3" style={{ color: 'var(--color-text-tertiary)' }}>
                  {result.result_type === 'multi_question'
                    ? `${result.total_questions} questions`
                    : result.result_type === 'single_question'
                    ? result.question_id
                    : '—'}
                </td>
                <td className="px-4 py-3 font-medium" style={{ fontFamily: 'var(--font-mono)', color: isFailed(result) ? 'var(--color-text-disabled)' : 'var(--color-text-primary)' }}>
                  {getResultScore(result)}
                </td>
                <td className="px-4 py-3" style={{ color: isFailed(result) ? 'var(--color-error)' : 'var(--color-text-tertiary)', fontStyle: isFailed(result) ? 'italic' : 'normal' }}>
                  {isFailed(result) ? `Failed: ${getResultSummary(result)}` : getResultSummary(result)}
                </td>
                <td className="px-4 py-3 text-xs" style={{ color: 'var(--color-text-disabled)' }}>
                  {formatDateTime(result.assessed_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
