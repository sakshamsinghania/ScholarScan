"""Tests for EvaluationService — multi-question assessment orchestration."""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from adapters.ocr.base import OcrPage, OcrResult
from services.evaluation_service import EvaluationService
from services.qa_extractor import QaSegment


def _mock_ocr_result(text: str) -> OcrResult:
    return OcrResult(
        text=text,
        confidence=0.9,
        provider="mock",
        page_data=(OcrPage(index=0, markdown=text),),
    )


@pytest.fixture
def mock_assessment_service():
    svc = MagicMock()
    svc.assess.return_value = {
        "extracted_text": "student answer text",
        "cleaned_text": "cleaned text",
        "tfidf_score": 0.5,
        "sbert_score": 0.7,
        "similarity_score": 0.65,
        "keyword_overlap": 0.6,
        "missing_keywords": ["keyword1"],
        "marks": 7.0,
        "max_marks": 10,
        "grade": "B",
        "feedback": "Good answer.",
        "assessed_at": datetime.now().isoformat(),
    }
    return svc


@pytest.fixture
def mock_pdf_service():
    svc = MagicMock()
    text = (
        "Q1. What is photosynthesis?\n"
        "Plants use sunlight to make food.\n\n"
        "Q2. What is gravity?\n"
        "Force that pulls objects down."
    )
    svc.extract_result.return_value = _mock_ocr_result(text)
    svc.extract_text.return_value = text
    return svc


@pytest.fixture
def mock_qa_extractor():
    svc = MagicMock()
    svc.extract.return_value = [
        QaSegment(sequential_id="Q1", raw_label="1.", question_text="What is photosynthesis?", answer_text="Plants use sunlight to make food.", start_page=0, end_page=0),
        QaSegment(sequential_id="Q2", raw_label="2.", question_text="What is gravity?", answer_text="Force that pulls objects down.", start_page=0, end_page=0),
    ]
    svc.extract_questions.return_value = [
        {"sequential_id": "Q1", "question": "What is photosynthesis?"},
        {"sequential_id": "Q2", "question": "What is gravity?"},
    ]
    return svc


@pytest.fixture
def mock_llm_service():
    svc = MagicMock()
    svc.is_configured = True
    svc.generate_model_answer.return_value = "Model answer from LLM"
    svc.generate_batch_answers.return_value = ["Model answer 1", "Model answer 2"]
    return svc


@pytest.fixture
def mock_ocr_fn():
    return MagicMock(return_value="OCR extracted answer text")


@pytest.fixture
def mock_result_store():
    svc = MagicMock()
    svc.store.return_value = "test-uuid"
    return svc


@pytest.fixture
def service(
    mock_pdf_service,
    mock_qa_extractor,
    mock_llm_service,
    mock_assessment_service,
    mock_result_store,
    mock_ocr_fn,
):
    return EvaluationService(
        pdf_service=mock_pdf_service,
        qa_extractor=mock_qa_extractor,
        llm_service=mock_llm_service,
        assessment_service=mock_assessment_service,
        result_store=mock_result_store,
        extract_text_fn=mock_ocr_fn,
    )


