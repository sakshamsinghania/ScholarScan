import { useState, useCallback, useEffect } from 'react'
import { BookOpen, AlertTriangle, LogOut, Shield } from 'lucide-react'
import type { AnyAssessmentResult } from './types/assessment'
import { assessmentApi } from './api/assessment-api'
import { useAuth } from './auth/useAuth'
import { AuthCard } from './components/auth/AuthCard'
import { HealthBadge } from './components/HealthBadge'
import { AssessmentForm } from './components/AssessmentForm'
import { ResultsDisplay } from './components/ResultsDisplay'
import { ResultsHistory } from './components/ResultsHistory'
import { ProgressTracker } from './components/ProgressTracker'
import { ToastHost } from './components/ToastHost'

const ACTIVE_TASK_KEY = 'scholarscan.activeTask'

const App = () => {
  const { user, status, logout } = useAuth()
  const [result, setResult] = useState<AnyAssessmentResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const [historyRefreshToken, setHistoryRefreshToken] = useState(0)

  const handleResult = useCallback((next: AnyAssessmentResult) => {
    setResult(next)
    setError(null)
    setActiveTaskId(null)
    localStorage.removeItem(ACTIVE_TASK_KEY)
    setHistoryRefreshToken((t) => t + 1)
  }, [])

  const handleTaskStarted = useCallback((taskId: string) => {
    setActiveTaskId(taskId)
    localStorage.setItem(ACTIVE_TASK_KEY, taskId)
    setResult(null)
    setError(null)
  }, [])

  const handleError = useCallback((msg: string) => {
    setError(msg)
    setResult(null)
    setActiveTaskId(null)
    localStorage.removeItem(ACTIVE_TASK_KEY)
  }, [])

  // Restore active task on mount
  useEffect(() => {
    if (status !== 'authed') return
    const savedTaskId = localStorage.getItem(ACTIVE_TASK_KEY)
    if (!savedTaskId) return

    assessmentApi.getTaskResult(savedTaskId)
      .then((res: Response) => {
        if (res.status === 202) {
          setActiveTaskId(savedTaskId)
        } else if (res.status === 200) {
          res.json().then((data: AnyAssessmentResult) => {
            setResult(data)
            localStorage.removeItem(ACTIVE_TASK_KEY)
          })
        } else {
          localStorage.removeItem(ACTIVE_TASK_KEY)
        }
      })
      .catch(() => {
        localStorage.removeItem(ACTIVE_TASK_KEY)
      })
  }, [status])

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--color-surface-0)' }}>
        <div className="text-center animate-fade-in">
          <BookOpen size={28} className="mx-auto mb-3 subtle-pulse" style={{ color: 'var(--color-accent)' }} />
          <p className="text-sm" style={{ color: 'var(--color-text-tertiary)' }}>Loading…</p>
        </div>
      </div>
    )
  }

  if (status === 'anon') {
    return <AuthCard />
  }

  const errorTitle = error?.toLowerCase().includes('assessment api')
    ? 'Assessment API unavailable'
    : 'Assessment failed'

  return (
    <div className="min-h-screen">
      <ToastHost />

      {/* ── Header ── */}
      <header className="sticky top-0 z-20 px-6 py-4 flex items-center justify-between" style={{ background: 'var(--color-surface-0)', borderBottom: '1px solid var(--color-border)' }}>
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg" style={{ background: 'var(--color-accent-subtle)', border: '1px solid var(--color-accent-border)' }}>
            <BookOpen size={20} style={{ color: 'var(--color-accent)' }} />
          </div>
          <div>
            <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.35rem', color: 'var(--color-text-primary)', lineHeight: 1.2 }}>
              ScholarScan
            </h1>
            <p className="text-xs" style={{ color: 'var(--color-text-tertiary)', letterSpacing: '0.02em' }}>
              AI-Powered Assessment
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <HealthBadge />
          {user && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-md" style={{ background: 'var(--color-surface-2)', border: '1px solid var(--color-border)' }}>
              <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>{user.email}</span>
              {user.role === 'admin' && (
                <span className="flex items-center gap-1 text-xs px-1.5 py-0.5 rounded" style={{ background: 'var(--color-accent-subtle)', color: 'var(--color-accent)' }}>
                  <Shield size={10} />
                  admin
                </span>
              )}
              <button
                type="button"
                onClick={logout}
                className="p-1 rounded hover-surface-3"
                style={{ color: 'var(--color-text-tertiary)' }}
                title="Sign out"
              >
                <LogOut size={14} />
              </button>
            </div>
          )}
        </div>
      </header>

      {/* ── Main layout ── */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

          {/* ── Sidebar: Form ── */}
          <aside className="lg:col-span-4">
            <div className="surface-1 p-6 lg:sticky lg:top-24">
              <h2 className="text-sm font-semibold mb-5" style={{ color: 'var(--color-text-tertiary)', letterSpacing: '0.02em' }}>
                Upload for grading
              </h2>
              <AssessmentForm
                onResult={handleResult}
                onTaskStarted={handleTaskStarted}
                onError={handleError}
              />
            </div>
          </aside>

          {/* ── Main content ── */}
          <section className="lg:col-span-8 space-y-6" aria-label="Assessment results">

            {/* Error */}
            {error && (
              <div
                className="surface-2 p-4 flex items-start gap-3 animate-fade-in"
                role="alert"
              >
                  <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" style={{ color: 'var(--color-error)' }} />
                <div>
                  <p className="text-sm font-medium" style={{ color: 'var(--color-error)' }}>{errorTitle}</p>
                  <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>{error}</p>
                </div>
              </div>
            )}

            {/* Progress Tracker */}
            {activeTaskId && (
              <ProgressTracker
                taskId={activeTaskId}
                onComplete={handleResult}
                onError={handleError}
              />
            )}

            {/* Results */}
            {result && <ResultsDisplay result={result} />}

            {/* Empty state */}
            {!result && !error && !activeTaskId && (
              <div className="py-16 text-center animate-fade-in">
                <BookOpen size={28} className="mx-auto mb-3" style={{ color: 'var(--color-text-disabled)', opacity: 0.7 }} />
                <p className="text-sm" style={{ color: 'var(--color-text-tertiary)' }}>
                  Upload a student's answer to get started
                </p>
              </div>
            )}

            {/* History — always mounted, manages its own empty/loading/error states */}
            <ResultsHistory refreshToken={historyRefreshToken} />
          </section>
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="text-center text-xs py-8" style={{ color: 'var(--color-text-disabled)' }}>
        ScholarScan · Intelligent Grading
      </footer>
    </div>
  )
}

export default App
