"""Orchestrate multi-question assessment: PDF → Questions → LLM → Scoring."""

import logging
from datetime import datetime, timezone
from typing import Callable

from services.pdf_service import PdfService
from services.question_service import QuestionService
from services.llm_service import LlmService
from services.assessment_service import AssessmentService
from services.result_storage_service import ResultStorageService

logger = logging.getLogger(__name__)


class EvaluationService:
    """
    Multi-question assessment orchestrator.

    Pipeline:
    1. Extract text from answer file (OCR for images, pdfplumber for PDFs)
    2. Detect Q&A segments from student text
    3. Optionally extract questions from a separate question paper
    4. Generate model answers via LLM for each question
    5. Run per-question assessment via AssessmentService
    6. Aggregate and return results
    """

    def __init__(
        self,
        pdf_service: PdfService,
        question_service: QuestionService,
        llm_service: LlmService,
        assessment_service: AssessmentService,
        result_store: ResultStorageService,
        extract_text_fn: Callable[[str], str],
    ):
        self._pdf = pdf_service
        self._questions = question_service
        self._llm = llm_service
        self._assess = assessment_service
        self._store = result_store
        self._extract_text = extract_text_fn

    def evaluate(
        self,
        answer_file_path: str,
        file_type: str,
        question_file_path: str | None = None,
        question_file_type: str | None = None,
        student_id: str = "anonymous",
        max_marks_per_question: int = 10,
        on_progress: Callable[[str, str], None] | None = None,
    ) -> dict:
        """
        Run the full multi-question pipeline.

        Args:
            answer_file_path: Path to the uploaded answer file.
            file_type: "image" or "pdf".
            question_file_path: Optional separate question paper.
            question_file_type: "image" or "pdf" for the question paper.
            student_id: Student identifier.
            max_marks_per_question: Marks per question.
            on_progress: Optional callback(stage, message) for live updates.

        Returns:
            MultiAssessmentResponse-shaped dict.
        """
        def _progress(stage: str, message: str = ""):
            if on_progress:
                on_progress(stage, message)

        logger.info(
            "Starting evaluation for student_id=%s file_type=%s answer_file=%s question_file=%s",
            student_id,
            file_type,
            answer_file_path,
            question_file_path,
        )
        _progress("upload_received", "File received for processing")
        _progress("file_type_detection", f"Detected file type: {file_type}")

        # Step 1: Extract raw text from answer file
        _progress("text_extraction", self._text_extraction_started_message(file_type))
        raw_text = self._extract_raw_text(answer_file_path, file_type, on_progress=_progress)
        if not raw_text or not raw_text.strip():
            raise ValueError(
                "Text extraction produced no readable content from the uploaded file."
            )
        _progress("text_extraction", f"Extracted {len(raw_text)} characters")

        # Step 2: NLP preprocessing (implicit in assessment service)
        _progress("nlp_preprocessing", "Cleaning and preprocessing text")

        # Step 3: Detect Q&A segments from student text
        detected = self._questions.detect_questions(raw_text)
        if not detected:
            raise ValueError("No questions or answers could be detected in the uploaded file.")
        _progress("question_detection", f"Found {len(detected)} question(s)")

        # Step 4: If separate question paper provided, extract questions
        question_texts = None
        if question_file_path:
            question_texts = self._extract_question_paper(
                question_file_path, question_file_type or file_type
            )

        # Step 5: Generate model answers via LLM
        if not getattr(self._llm, "is_configured", False):
            raise ValueError(
                "AI reference answer generation is unavailable. "
                "Configure the LLM service or use manual assessment with a teacher-provided model answer."
            )

        _progress("llm_generation", f"Generating answers for {len(detected)} question(s)")

        per_question_results = []
        question_lookup = self._build_question_lookup(question_texts)
        for i, dq in enumerate(detected):
            question_text = self._resolve_question_text(
                detected_question=dq,
                question_texts=question_texts,
                question_lookup=question_lookup,
                index=i,
            )

            if not question_text:
                raise ValueError(
                    "Assessment requires authoritative question text. "
                    "Upload the question paper or use manual mode with a teacher-provided model answer."
                )

            # Generate model answer via LLM
            model_answer = self._llm.generate_model_answer(question_text).strip()
            if not model_answer:
                raise ValueError(
                    f"AI reference answer generation failed for {dq.question_id}. "
                    "Please retry or switch to manual assessment with a teacher-provided model answer."
                )

            _progress("answer_mapping", f"Processing Q{i + 1}")

            # Step 6: Similarity + Scoring (per question)
            _progress("similarity", f"Evaluating Q{i + 1}")

            try:
                result = self._assess.assess(
                    image_path=answer_file_path,
                    model_answer=model_answer,
                    question_id=dq.question_id,
                    student_id=student_id,
                    max_marks=max_marks_per_question,
                    pre_extracted_text=dq.answer_text,
                )
            except Exception as e:
                logger.error("Assessment failed for %s: %s", dq.question_id, e)
                result = self._failed_result(dq.question_id, max_marks_per_question, str(e))

            per_question_results.append({
                "question_id": dq.question_id,
                "question": question_text,
                "student_answer": dq.answer_text,
                "model_answer": model_answer,
                "similarity_score": result.get("similarity_score", 0),
                "tfidf_score": result.get("tfidf_score", 0),
                "sbert_score": result.get("sbert_score", 0),
                "keyword_overlap": result.get("keyword_overlap", 0),
                "missing_keywords": result.get("missing_keywords", []),
                "marks": result.get("marks", 0),
                "max_marks": max_marks_per_question,
                "grade": result.get("grade", "N/A"),
                "feedback": result.get("feedback", ""),
                "status": result.get("status", "completed"),
                "failure_reason": result.get("failure_reason"),
            })

        _progress("scoring", "Aggregating final scores")

        # Step 7: Aggregate
        now = datetime.now(timezone.utc).isoformat()
        failed_questions = sum(1 for result in per_question_results if result["status"] == "failed")
        total_score = sum(r["marks"] for r in per_question_results)
        max_total = max_marks_per_question * len(per_question_results)

        response = {
            "total_score": total_score,
            "max_total_score": max_total,
            "total_questions": len(per_question_results),
            "failed_questions": failed_questions,
            "status": "partial_failure" if failed_questions else "completed",
            "student_id": student_id,
            "assessed_at": now,
            "results": per_question_results,
        }

        # Store aggregated result
        self._store.store(response)

        logger.info(
            "Completed evaluation for student_id=%s total_questions=%d total_score=%s/%s",
            student_id,
            len(per_question_results),
            total_score,
            max_total,
        )
        _progress("completed", "Assessment complete!")

        return response

    def _extract_raw_text(
        self,
        file_path: str,
        file_type: str,
        on_progress: Callable[[str, str], None] | None = None,
    ) -> str:
        """Extract text from file based on type."""
        if file_type == "pdf":
            return self._pdf.extract_text(
                file_path,
                on_progress=lambda current, total, mode: self._report_pdf_progress(
                    current,
                    total,
                    mode,
                    on_progress,
                ),
            )
        else:
            return self._extract_text(file_path)

    @staticmethod
    def _text_extraction_started_message(file_type: str) -> str:
        if file_type == "pdf":
            return "Extracting text from PDF pages"
        return "Extracting text from uploaded file"

    @staticmethod
    def _report_pdf_progress(
        current_page: int,
        total_pages: int,
        extraction_mode: str,
        on_progress: Callable[[str, str], None] | None,
    ) -> None:
        if not on_progress:
            return

        mode_label = "OCR" if extraction_mode == "ocr" else "digital extraction"
        on_progress(
            "text_extraction",
            f"Processing page {current_page}/{total_pages} via {mode_label}",
        )

    def _extract_question_paper(self, file_path: str, file_type: str) -> list[dict]:
        """Extract questions from a separate question paper."""
        raw = self._extract_raw_text(file_path, file_type)
        return self._questions.extract_questions_only(raw)

    @staticmethod
    def _build_question_lookup(question_texts: list[dict] | None) -> dict[str, str]:
        if not question_texts:
            return {}

        lookup: dict[str, str] = {}
        for entry in question_texts:
            question_id = str(entry.get("question_id", "")).strip().upper()
            question_text = str(entry.get("question", "")).strip()
            if question_id and question_text:
                lookup[question_id] = question_text
        return lookup

    @staticmethod
    def _resolve_question_text(
        detected_question,
        question_texts: list[dict] | None,
        question_lookup: dict[str, str],
        index: int,
    ) -> str:
        detected_id = (detected_question.question_id or "").strip().upper()
        if detected_id and detected_id in question_lookup:
            return question_lookup[detected_id]

        if question_texts and index < len(question_texts):
            fallback = str(question_texts[index].get("question", "")).strip()
            if fallback:
                return fallback

        return detected_question.text.strip()

    @staticmethod
    def _failed_result(question_id: str, max_marks: int, failure_reason: str) -> dict:
        """Fallback result when assessment fails for a question."""
        return {
            "similarity_score": 0,
            "tfidf_score": 0,
            "sbert_score": 0,
            "keyword_overlap": 0,
            "missing_keywords": [],
            "marks": 0,
            "max_marks": max_marks,
            "grade": "N/A",
            "feedback": "Assessment could not be completed for this question.",
            "status": "failed",
            "failure_reason": failure_reason or f"Assessment failed for {question_id}.",
        }
