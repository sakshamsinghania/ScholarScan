import { useState, useRef, useCallback, useEffect } from 'react'
import { Upload, FileImage, FileText, X, Send, Loader2, Sparkles, ChevronDown } from 'lucide-react'
import type { AnyAssessmentResult } from '../types/assessment'
import { assessmentApi, getUserFacingErrorMessage, isTaskStart, validateFile } from '../api/assessment-api'

interface Props {
  onResult: (result: AnyAssessmentResult) => void
  onTaskStarted: (taskId: string) => void
  onError: (error: string) => void
}

export const AssessmentForm = ({ onResult, onTaskStarted, onError }: Props) => {
  const [answerFile, setAnswerFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [questionFile, setQuestionFile] = useState<File | null>(null)
  const [modelAnswer, setModelAnswer] = useState('')
  const [studentId, setStudentId] = useState('')
  const [maxMarks, setMaxMarks] = useState('10')
  const [loading, setLoading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [useAutoModel, setUseAutoModel] = useState(false)
  const [showOptions, setShowOptions] = useState(false)
  const answerFileRef = useRef<HTMLInputElement>(null)
  const questionFileRef = useRef<HTMLInputElement>(null)

  const isPdf = answerFile?.name.toLowerCase().endsWith('.pdf')

  // Force auto mode when PDF is selected — manual mode only works with images
  useEffect(() => {
    if (isPdf && !useAutoModel) {
      setUseAutoModel(true)
    }
  }, [isPdf, useAutoModel])

  useEffect(() => {
    if (useAutoModel || !questionFile) return
    setQuestionFile(null)
    if (questionFileRef.current) questionFileRef.current.value = ''
  }, [questionFile, useAutoModel])

  const handleFile = useCallback((file: File) => {
    const error = validateFile(file)
    if (error) {
      onError(error)
      return
    }
    setAnswerFile(file)

    if (file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file)
      setPreview(url)
    } else {
      setPreview(null)
    }
  }, [onError])

  // Revoke object URL on cleanup
  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview)
    }
  }, [preview])

  const handleQuestionFile = useCallback((file: File) => {
    if (!useAutoModel) {
      onError('Question papers are only available in auto mode.')
      return
    }
    const error = validateFile(file)
    if (error) {
      onError(error)
      return
    }
    setQuestionFile(file)
  }, [onError, useAutoModel])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }, [handleFile])

  const clearAnswerFile = () => {
    if (preview) URL.revokeObjectURL(preview)
    setAnswerFile(null)
    setPreview(null)
    if (answerFileRef.current) answerFileRef.current.value = ''
  }

  const clearQuestionFile = () => {
    setQuestionFile(null)
    if (questionFileRef.current) questionFileRef.current.value = ''
  }

  const canSubmit = answerFile && (!useAutoModel ? modelAnswer.trim() : true) && !loading

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!answerFile) return

    setLoading(true)
    try {
      if (!useAutoModel && modelAnswer.trim()) {
        // Manual mode — images only (PDF guard above ensures this)
        const result = await assessmentApi.submitManualAssessment(
          answerFile,
          modelAnswer,
          {
            studentId: studentId || undefined,
            maxMarks: parseInt(maxMarks) || undefined,
          }
        )
        onResult(result)
      } else {
        // Auto/document mode
        const response = await assessmentApi.submitDocumentAssessment(
          answerFile,
          {
            questionFile: questionFile || undefined,
            studentId: studentId || undefined,
            maxMarks: parseInt(maxMarks) || undefined,
          }
        )
        if (isTaskStart(response)) {
          onTaskStarted(response.task_id)
        } else {
          onResult(response as AnyAssessmentResult)
        }
      }
    } catch (err) {
      onError(getUserFacingErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* ── Answer File ── */}
      <div>
        <label htmlFor="answer-file-input" className="block text-xs font-medium mb-2" style={{ color: 'var(--color-text-tertiary)', letterSpacing: '0.02em' }}>
          Student answer
        </label>
        {answerFile ? (
          <div className="surface-2 p-3 relative">
            <button
              type="button"
              onClick={clearAnswerFile}
              aria-label="Remove uploaded file"
              className="absolute top-2 right-2 p-2 rounded-md hover-surface-3"
              style={{ color: 'var(--color-text-tertiary)' }}
            >
              <X size={14} />
            </button>
            {preview ? (
              <img
                src={preview}
                alt="Uploaded student answer"
                className="w-full max-h-44 object-contain rounded-md"
              />
            ) : (
              <div className="flex items-center gap-3 py-2">
                <FileText size={24} style={{ color: 'var(--color-accent)' }} />
                <div>
                  <p className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
                    {answerFile.name}
                  </p>
                  <p className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
                    PDF · {(answerFile.size / 1024).toFixed(0)} KB
                  </p>
                </div>
              </div>
            )}
            {!isPdf && (
              <p className="mt-2 text-xs truncate" style={{ color: 'var(--color-text-tertiary)' }}>
                <FileImage size={12} className="inline mr-1" />
                {answerFile.name} ({(answerFile.size / 1024).toFixed(0)} KB)
              </p>
            )}
          </div>
        ) : (
          <button
            type="button"
            className={`drop-zone w-full p-6 flex flex-col items-center gap-2 ${dragOver ? 'dragover' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => answerFileRef.current?.click()}
            aria-label="Upload student answer file"
          >
            <Upload size={22} style={{ color: 'var(--color-text-disabled)' }} />
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              Drop file or <span style={{ color: 'var(--color-accent)' }}>browse</span>
            </p>
            <p className="text-xs" style={{ color: 'var(--color-text-disabled)' }}>
              JPG, PNG, or PDF (max 16 MB)
            </p>
          </button>
        )}
        <input
          ref={answerFileRef}
          id="answer-file-input"
          type="file"
          accept=".jpg,.jpeg,.png,.pdf"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />
      </div>

      {/* ── Question Paper (optional) ── */}
      <div>
        <label htmlFor="question-file-input" className="block text-xs font-medium mb-2" style={{ color: 'var(--color-text-tertiary)', letterSpacing: '0.02em' }}>
          Question paper <span className="font-normal" style={{ color: 'var(--color-text-disabled)' }}>(optional)</span>
        </label>
        {questionFile ? (
          <div className="surface-2 p-3 flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0">
              <FileText size={16} style={{ color: 'var(--color-accent)' }} />
              <span className="text-sm truncate" style={{ color: 'var(--color-text-primary)' }}>
                {questionFile.name}
              </span>
            </div>
            <button
              type="button"
              onClick={clearQuestionFile}
              aria-label="Remove question paper"
              className="p-2 rounded-md flex-shrink-0 hover-surface-3"
              style={{ color: 'var(--color-text-tertiary)' }}
            >
              <X size={14} />
            </button>
          </div>
        ) : (
          <button
            type="button"
            disabled={!useAutoModel}
            onClick={() => questionFileRef.current?.click()}
            className="w-full py-2.5 px-4 rounded-lg text-sm text-left hover-accent-subtle"
            style={{
              border: '1px dashed var(--color-border-hover)',
              color: !useAutoModel ? 'var(--color-text-disabled)' : 'var(--color-text-tertiary)',
              opacity: !useAutoModel ? 0.7 : 1,
              cursor: !useAutoModel ? 'not-allowed' : 'pointer',
            }}
          >
            {useAutoModel ? '+ Add question paper' : 'Question paper disabled in manual mode'}
          </button>
        )}
        <input
          ref={questionFileRef}
          id="question-file-input"
          type="file"
          accept=".jpg,.jpeg,.png,.pdf"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleQuestionFile(e.target.files[0])}
        />
      </div>

      {/* ── Model Answer ── */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs font-medium" style={{ color: 'var(--color-text-tertiary)', letterSpacing: '0.02em' }}>
            Model answer
          </label>
          <button
            type="button"
            onClick={() => !isPdf && setUseAutoModel(!useAutoModel)}
            disabled={!!isPdf}
            className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-md transition-colors"
            style={{
              background: useAutoModel ? 'var(--color-accent-subtle)' : 'var(--color-surface-3)',
              color: useAutoModel ? 'var(--color-accent)' : 'var(--color-text-tertiary)',
              border: `1px solid ${useAutoModel ? 'var(--color-accent-border)' : 'var(--color-border)'}`,
              opacity: isPdf ? 0.5 : 1,
              cursor: isPdf ? 'not-allowed' : 'pointer',
            }}
            title={isPdf ? 'PDF uploads require AI-generated model answers' : undefined}
            aria-pressed={useAutoModel}
          >
            <Sparkles size={11} />
            {useAutoModel ? 'Generate model answer' : 'Manual'}
          </button>
        </div>

        {!useAutoModel && (
          <>
            <textarea
              value={modelAnswer}
              onChange={(e) => setModelAnswer(e.target.value)}
              placeholder="Enter the teacher-provided reference answer..."
              rows={4}
              aria-label="Model answer text"
              className="input-base resize-none"
            />
            <p className="mt-2 text-xs" style={{ color: 'var(--color-text-disabled)' }}>
              Manual mode is the safer default. It scores against a teacher-provided reference answer and does not use a question paper.
            </p>
          </>
        )}

        {useAutoModel && (
          <p className="text-xs" style={{ color: 'var(--color-text-disabled)' }}>
            Auto mode requires detected question text or a separate question paper, plus AI reference-answer generation.
          </p>
        )}
      </div>

      {/* ── Options toggle (progressive disclosure) ── */}
      <button
        type="button"
        onClick={() => setShowOptions(!showOptions)}
        className="flex items-center gap-1.5 text-xs py-1 transition-colors"
        style={{ color: 'var(--color-text-tertiary)' }}
      >
        <ChevronDown
          size={14}
          style={{
            transition: 'transform 0.2s ease',
            transform: showOptions ? 'rotate(180deg)' : 'rotate(0deg)',
          }}
        />
        Assessment options
      </button>

      {showOptions && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 animate-fade-in">
          <div>
            <label htmlFor="student-id-input" className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-text-tertiary)' }}>
              Student ID
            </label>
            <input
              id="student-id-input"
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              placeholder="e.g. student_01"
              className="input-base"
            />
          </div>
          <div>
            <label htmlFor="max-marks-input" className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-text-tertiary)' }}>
              Max marks
            </label>
            <input
              id="max-marks-input"
              value={maxMarks}
              onChange={(e) => setMaxMarks(e.target.value)}
              type="number"
              min="1"
              max="100"
              className="input-base"
            />
          </div>
        </div>
      )}

      {/* ── Submit ── */}
      <button
        type="submit"
        disabled={!canSubmit}
        className="btn-primary w-full flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            Analyzing…
          </>
        ) : (
          <>
            <Send size={16} />
            Upload for grading
          </>
        )}
      </button>
    </form>
  )
}
