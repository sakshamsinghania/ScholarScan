"""Orchestrate multi-question assessment: OCR → Q&A Extraction → LLM → Scoring."""

import logging
from datetime import datetime, timezone
from typing import Callable

from adapters.ocr.base import OcrResult
from config import Config
from core.similarity import TieredReference
from services.pdf_service import PdfService
from services.qa_extractor import QaExtractor
from services.llm_service import LlmService
from services.assessment_service import AssessmentService
from services.result_storage_service import ResultStorageService

logger = logging.getLogger(__name__)


class EvaluationService:
    """
    Multi-question assessment orchestrator.

    Pipeline:
    1. Extract OCR result from answer file (page-aware OcrResult)
    2. Run QaExtractor on page markdown to detect Q&A segments
    3. Optionally extract questions from a separate question paper
    4. Generate model answers via LLM for each question
    5. Run per-question assessment via AssessmentService
    6. Aggregate and return results
    """

    def __init__(
        self,
        pdf_service: PdfService,
        qa_extractor: QaExtractor,
        llm_service: LlmService,
        assessment_service: AssessmentService,
        result_store: ResultStorageService,
        extract_text_fn: Callable[[str], str],
        extract_result_fn: Callable[[str], OcrResult] | None = None,
    ):
        self._pdf = pdf_service
        self._qa = qa_extractor
        self._llm = llm_service
        self._assess = assessment_service
        self._store = result_store
        self._extract_text = extract_text_fn
        self._extract_result = extract_result_fn

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

        # Step 1: Extract OCR result (page-aware)
        _progress("text_extraction", self._text_extraction_started_message(file_type))
        ocr_result = self._extract_raw_ocr(answer_file_path, file_type, on_progress=_progress)
        if not ocr_result.text or not ocr_result.text.strip():
            raise ValueError(
                "Text extraction produced no readable content from the uploaded file."
            )
        _progress("text_extraction", f"Extracted {len(ocr_result.text)} characters")

        # Step 2: NLP preprocessing (implicit in assessment service)
        _progress("nlp_preprocessing", "Cleaning and preprocessing text")

        # Step 3: Detect Q&A segments via QaExtractor
        pages_md = [p.markdown for p in ocr_result.page_data] if ocr_result.page_data else [ocr_result.text]
        detected = self._qa.extract(pages_md)
        detected = [d for d in detected if not d.is_orphan]
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

            tiered: TieredReference | None = None
            tiered_enabled = getattr(Config, "TIERED_REFERENCE_ENABLED", False)

            if tiered_enabled and hasattr(self._llm, "generate_tiered_model_answer"):
                tiered = self._llm.generate_tiered_model_answer(question_text)
                model_answer = tiered.flat_text
            else:
                model_answer = self._llm.generate_model_answer(question_text).strip()

            if not model_answer:
                raise ValueError(
                    f"AI reference answer generation failed for {dq.sequential_id}. "
                    "Please retry or switch to manual assessment with a teacher-provided model answer."
                )

            _progress("answer_mapping", f"Processing Q{i + 1}")
            _progress("similarity", f"Evaluating Q{i + 1}")

            try:
                result = self._assess.assess(
                    image_path=answer_file_path,
                    model_answer=model_answer,
                    question_id=dq.sequential_id,
                    student_id=student_id,
                    max_marks=max_marks_per_question,
                    pre_extracted_text=dq.answer_text,
                    source=ocr_result.provider,
                    tiered_reference=tiered,
                )
            except Exception as e:
                logger.error("Assessment failed for %s: %s", dq.sequential_id, e)
                result = self._failed_result(dq.sequential_id, max_marks_per_question, str(e))

            per_question_results.append({
                "question_id": dq.sequential_id,
                "question": question_text,
                "student_answer": dq.answer_text,
                "model_answer": model_answer,
                "similarity_score": result.get("similarity_score", 0),
                "tfidf_score": result.get("tfidf_score", 0),
                "sbert_score": result.get("sbert_score", 0),
                "sentence_similarity": result.get("sentence_similarity", 0),
                "concept_coverage": result.get("concept_coverage", 0),
                "entailment_score": result.get("entailment_score"),
                "keyword_overlap": result.get("keyword_overlap", 0),
                "missing_keywords": result.get("missing_keywords", []),
                "marks": result.get("marks", 0),
                "max_marks": max_marks_per_question,
                "grade": result.get("grade", "N/A"),
                "feedback": result.get("feedback", ""),
                "status": result.get("status", "completed"),
                "failure_reason": result.get("failure_reason"),
                "reference_tiers": {
                    "core": tiered.core,
                    "supporting": tiered.supporting,
                    "extended": tiered.extended,
                } if tiered and tiered.core else None,
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

    def _extract_raw_ocr(
        self,
        file_path: str,
        file_type: str,
        on_progress: Callable[[str, str], None] | None = None,
    ) -> OcrResult:
        if file_type == "pdf":
            return self._pdf.extract_result(
                file_path,
                on_progress=lambda current, total, mode: self._report_pdf_progress(
                    current, total, mode, on_progress,
                ),
            )
        else:
            if self._extract_result:
                return self._extract_result(file_path)
            text = self._extract_text(file_path)
            from adapters.ocr.base import OcrPage
            return OcrResult(
                text=text,
                confidence=0.0,
                provider="unknown",
                page_data=(OcrPage(index=0, markdown=text),),
            )

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
        ocr_result = self._extract_raw_ocr(file_path, file_type)
        pages_md = [p.markdown for p in ocr_result.page_data] if ocr_result.page_data else [ocr_result.text]
        return self._qa.extract_questions(pages_md)

    @staticmethod
    def _build_question_lookup(question_texts: list[dict] | None) -> dict[str, str]:
        if not question_texts:
            return {}

        lookup: dict[str, str] = {}
        for entry in question_texts:
            qid = str(entry.get("sequential_id", entry.get("question_id", ""))).strip().upper()
            question_text = str(entry.get("question", "")).strip()
            if qid and question_text:
                lookup[qid] = question_text
        return lookup

    @staticmethod
    def _resolve_question_text(
        detected_question,
        question_texts: list[dict] | None,
        question_lookup: dict[str, str],
        index: int,
    ) -> str:
        detected_id = (detected_question.sequential_id or "").strip().upper()
        if detected_id and detected_id in question_lookup:
            return question_lookup[detected_id]

        if question_texts and index < len(question_texts):
            fallback = str(question_texts[index].get("question", "")).strip()
            if fallback:
                return fallback

        return detected_question.question_text.strip()

    @staticmethod
    def _failed_result(question_id: str, max_marks: int, failure_reason: str) -> dict:
        return {
            "similarity_score": 0,
            "tfidf_score": 0,
            "sbert_score": 0,
            "sentence_similarity": 0,
            "concept_coverage": 0,
            "entailment_score": None,
            "keyword_overlap": 0,
            "missing_keywords": [],
            "marks": 0,
            "max_marks": max_marks,
            "grade": "N/A",
            "feedback": "Assessment could not be completed for this question.",
            "status": "failed",
            "failure_reason": failure_reason or f"Assessment failed for {question_id}.",
        }
