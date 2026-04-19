export interface AssessmentResponse {
  extracted_text: string
  cleaned_text: string
  tfidf_score: number
  sbert_score: number
  similarity_score: number
  keyword_overlap: number
  missing_keywords: string[]
  marks: number
  max_marks: number
  grade: string
  feedback: string
  assessed_at: string
}

export interface QuestionResult {
  question_id: string
  question: string
  student_answer: string
  model_answer: string
  similarity_score: number
  tfidf_score: number
  sbert_score: number
  keyword_overlap: number
  missing_keywords: string[]
  marks: number
  max_marks: number
  grade: string
  feedback: string
  status: 'completed' | 'failed'
  failure_reason?: string | null
}

export interface MultiAssessmentResponse {
  total_score: number
  max_total_score: number
  total_questions: number
  failed_questions: number
  status: 'completed' | 'partial_failure'
  student_id: string
  assessed_at: string
  results: QuestionResult[]
}

export type AnyAssessmentResult = AssessmentResponse | MultiAssessmentResponse

export function isMultiAssessment(result: AnyAssessmentResult): result is MultiAssessmentResponse {
  return 'results' in result && 'total_questions' in result
}

export interface HealthStatus {
  status: 'healthy' | 'degraded'
  ocr_available: boolean
  tesseract_available: boolean
  vision_credentials_configured: boolean
  sbert_loaded: boolean
  spacy_model_loaded: boolean
  llm_configured: boolean
  pdf_support: boolean
  capabilities: {
    ocr: boolean
    semantic_similarity: boolean
    llm: boolean
    pdf: boolean
  }
  supported_modes: {
    manual_assessment: boolean
    auto_reference_generation: boolean
    multi_question_assessment: boolean
  }
  timestamp: string
}

export interface SingleHistoryResult {
  id: string
  result_type: 'single_question'
  student_id: string
  assessed_at: string
  question_id: string
  score_ratio: number
  marks: number
  max_marks: number
  grade: string
}

export interface MultiHistoryResult {
  id: string
  result_type: 'multi_question'
  student_id: string
  assessed_at: string
  total_questions: number
  total_score: number
  max_total_score: number
  average_score_ratio: number
}

export type HistoryResult = SingleHistoryResult | MultiHistoryResult

export interface ResultsResponse {
  results: HistoryResult[]
  count: number
}

// ── Progress tracking types ──

export interface ProgressEvent {
  task_id: string
  stage: string
  status: 'running' | 'completed' | 'error'
  message: string
  step: number
  total_steps: number
  completed_stages: string[]
}

export interface TaskStartResponse {
  task_id: string
  status: 'processing'
}

export const PIPELINE_STAGES = [
  { key: 'upload_received', label: 'Upload received', icon: 'Upload' },
  { key: 'file_type_detection', label: 'File type detection', icon: 'FileSearch' },
  { key: 'text_extraction', label: 'Text extraction', icon: 'ScanText' },
  { key: 'nlp_preprocessing', label: 'NLP preprocessing', icon: 'Braces' },
  { key: 'question_detection', label: 'Question detection', icon: 'Search' },
  { key: 'llm_generation', label: 'AI answer generation', icon: 'Sparkles' },
  { key: 'answer_mapping', label: 'Answer mapping', icon: 'ArrowRightLeft' },
  { key: 'similarity', label: 'Similarity computation', icon: 'GitCompare' },
  { key: 'scoring', label: 'Scoring & feedback', icon: 'Award' },
  { key: 'completed', label: 'Complete', icon: 'CheckCircle' },
] as const
