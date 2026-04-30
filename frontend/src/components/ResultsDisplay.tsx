import { FileText, Award, MessageSquare, TrendingUp, AlertCircle, ChevronDown, ChevronUp, BookOpen } from 'lucide-react'
import { useState } from 'react'
import type { AnyAssessmentResult, AssessmentResponse, MultiAssessmentResponse, QuestionResult } from '../types/assessment'
import { isMultiAssessment } from '../types/assessment'

interface Props {
  result: AnyAssessmentResult
}

/* ── Score Ring ── */
const ScoreRing = ({ score, label, size = 100 }: { score: number; label: string; size?: number }) => {
  const strokeWidth = 6
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - score * circumference
  const percentage = Math.round(score * 100)

  const getColor = (s: number) => {
    if (s >= 0.8) return 'var(--color-grade-a)'
    if (s >= 0.65) return 'var(--color-grade-b)'
    if (s >= 0.5) return 'var(--color-grade-c)'
    if (s >= 0.35) return 'var(--color-grade-d)'
    return 'var(--color-grade-f)'
  }

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative" style={{ width: size, height: size }}>
        <svg className="score-ring" width={size} height={size}>
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--color-border)" strokeWidth={strokeWidth} />
          <circle className="score-ring__circle" cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={getColor(score)} strokeWidth={strokeWidth} strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset} />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="font-semibold" style={{ color: getColor(score), fontSize: size > 80 ? '1.1rem' : '0.85rem', fontFamily: 'var(--font-mono)' }}>
            {percentage}%
          </span>
        </div>
      </div>
      <span className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>{label}</span>
    </div>
  )
}

const GradeBadge = ({ grade, size = 'lg' }: { grade: string; size?: 'sm' | 'lg' }) => {
  const cls = `grade-${grade.toLowerCase()}`
  const px = size === 'lg' ? 'px-4 py-2 text-2xl' : 'px-2 py-0.5 text-xs'
  return <span className={`${cls} ${px} rounded-lg font-bold inline-block`}>{grade}</span>
}

const StatusBadge = ({ label }: { label: string }) => (
  <span
    className="px-2 py-0.5 text-xs rounded-lg font-bold inline-block"
    style={{
      background: 'var(--color-error-subtle)',
      color: 'var(--color-error)',
      border: '1px solid rgba(217,83,79,0.2)',
    }}
  >
    {label}
  </span>
)

