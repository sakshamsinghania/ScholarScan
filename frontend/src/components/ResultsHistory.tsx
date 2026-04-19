import { useEffect, useState, useCallback } from 'react'
import { Users, AlertTriangle, RefreshCw, Clock3 } from 'lucide-react'
import type { HistoryResult, ResultsResponse } from '../types/assessment'
import { assessmentApi, getUserFacingErrorMessage, isApiOutageError } from '../api/assessment-api'

interface Props {
  refreshToken: number
}

type Status = 'loading' | 'ready' | 'empty' | 'error'

const formatDateTime = (value: string) => {
  return new Date(value).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

const getResultScore = (result: HistoryResult) => {
  if (result.result_type === 'multi_question') {
    return `${Math.round(result.average_score_ratio * 100)}% avg`
  }

  return `${Math.round(result.score_ratio * 100)}%`
}

const getResultSummary = (result: HistoryResult) => {
  if (result.result_type === 'multi_question') {
    return `${result.total_score}/${result.max_total_score} across ${result.total_questions} questions`
  }

  return `${result.marks}/${result.max_marks} - ${result.grade}`
}

export const ResultsHistory = ({ refreshToken }: Props) => {
  const [data, setData] = useState<ResultsResponse | null>(null)
  const [status, setStatus] = useState<Status>('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [isOutage, setIsOutage] = useState(false)

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
          Completed grading runs will appear here with single-question and multi-question summaries.
        </p>
      </div>
    )
  }

  return (
    <div className="surface-1 overflow-hidden">
      <div className="p-5 flex items-center justify-between" style={{ borderBottom: '1px solid var(--color-border)' }}>
        <div className="flex items-center gap-2">
          <Users size={16} style={{ color: 'var(--color-accent)' }} />
          <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>History</h3>
          <span className="text-xs px-2 py-0.5 rounded-md" style={{
            background: 'var(--color-surface-3)', color: 'var(--color-text-tertiary)',
          }}>
            {data.count}
          </span>
        </div>
        <button
          onClick={refresh}
          className="text-xs px-3 py-1.5 rounded-md hover-accent-subtle"
          style={{ color: 'var(--color-accent)' }}
        >
          Refresh
        </button>
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
            {data.results.map((result) => (
              <tr
                key={result.id}
                className="hover-surface-2"
                style={{ borderBottom: '1px solid var(--color-border)' }}
              >
                <td className="px-4 py-3 font-medium" style={{ color: 'var(--color-text-primary)' }}>
                  {result.student_id}
                </td>
                <td className="px-4 py-3" style={{ color: 'var(--color-text-tertiary)' }}>
                  {result.result_type === 'multi_question' ? 'Multi-question' : 'Single question'}
                </td>
                <td className="px-4 py-3" style={{ color: 'var(--color-text-tertiary)' }}>
                  {result.result_type === 'multi_question'
                    ? `${result.total_questions} questions`
                    : result.question_id}
                </td>
                <td className="px-4 py-3 font-medium" style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-primary)' }}>
                  {getResultScore(result)}
                </td>
                <td className="px-4 py-3" style={{ color: 'var(--color-text-tertiary)' }}>
                  {getResultSummary(result)}
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
