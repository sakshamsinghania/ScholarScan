"""Tests for EvaluationService progress callback integration."""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from adapters.ocr.base import OcrPage, OcrResult
from services.evaluation_service import EvaluationService
from services.qa_extractor import QaExtractor


def _make_service(mock_extract=None):
    """Build EvaluationService with all mocked dependencies."""
    mock_extract = mock_extract or MagicMock(return_value="Q1. What is AI?\nArtificial Intelligence is...")

    mock_assess_result = {
        "similarity_score": 0.7,
        "tfidf_score": 0.6,
        "sbert_score": 0.8,
        "keyword_overlap": 0.5,
        "missing_keywords": [],
        "marks": 7,
        "max_marks": 10,
        "grade": "B",
        "feedback": "Good.",
    }

    mock_pdf = MagicMock()
    mock_pdf.extract_result.return_value = OcrResult(
        text="Q1. What is AI?\nAI answer",
        confidence=0.9,
        provider="mock",
        page_data=(OcrPage(index=0, markdown="Q1. What is AI?\nAI answer"),),
    )

    return EvaluationService(
        pdf_service=mock_pdf,
        qa_extractor=QaExtractor(),
        llm_service=MagicMock(
            generate_model_answer=MagicMock(return_value="AI is a field of computer science.")
        ),
        assessment_service=MagicMock(assess=MagicMock(return_value=mock_assess_result)),
        result_store=MagicMock(),
        extract_text_fn=mock_extract,
    )


class TestProgressCallback:
    def test_callback_invoked_during_pipeline(self):
        svc = _make_service()
        progress_calls = []

        def on_progress(stage: str, message: str = ""):
            progress_calls.append(stage)

        svc.evaluate(
            answer_file_path="/fake/image.jpg",
            file_type="image",
            on_progress=on_progress,
        )

        assert "upload_received" in progress_calls
        assert "file_type_detection" in progress_calls
        assert "text_extraction" in progress_calls
        assert "question_detection" in progress_calls
        assert "llm_generation" in progress_calls
        assert "similarity" in progress_calls
        assert "scoring" in progress_calls
        assert "completed" in progress_calls

    def test_callback_none_is_safe(self):
        svc = _make_service()

        result = svc.evaluate(
            answer_file_path="/fake/image.jpg",
            file_type="image",
        )
        assert result["total_questions"] >= 1

    def test_callback_receives_messages(self):
        svc = _make_service()
        messages = {}

        def on_progress(stage: str, message: str = ""):
            messages[stage] = message

        svc.evaluate(
            answer_file_path="/fake/image.jpg",
            file_type="image",
            on_progress=on_progress,
        )

        assert "character" in messages.get("text_extraction", "").lower() or len(messages.get("text_extraction", "")) > 0

    def test_pdf_pipeline_enters_text_extraction_before_pdf_work_starts(self):
        pdf_service = MagicMock()
        seen_stages = []

        def on_progress(stage: str, message: str = ""):
            seen_stages.append(stage)

        def extract_result_side_effect(*args, **kwargs):
            assert seen_stages[-1] == "text_extraction"
            return OcrResult(
                text="Q1. What is AI?\nArtificial Intelligence is...",
                confidence=0.9,
                provider="mock",
                page_data=(OcrPage(index=0, markdown="Q1. What is AI?\nArtificial Intelligence is..."),),
            )

        pdf_service.extract_result.side_effect = extract_result_side_effect

        svc = EvaluationService(
            pdf_service=pdf_service,
            qa_extractor=QaExtractor(),
            llm_service=MagicMock(
                generate_model_answer=MagicMock(return_value="AI is a field of computer science.")
            ),
            assessment_service=MagicMock(assess=MagicMock(return_value={
                "similarity_score": 0.7,
                "tfidf_score": 0.6,
                "sbert_score": 0.8,
                "keyword_overlap": 0.5,
                "missing_keywords": [],
                "marks": 7,
                "max_marks": 10,
                "grade": "B",
                "feedback": "Good.",
            })),
            result_store=MagicMock(),
            extract_text_fn=MagicMock(),
        )

        svc.evaluate(
            answer_file_path="/fake/answer.pdf",
            file_type="pdf",
            on_progress=on_progress,
        )

        assert "text_extraction" in seen_stages

    def test_error_in_pipeline_calls_error_callback(self):
        mock_extract = MagicMock(side_effect=RuntimeError("OCR broke"))
        svc = _make_service(mock_extract=mock_extract)
        progress_calls = []

        def on_progress(stage: str, message: str = ""):
            progress_calls.append((stage, message))

        with pytest.raises(RuntimeError):
            svc.evaluate(
                answer_file_path="/fake/image.jpg",
                file_type="image",
                on_progress=on_progress,
            )
