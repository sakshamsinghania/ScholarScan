"""Orchestrates the core assessment pipeline: OCR → NLP → Similarity → Scoring."""

from datetime import datetime, timezone
from typing import Any, Callable

from core.similarity import TieredReference
from services.result_storage_service import ResultStorageService


class AssessmentService:
    """
    Business layer that coordinates core modules to assess a student answer.

    Uses dependency injection for all core functions, making it fully
    testable without loading heavy ML models.
    """

    def __init__(
        self,
        extract_text_fn: Callable,
        preprocess_for_tfidf_fn: Callable,
        preprocess_for_sbert_fn: Callable,
        compute_similarity_fn: Callable,
        score_answer_fn: Callable,
        sbert_model: Any,
        result_store: ResultStorageService,
        preprocess_markdown_for_sbert_fn: Callable | None = None,
    ):
        self._extract_text = extract_text_fn
        self._preprocess_for_tfidf = preprocess_for_tfidf_fn
        self._preprocess_for_sbert = preprocess_for_sbert_fn
        self._preprocess_markdown_for_sbert = preprocess_markdown_for_sbert_fn
        self._compute_similarity = compute_similarity_fn
        self._score_answer = score_answer_fn
        self._sbert_model = sbert_model
        self._result_store = result_store

    def assess(
        self,
        image_path: str,
        model_answer: str,
        question_id: str = "Q1",
        student_id: str = "anonymous",
        max_marks: int = 10,
        pre_extracted_text: str | None = None,
        source: str = "manual",
        tiered_reference: TieredReference | None = None,
    ) -> dict:
        """
        Run the full assessment pipeline for a single student answer.

        Args:
            image_path: Path to the answer file (used for OCR if needed).
            model_answer: Reference answer to compare against.
            question_id: Identifier for the question being assessed.
            student_id: Student identifier.
            max_marks: Maximum marks for this question.
            pre_extracted_text: If provided, skip OCR and use this text directly.
                Used by EvaluationService when text was already extracted from PDF.

        Returns a dict matching the AssessmentResponse schema.
        Raises ValueError if OCR produces no text.
        Raises RuntimeError if OCR or processing fails.
        """
        # Step 1: Use pre-extracted text or run OCR
        if pre_extracted_text and pre_extracted_text.strip():
            raw_text = pre_extracted_text
        else:
            raw_text = self._run_ocr(image_path)

        # Step 2: NLP preprocessing (two modes)
        student_tfidf = self._preprocess_for_tfidf(raw_text)
        model_tfidf = self._preprocess_for_tfidf(model_answer)

        if source == "mistral" and self._preprocess_markdown_for_sbert:
            student_sbert = self._preprocess_markdown_for_sbert(raw_text)
            model_sbert = self._preprocess_markdown_for_sbert(model_answer)
        else:
            student_sbert = self._preprocess_for_sbert(raw_text)
            model_sbert = self._preprocess_for_sbert(model_answer)

        # Step 3: Similarity computation
        sim_result = self._compute_similarity(
            student_tfidf=student_tfidf,
            model_tfidf=model_tfidf,
            student_sbert=student_sbert,
            model_sbert=model_sbert,
            sbert_model=self._sbert_model,
            tiered_reference=tiered_reference,
        )

        # Step 4: Scoring
        assessment = self._score_answer(
            similarity_result=sim_result,
            question_id=question_id,
            student_id=student_id,
            raw_ocr_text=raw_text,
            cleaned_text=student_tfidf,
            max_marks=max_marks,
        )

        # Step 5: Build response
        response = self._build_response(assessment)
        response["sentence_similarity"] = sim_result.get("sentence_similarity", 0.0)
        response["concept_coverage"] = sim_result.get("concept_coverage", 0.0)
        response["entailment_score"] = sim_result.get("entailment_score")

        # Step 6: Store result
        stored = {**response, "question_id": question_id, "student_id": student_id}
        self._result_store.store(stored)

        return response

    def _run_ocr(self, image_path: str) -> str:
        """Extract text from image with error wrapping."""
        try:
            raw_text = self._extract_text(image_path)
        except Exception as e:
            raise RuntimeError(f"OCR failed: {e}") from e

        if not raw_text or not raw_text.strip():
            raise ValueError(
                "OCR extracted no text from the image. "
                "Ensure the image contains readable handwritten text."
            )

        return raw_text

    @staticmethod
    def _build_response(assessment: Any) -> dict:
        """Map core AssessmentResult to API response dict."""
        return {
            "extracted_text": assessment.raw_ocr_text,
            "cleaned_text": assessment.cleaned_text,
            "tfidf_score": assessment.tfidf_score,
            "sbert_score": assessment.sbert_score,
            "similarity_score": assessment.combined_score,
            "keyword_overlap": assessment.keyword_overlap,
            "missing_keywords": assessment.missing_keywords,
            "marks": assessment.marks,
            "max_marks": assessment.max_marks,
            "grade": assessment.grade,
            "feedback": assessment.feedback,
            "assessed_at": datetime.now(timezone.utc).isoformat(),
        }
