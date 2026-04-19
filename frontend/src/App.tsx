import { useState, useCallback } from 'react'
import { BookOpen, AlertTriangle } from 'lucide-react'
import type { AnyAssessmentResult } from './types/assessment'
import { HealthBadge } from './components/HealthBadge'
import { AssessmentForm } from './components/AssessmentForm'
import { ResultsDisplay } from './components/ResultsDisplay'
import { ResultsHistory } from './components/ResultsHistory'
import { ProgressTracker } from './components/ProgressTracker'

const App = () => {
  const [result, setResult] = useState<AnyAssessmentResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const [historyRefreshToken, setHistoryRefreshToken] = useState(0)

  const handleResult = useCallback((next: AnyAssessmentResult) => {
    setResult(next)
    setError(null)
    setActiveTaskId(null)
    setHistoryRefreshToken((t) => t + 1)
  }, [])

  const handleTaskStarted = useCallback((taskId: string) => {
    setActiveTaskId(taskId)
    setResult(null)
    setError(null)
  }, [])

  const handleError = useCallback((msg: string) => {
    setError(msg)
    setResult(null)
    setActiveTaskId(null)
  }, [])

  const errorTitle = error?.toLowerCase().includes('assessment api')
    ? 'Assessment API unavailable'
    : 'Assessment failed'

  return (
    <div className="min-h-screen">
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
        <HealthBadge />
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