class TestEvaluatePdf:
    def test_returns_multi_result(self, service, tmp_path):
        pdf_path = str(tmp_path / "test.pdf")
        open(pdf_path, "w").close()
        result = service.evaluate(
            answer_file_path=pdf_path,
            file_type="pdf",
            student_id="alice",
        )
        assert "results" in result
        assert "total_score" in result
        assert "total_questions" in result

    def test_calls_pdf_extraction(self, service, mock_pdf_service, tmp_path):
        pdf_path = str(tmp_path / "test.pdf")
        open(pdf_path, "w").close()
        service.evaluate(answer_file_path=pdf_path, file_type="pdf")
        mock_pdf_service.extract_result.assert_called_once()

    def test_generates_llm_answers(self, service, mock_llm_service, tmp_path):
        pdf_path = str(tmp_path / "test.pdf")
        open(pdf_path, "w").close()
        service.evaluate(answer_file_path=pdf_path, file_type="pdf")
        assert mock_llm_service.generate_model_answer.called

    def test_result_count_matches_questions(self, service, tmp_path):
        pdf_path = str(tmp_path / "test.pdf")
        open(pdf_path, "w").close()
        result = service.evaluate(answer_file_path=pdf_path, file_type="pdf")
        assert result["total_questions"] == 2
        assert len(result["results"]) == 2

    def test_reuses_cached_model_answer_for_repeated_question_text(
        self,
        mock_pdf_service,
        mock_qa_extractor,
        mock_assessment_service,
        mock_result_store,
        mock_ocr_fn,
        tmp_path,
    ):
        mock_qa_extractor.extract.return_value = [
            QaSegment(
                sequential_id="Q1",
                raw_label="1.",
                question_text="What is gravity?",
                answer_text="Force that pulls objects down.",
                start_page=0, end_page=0,
            ),
            QaSegment(
                sequential_id="Q2",
                raw_label="2.",
                question_text="What is gravity?",
                answer_text="Gravity keeps planets in orbit.",
                start_page=0, end_page=0,
            ),
        ]

        openai_client = MagicMock()
        response = MagicMock()
        response.choices = [MagicMock(message=MagicMock(content="Gravity is the force of attraction between masses."))]
        openai_client.chat.completions.create.return_value = response

        with patch("services.llm_service.OpenAI", return_value=openai_client):
            from services.llm_service import LlmService
            llm_service = LlmService(
                api_key="test-key",
                model="llama-3.3-70b-versatile",
                base_url="https://api.groq.com/openai/v1",
                cache_path=str(tmp_path / "evaluation-cache.json"),
            )

        try:
            service = EvaluationService(
                pdf_service=mock_pdf_service,
                qa_extractor=mock_qa_extractor,
                llm_service=llm_service,
                assessment_service=mock_assessment_service,
                result_store=mock_result_store,
                extract_text_fn=mock_ocr_fn,
            )

            pdf_path = str(tmp_path / "test.pdf")
            open(pdf_path, "w").close()
            result = service.evaluate(answer_file_path=pdf_path, file_type="pdf")

            assert openai_client.chat.completions.create.call_count == 1
            assert [item["model_answer"] for item in result["results"]] == [
                "Gravity is the force of attraction between masses.",
                "Gravity is the force of attraction between masses.",
            ]
        finally:
            llm_service.close()


class TestEvaluateImage:
    def test_uses_ocr_for_image(self, service, mock_ocr_fn, mock_qa_extractor, tmp_path):
        img_path = str(tmp_path / "test.jpg")
        open(img_path, "w").close()
        mock_qa_extractor.extract.return_value = [
            QaSegment(
                sequential_id="Q1",
                raw_label=None,
                question_text="What concept is being explained?",
                answer_text="OCR extracted answer text",
                start_page=0, end_page=0,
            ),
        ]
        service.evaluate(answer_file_path=img_path, file_type="image")
        mock_ocr_fn.assert_called_once_with(img_path)

    def test_raises_when_text_extraction_is_empty(self, service, mock_ocr_fn, mock_qa_extractor, tmp_path):
        img_path = str(tmp_path / "test.jpg")
        open(img_path, "w").close()
        mock_ocr_fn.return_value = ""
        mock_qa_extractor.extract.return_value = []

        with pytest.raises(ValueError, match="Text extraction produced no readable content"):
            service.evaluate(answer_file_path=img_path, file_type="image")

    def test_rejects_student_answer_as_reference_fallback(self, service, mock_qa_extractor, tmp_path):
        img_path = str(tmp_path / "test.jpg")
        open(img_path, "w").close()
        mock_qa_extractor.extract.return_value = [
            QaSegment(sequential_id="Q1", raw_label=None, question_text="", answer_text="OCR extracted answer text", start_page=0, end_page=0),
        ]

        with pytest.raises(ValueError, match="authoritative question text"):
            service.evaluate(answer_file_path=img_path, file_type="image")