/* ── Question Card (multi-question) ── */
const QuestionCard = ({ q, index }: { q: QuestionResult; index: number }) => {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="surface-2 overflow-hidden animate-fade-in" style={{ animationDelay: `${index * 0.06}s` }}>
      {/* Header row */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-center justify-between cursor-pointer hover-surface-3"
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-3">
          {q.status === 'failed' ? <StatusBadge label="Failed" /> : <GradeBadge grade={q.grade} size="sm" />}
          <div className="text-left">
            <p className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
              {q.question_id}
            </p>
            {q.question && (
              <p className="text-xs truncate max-w-[200px]" style={{ color: 'var(--color-text-tertiary)' }}>
                {q.question}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-base font-semibold" style={{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
              {q.marks}<span className="text-xs font-normal" style={{ color: 'var(--color-text-tertiary)' }}>/{q.max_marks}</span>
            </p>
            <p className="text-xs" style={{ color: 'var(--color-text-tertiary)', fontFamily: 'var(--font-mono)' }}>
              {q.status === 'failed' ? 'Not graded' : `${Math.round(q.similarity_score * 100)}% match`}
            </p>
          </div>
          {expanded ? <ChevronUp size={14} style={{ color: 'var(--color-text-disabled)' }} /> : <ChevronDown size={14} style={{ color: 'var(--color-text-disabled)' }} />}
        </div>
      </button>

      {/* Expanded */}
      {expanded && (
        <div className="px-4 pb-4 space-y-4" style={{ borderTop: '1px solid var(--color-border)' }}>
          {q.status === 'failed' ? (
            <div
              className="mt-4 p-3 rounded-lg"
              style={{ background: 'var(--color-error-subtle)', border: '1px solid rgba(217,83,79,0.2)' }}
            >
              <p className="text-xs font-medium mb-1" style={{ color: 'var(--color-error)' }}>
                Automatic grading failed
              </p>
              <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
                {q.failure_reason || q.feedback}
              </p>
            </div>
          ) : (
            <div className="flex flex-wrap justify-start gap-5 pt-4">
              <ScoreRing score={q.similarity_score} label="Overall" size={72} />
              <ScoreRing score={q.sbert_score ?? 0} label="SBERT" size={56} />
              <ScoreRing score={q.sentence_similarity ?? 0} label="Sentence" size={56} />
              <ScoreRing score={q.concept_coverage ?? 0} label="Concept" size={56} />
              <ScoreRing score={q.tfidf_score ?? 0} label="TF-IDF" size={56} />
              <ScoreRing score={q.entailment_score ?? 0} label="NLI" size={56} />
            </div>
          )}

          {/* Feedback */}
          <div className="surface-3 p-3 rounded-lg">
            <p className="text-xs font-medium mb-1" style={{ color: 'var(--color-text-tertiary)' }}>Feedback</p>
            <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>{q.feedback}</p>
          </div>

          {/* Student Answer */}
          {q.student_answer && (
            <div className="surface-3 p-3 rounded-lg">
              <p className="text-xs font-medium mb-1" style={{ color: 'var(--color-text-tertiary)' }}>Student Answer</p>
              <p className="text-xs leading-relaxed" style={{ color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>
                {q.student_answer}
              </p>
            </div>
          )}

          {/* Model Answer */}
          {q.model_answer && (
            <div className="p-3 rounded-lg" style={{ background: 'var(--color-accent-subtle)', border: '1px solid var(--color-accent-border)' }}>
              <p className="text-xs font-medium mb-1" style={{ color: 'var(--color-accent)' }}>Model Answer (AI)</p>
              <p className="text-xs leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
                {q.model_answer}
              </p>
            </div>
          )}

          {/* Missing Keywords */}
          {q.missing_keywords.length > 0 && (
            <div>
              <p className="text-xs font-medium mb-1.5" style={{ color: 'var(--color-text-tertiary)' }}>
                Missing Keywords ({Math.round(q.keyword_overlap * 100)}% covered)
              </p>
              <div className="flex flex-wrap gap-1.5">
                {q.missing_keywords.slice(0, 5).map((kw) => (
                  <span key={kw} className="keyword-chip">{kw}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ── Single Result (legacy) ── */
const SingleResultDisplay = ({ result }: { result: AssessmentResponse }) => (
  <div className="space-y-5 animate-fade-in">
    <div className="surface-1 p-6">
      <div className="flex items-center gap-2 mb-5">
        <TrendingUp size={16} style={{ color: 'var(--color-accent)' }} />
        <h3 className="text-base font-semibold">Score Overview</h3>
      </div>
      <div className="flex items-center justify-between">
        <div className="flex gap-5">
          <ScoreRing score={result.similarity_score} label="Overall" size={100} />
          <ScoreRing score={result.sbert_score ?? 0} label="SBERT" size={72} />
          <ScoreRing score={result.sentence_similarity ?? 0} label="Sentence" size={72} />
          <ScoreRing score={result.concept_coverage ?? 0} label="Concept" size={72} />
          <ScoreRing score={result.tfidf_score ?? 0} label="TF-IDF" size={72} />
          <ScoreRing score={result.entailment_score ?? 0} label="NLI" size={72} />
        </div>
        <div className="text-right space-y-2">
          <GradeBadge grade={result.grade} />
          <div className="text-3xl font-bold" style={{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
            {result.marks}
            <span className="text-base font-normal" style={{ color: 'var(--color-text-tertiary)' }}>/{result.max_marks}</span>
          </div>
        </div>
      </div>
    </div>

    <div className="surface-1 p-6">
      <div className="flex items-center gap-2 mb-3">
        <MessageSquare size={16} style={{ color: 'var(--color-accent)' }} />
        <h3 className="text-base font-semibold">Feedback</h3>
      </div>
      <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>{result.feedback}</p>
    </div>

    {result.missing_keywords.length > 0 && (
      <div className="surface-1 p-6">
        <div className="flex items-center gap-2 mb-3">
          <AlertCircle size={16} style={{ color: 'var(--color-warning)' }} />
          <h3 className="text-base font-semibold">Missing Keywords</h3>
        </div>
        <div className="flex flex-wrap gap-2">
          {result.missing_keywords.map((kw) => (
            <span key={kw} className="keyword-chip">{kw}</span>
          ))}
        </div>
      </div>
    )}

    <div className="surface-1 p-6">
      <div className="flex items-center gap-2 mb-3">
        <FileText size={16} style={{ color: 'var(--color-accent)' }} />
        <h3 className="text-base font-semibold">Extracted Text</h3>
      </div>
      <div
        className="p-4 rounded-lg max-h-48 overflow-y-auto text-sm leading-relaxed"
        style={{ background: 'var(--color-surface-0)', fontFamily: 'var(--font-mono)', color: 'var(--color-text-secondary)' }}
      >
        {result.extracted_text}
      </div>
    </div>
  </div>
)

/* ── Multi-Question Display ── */
const MultiResultDisplay = ({ result }: { result: MultiAssessmentResponse }) => {
  const scorePercent = result.max_total_score > 0
    ? result.total_score / result.max_total_score
    : 0

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Summary */}
      <div className="surface-1 p-6">
        <div className="flex items-center gap-2 mb-5">
          <Award size={16} style={{ color: 'var(--color-accent)' }} />
          <h3 className="text-base font-semibold">Assessment Summary</h3>
          <span className="text-xs px-2 py-0.5 rounded-md ml-auto" style={{
            background: 'var(--color-surface-3)', color: 'var(--color-text-tertiary)',
          }}>
            {result.total_questions} question{result.total_questions !== 1 ? 's' : ''}
          </span>
        </div>

        {result.status === 'partial_failure' && (
          <div
            className="mb-4 p-3 rounded-lg"
            style={{ background: 'var(--color-error-subtle)', border: '1px solid rgba(217,83,79,0.2)' }}
          >
            <p className="text-sm font-medium" style={{ color: 'var(--color-error)' }}>
              {result.failed_questions} question{result.failed_questions !== 1 ? 's were' : ' was'} not graded automatically
            </p>
            <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
              Review the affected questions below instead of treating them as academic scores.
            </p>
          </div>
        )}

        <div className="flex items-center justify-between">
          <ScoreRing score={scorePercent} label="Overall" size={110} />
          <div className="text-right space-y-1">
            <div className="text-3xl font-bold" style={{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
              {result.total_score}
              <span className="text-base font-normal" style={{ color: 'var(--color-text-tertiary)' }}>
                /{result.max_total_score}
              </span>
            </div>
            <p className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>total marks</p>
            <p className="text-xs" style={{ color: 'var(--color-text-disabled)' }}>
              {result.student_id}
            </p>
          </div>
        </div>

        {/* Mini bars */}
        <div className="mt-5 space-y-2">
          {result.results.map((q) => (
            <div key={q.question_id} className="flex items-center gap-3">
              <span className="text-xs w-8 font-medium" style={{ color: 'var(--color-text-tertiary)', fontFamily: 'var(--font-mono)' }}>{q.question_id}</span>
              <div className="flex-1 h-1.5 rounded-full" style={{ background: 'var(--color-border)' }}>
                <div
                  className="h-1.5 rounded-full transition-all duration-700"
                  style={{
                    width: `${q.max_marks > 0 ? (q.marks / q.max_marks) * 100 : 0}%`,
                    background: q.status === 'failed' ? 'var(--color-error)' : 'var(--color-accent)',
                  }}
                />
              </div>
              <span className="text-xs w-12 text-right" style={{ color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>
                {q.marks}/{q.max_marks}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Per-Question Cards */}
      <div className="flex items-center gap-2 px-1">
        <BookOpen size={14} style={{ color: 'var(--color-accent)' }} />
        <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text-secondary)' }}>
          Per-Question Results
        </h3>
      </div>

      <div className="space-y-2">
        {result.results.map((q, i) => (
          <QuestionCard key={q.question_id} q={q} index={i} />
        ))}
      </div>
    </div>
  )
}

/* ── Export ── */
export const ResultsDisplay = ({ result }: Props) => {
  if (isMultiAssessment(result)) {
    return <MultiResultDisplay result={result} />
  }
  return <SingleResultDisplay result={result} />
}
