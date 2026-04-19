"""Tests for AssessmentService — orchestrates core assessment pipeline."""

import os
import sys
import pytest
from unittest.mock import MagicMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.assessment_service import AssessmentService
from services.result_storage_service import ResultStorageService


@pytest.fixture
def mock_dependencies():
    """Create mock callables that mimic core module functions."""
    return {
        "extract_text": MagicMock(return_value="Plants make food from sunlight"),
        "preprocess_for_tfidf": MagicMock(return_value="plant make food sunlight"),
        "preprocess_for_sbert": MagicMock(
            return_value="plants make food from sunlight"
        ),
        "compute_similarity": MagicMock(
            return_value={
                "tfidf_score": 0.52,
                "sbert_score": 0.73,
                "combined_score": 0.67,
                "keyword_overlap": 0.60,
                "missing_keywords": ["chlorophyll", "glucose"],
            }
        ),
        "score_answer": MagicMock(
            return_value=MagicMock(
                raw_ocr_text="Plants make food from sunlight",
                cleaned_text="plant make food sunlight",
                tfidf_score=0.52,
                sbert_score=0.73,
                combined_score=0.67,
                keyword_overlap=0.60,
                missing_keywords=["chlorophyll", "glucose"],
                marks=7.5,
                max_marks=10,
                grade="B",
                feedback="Good answer.",
            )
        ),
        "sbert_model": MagicMock(),
    }


@pytest.fixture
def service(mock_dependencies):
    store = ResultStorageService()
    return AssessmentService(
        extract_text_fn=mock_dependencies["extract_text"],
        preprocess_for_tfidf_fn=mock_dependencies["preprocess_for_tfidf"],
        preprocess_for_sbert_fn=mock_dependencies["preprocess_for_sbert"],
        compute_similarity_fn=mock_dependencies["compute_similarity"],
        score_answer_fn=mock_dependencies["score_answer"],
        sbert_model=mock_dependencies["sbert_model"],
        result_store=store,
    )


class TestAssess:
    def test_returns_response_dict(self, service):
        result = service.assess(
            image_path="/fake/path.jpg",
            model_answer="Photosynthesis is...",
        )
        assert isinstance(result, dict)

    def test_response_contains_required_fields(self, service):
        result = service.assess(
            image_path="/fake/path.jpg",
            model_answer="Photosynthesis is...",
        )
        required = {
            "extracted_text",
            "cleaned_text",
            "tfidf_score",
            "sbert_score",
            "similarity_score",
            "keyword_overlap",
            "missing_keywords",
            "marks",
            "max_marks",
            "grade",
            "feedback",
            "assessed_at",
        }
        assert required.issubset(result.keys())

    def test_calls_extract_text_with_image_path(self, service, mock_dependencies):
        service.assess(image_path="/test/image.jpg", model_answer="answer")
        mock_dependencies["extract_text"].assert_called_once_with("/test/image.jpg")

    def test_calls_preprocess_for_both_modes(self, service, mock_dependencies):
        service.assess(image_path="/test/image.jpg", model_answer="answer")
        # Should be called twice: once for student text, once for model answer
        assert mock_dependencies["preprocess_for_tfidf"].call_count == 2
        assert mock_dependencies["preprocess_for_sbert"].call_count == 2

    def test_calls_compute_similarity(self, service, mock_dependencies):
        service.assess(image_path="/test/image.jpg", model_answer="answer")
        mock_dependencies["compute_similarity"].assert_called_once()

    def test_calls_score_answer(self, service, mock_dependencies):
        service.assess(image_path="/test/image.jpg", model_answer="answer")
        mock_dependencies["score_answer"].assert_called_once()

    def test_stores_result(self, service):
        service.assess(image_path="/test/image.jpg", model_answer="answer")
        assert len(service._result_store.get_all()) == 1

    def test_assessed_at_is_iso_format(self, service):
        result = service.assess(image_path="/test/image.jpg", model_answer="answer")
        # Should parse as valid ISO datetime
        datetime.fromisoformat(result["assessed_at"])

    def test_handles_custom_question_and_student_id(self, service):
        result = service.assess(
            image_path="/test/image.jpg",
            model_answer="answer",
            question_id="Q5",
            student_id="john",
            max_marks=20,
        )
        assert result["max_marks"] == 10  # max_marks comes from score_answer mock


class TestAssessErrors:
    def test_raises_on_empty_ocr_text(self, service, mock_dependencies):
        mock_dependencies["extract_text"].return_value = ""
        with pytest.raises(ValueError, match="OCR extracted no text"):
            service.assess(image_path="/test/image.jpg", model_answer="answer")

    def test_raises_on_whitespace_only_ocr(self, service, mock_dependencies):
        mock_dependencies["extract_text"].return_value = "   \n  "
        with pytest.raises(ValueError, match="OCR extracted no text"):
            service.assess(image_path="/test/image.jpg", model_answer="answer")

    def test_wraps_ocr_exception(self, service, mock_dependencies):
        mock_dependencies["extract_text"].side_effect = FileNotFoundError("no file")
        with pytest.raises(RuntimeError, match="OCR failed"):
            service.assess(image_path="/bad/path.jpg", model_answer="answer")
