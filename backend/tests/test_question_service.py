"""Tests for QuestionService — question detection and Q&A parsing."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.question_service import QuestionService, DetectedQuestion


@pytest.fixture
def service():
    return QuestionService()


class TestDetectQuestions:
    def test_detects_q_numbered_pattern(self, service):
        text = (
            "Q1. What is photosynthesis?\n"
            "Plants use sunlight to make food.\n\n"
            "Q2. What is gravity?\n"
            "Force that pulls objects down."
        )
        results = service.detect_questions(text)
        assert len(results) == 2
        assert results[0].question_id == "Q1"
        assert results[1].question_id == "Q2"

    def test_detects_question_word_pattern(self, service):
        text = (
            "Question 1: Define osmosis.\n"
            "Movement of water through membrane.\n\n"
            "Question 2: What is diffusion?\n"
            "Spreading of particles from high to low."
        )
        results = service.detect_questions(text)
        assert len(results) == 2

    def test_detects_parenthesized_numbers(self, service):
        text = (
            "1) Explain the water cycle.\n"
            "Water evaporates and condenses.\n\n"
            "2) What causes rain?\n"
            "Condensation of water vapor."
        )
        results = service.detect_questions(text)
        assert len(results) == 2

    def test_detects_dot_numbered(self, service):
        text = (
            "1. What is DNA?\n"
            "A molecule that carries genetic info.\n\n"
            "2. What are chromosomes?\n"
            "Thread-like structures in cells."
        )
        results = service.detect_questions(text)
        assert len(results) == 2

    def test_single_block_fallback(self, service):
        text = "Plants use sunlight to produce food through photosynthesis."
        results = service.detect_questions(text)
        assert len(results) == 1
        assert results[0].question_id == "Q1"
        assert results[0].answer_text == text.strip()

    def test_empty_text_returns_empty(self, service):
        results = service.detect_questions("")
        assert results == []

    def test_whitespace_only_returns_empty(self, service):
        results = service.detect_questions("   \n  ")
        assert results == []

    def test_returns_detected_question_objects(self, service):
        text = "Q1. Test?\nAnswer here."
        results = service.detect_questions(text)
        assert isinstance(results[0], DetectedQuestion)

    def test_answer_text_extracted(self, service):
        text = (
            "Q1. What is photosynthesis?\n"
            "Plants use sunlight to make food and oxygen.\n\n"
            "Q2. What is gravity?\n"
            "Gravity pulls things down."
        )
        results = service.detect_questions(text)
        assert "sunlight" in results[0].answer_text
        assert "gravity" in results[1].answer_text.lower() or "pulls" in results[1].answer_text.lower()


class TestExtractQuestionsOnly:
    def test_extracts_only_questions(self, service):
        text = (
            "Q1. What is photosynthesis?\n"
            "Q2. What is gravity?\n"
            "Q3. Describe the water cycle."
        )
        results = service.extract_questions_only(text)
        assert len(results) == 3
        assert all("question_id" in r and "question" in r for r in results)

    def test_returns_list_of_dicts(self, service):
        text = "Q1. Test question?"
        results = service.extract_questions_only(text)
        assert isinstance(results, list)
        assert isinstance(results[0], dict)
