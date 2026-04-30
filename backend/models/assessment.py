"""Pydantic schemas for assessment request/response validation."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AssessmentBaseModel(BaseModel):
    """Shared base model for assessment schemas."""

    model_config = ConfigDict(protected_namespaces=())


class AssessmentResponse(AssessmentBaseModel):
    """JSON response shape for POST /api/assess (single-question, backward compat)."""

    extracted_text: str = Field(description="Raw OCR output from Google Vision")
    cleaned_text: str = Field(description="NLP-preprocessed student text")
    tfidf_score: float = Field(ge=0.0, le=1.0)
    sbert_score: float = Field(ge=-1.0, le=1.0)
    similarity_score: float = Field(description="Weighted combined score")
    keyword_overlap: float = Field(ge=0.0, le=1.0)
    missing_keywords: list[str] = Field(default_factory=list)
    marks: float = Field(ge=0.0)
    max_marks: int = Field(ge=1)
    grade: str = Field(description="Letter grade: A/B/C/D/F")
    feedback: str
    assessed_at: str = Field(description="ISO 8601 timestamp")


class QuestionResult(AssessmentBaseModel):
    """Result for a single question within a multi-question assessment."""

    question_id: str
    question: str = Field(default="", description="Detected question text")
    student_answer: str = Field(description="Student's answer for this question")
    model_answer: str = Field(description="LLM-generated or provided model answer")
    similarity_score: float = Field(description="Weighted combined score")
    tfidf_score: float = Field(ge=0.0, le=1.0)
    sbert_score: float = Field(ge=-1.0, le=1.0)
    sentence_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    concept_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    entailment_score: float | None = Field(default=None)
    keyword_overlap: float = Field(ge=0.0, le=1.0)
    missing_keywords: list[str] = Field(default_factory=list)
    marks: float = Field(ge=0.0)
    max_marks: int = Field(ge=1)
    grade: str
    feedback: str
    status: Literal["completed", "failed"] = "completed"
    failure_reason: str | None = None


class MultiAssessmentResponse(AssessmentBaseModel):
    """JSON response shape for multi-question assessment."""

    total_score: float = Field(ge=0.0)
    max_total_score: int = Field(ge=1)
    total_questions: int = Field(ge=1)
    failed_questions: int = Field(ge=0)
    status: Literal["completed", "partial_failure"] = "completed"
    student_id: str
    assessed_at: str = Field(description="ISO 8601 timestamp")
    results: list[QuestionResult]


class TaskStartResponse(AssessmentBaseModel):
    """Accepted async assessment task."""

    task_id: str
    status: Literal["processing"]


class SingleHistoryEntry(AssessmentBaseModel):
    """History-safe summary for a single-question assessment."""

    id: str
    result_type: Literal["single_question"]
    student_id: str
    assessed_at: str
    question_id: str
    score_ratio: float = Field(ge=0.0, le=1.0)
    marks: float = Field(ge=0.0)
    max_marks: int = Field(ge=1)
    grade: str


class MultiHistoryEntry(AssessmentBaseModel):
    """History-safe summary for an aggregate multi-question assessment."""

    id: str
    result_type: Literal["multi_question"]
    student_id: str
    assessed_at: str
    total_questions: int = Field(ge=1)
    total_score: float = Field(ge=0.0)
    max_total_score: int = Field(ge=1)
    average_score_ratio: float = Field(ge=0.0, le=1.0)


class ErrorResponse(AssessmentBaseModel):
    """Standard error envelope."""

    error: str
    code: int