class TestEvaluateWithQuestionPaper:
    def test_uses_question_paper(self, service, mock_qa_extractor, tmp_path):
        answer_path = str(tmp_path / "answers.pdf")
        question_path = str(tmp_path / "questions.pdf")
        open(answer_path, "w").close()
        open(question_path, "w").close()

        service.evaluate(
            answer_file_path=answer_path,
            file_type="pdf",
            question_file_path=question_path,
            question_file_type="pdf",
        )
        # extract_questions called for question paper extraction
        mock_qa_extractor.extract_questions.assert_called_once()

    def test_raises_when_llm_is_unavailable_for_multi_question_grading(
        self, service, mock_llm_service, tmp_path
    ):
        pdf_path = str(tmp_path / "test.pdf")
        open(pdf_path, "w").close()
        mock_llm_service.is_configured = False

        with pytest.raises(ValueError, match="AI reference answer generation is unavailable"):
            service.evaluate(answer_file_path=pdf_path, file_type="pdf")

    def test_matches_question_paper_entries_by_question_id_instead_of_position(
        self,
        mock_pdf_service,
        mock_qa_extractor,
        mock_llm_service,
        mock_assessment_service,
        mock_result_store,
        mock_ocr_fn,
        tmp_path,
    ):
        mock_qa_extractor.extract.return_value = [
            QaSegment(
                sequential_id="Q1",
                raw_label="1.",
                question_text="student detected q1",
                answer_text="answer 1",
                start_page=0, end_page=0,
            ),
            QaSegment(
                sequential_id="Q3",
                raw_label="3.",
                question_text="student detected q3",
                answer_text="answer 3",
                start_page=0, end_page=0,
            ),
        ]
        mock_qa_extractor.extract_questions.return_value = [
            {"sequential_id": "Q1", "question": "paper q1"},
            {"sequential_id": "Q2", "question": "paper q2"},
            {"sequential_id": "Q3", "question": "paper q3"},
        ]

        service = EvaluationService(
            pdf_service=mock_pdf_service,
            qa_extractor=mock_qa_extractor,
            llm_service=mock_llm_service,
            assessment_service=mock_assessment_service,
            result_store=mock_result_store,
            extract_text_fn=mock_ocr_fn,
        )

        answer_path = str(tmp_path / "answers.pdf")
        question_path = str(tmp_path / "questions.pdf")
        open(answer_path, "w").close()
        open(question_path, "w").close()

        result = service.evaluate(
            answer_file_path=answer_path,
            file_type="pdf",
            question_file_path=question_path,
            question_file_type="pdf",
        )

        assert [item["question"] for item in result["results"]] == ["paper q1", "paper q3"]
        assert [call.args[0] for call in mock_llm_service.generate_model_answer.call_args_list] == [
            "paper q1",
            "paper q3",
        ]


class TestAggregation:
    def test_total_score_sums_marks(self, service, mock_assessment_service, tmp_path):
        pdf_path = str(tmp_path / "test.pdf")
        open(pdf_path, "w").close()
        result = service.evaluate(answer_file_path=pdf_path, file_type="pdf")
        assert result["total_score"] == 14.0

    def test_max_total_score_sums_max_marks(self, service, tmp_path):
        pdf_path = str(tmp_path / "test.pdf")
        open(pdf_path, "w").close()
        result = service.evaluate(answer_file_path=pdf_path, file_type="pdf", max_marks_per_question=10)
        assert result["max_total_score"] == 20

    def test_student_id_in_result(self, service, tmp_path):
        pdf_path = str(tmp_path / "test.pdf")
        open(pdf_path, "w").close()
        result = service.evaluate(answer_file_path=pdf_path, file_type="pdf", student_id="bob")
        assert result["student_id"] == "bob"

    def test_marks_assessment_exceptions_as_failed_without_f_grade(
        self,
        mock_pdf_service,
        mock_qa_extractor,
        mock_llm_service,
        mock_result_store,
        mock_ocr_fn,
        tmp_path,
    ):
        mock_assessment_service = MagicMock()
        mock_assessment_service.assess.side_effect = [
            RuntimeError("SBERT unavailable"),
            {
                "similarity_score": 0.65,
                "tfidf_score": 0.5,
                "sbert_score": 0.7,
                "keyword_overlap": 0.6,
                "missing_keywords": [],
                "marks": 7.0,
                "max_marks": 10,
                "grade": "B",
                "feedback": "Good answer.",
            },
        ]

        service = EvaluationService(
            pdf_service=mock_pdf_service,
            qa_extractor=mock_qa_extractor,
            llm_service=mock_llm_service,
            assessment_service=mock_assessment_service,
            result_store=mock_result_store,
            extract_text_fn=mock_ocr_fn,
        )

        pdf_path = str(tmp_path / "test.pdf")
        open(pdf_path, "w").close()

        result = service.evaluate(answer_file_path=pdf_path, file_type="pdf")

        failed_question = result["results"][0]
        assert failed_question["status"] == "failed"
        assert failed_question["grade"] == "N/A"
        assert "SBERT unavailable" in failed_question["failure_reason"]
        assert result["failed_questions"] == 1
        assert result["status"] == "partial_failure"
