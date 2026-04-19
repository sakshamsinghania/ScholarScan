"""Tests for ResultStorageService — in-memory assessment result store."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.result_storage_service import ResultStorageService

@pytest.fixture
def store():
    return ResultStorageService()

@pytest.fixture
def sample_result():
    return {
        "extracted_text": "Plants make food",
        "cleaned_text": "plant make food",
        "tfidf_score": 0.52,
        "sbert_score": 0.73,
        "similarity_score": 0.67,
        "keyword_overlap": 0.60,
        "missing_keywords": ["chlorophyll"],
        "marks": 7.5,
        "max_marks": 10,
        "grade": "B",
        "feedback": "Good answer.",
        "assessed_at": "2026-04-05T01:00:00",
        "question_id": "Q1",
        "student_id": "student_01",
    }


class TestStore:
    def test_starts_empty(self, store):
        assert store.get_all() == []

    def test_store_adds_result(self, store, sample_result):
        store.store(sample_result)
        assert len(store.get_all()) == 1

    def test_stored_result_has_id(self, store, sample_result):
        store.store(sample_result)
        result = store.get_all()[0]
        assert "id" in result

    def test_multiple_stores_accumulate(self, store, sample_result):
        store.store(sample_result)
        store.store(sample_result)
        assert len(store.get_all()) == 2

    def test_get_all_returns_copies(self, store, sample_result):
        store.store(sample_result)
        results = store.get_all()
        results.clear()
        assert len(store.get_all()) == 1

    def test_evicts_oldest_results_when_capacity_is_exceeded(self, sample_result):
        store = ResultStorageService(max_entries=2)

        store.store({**sample_result, "student_id": "student_01"})
        store.store({**sample_result, "student_id": "student_02"})
        store.store({**sample_result, "student_id": "student_03"})

        results = store.get_all()
        assert len(results) == 2
        assert [result["student_id"] for result in results] == ["student_02", "student_03"]


class TestFiltering:
    def test_filter_by_student_id(self, store, sample_result):
        store.store(sample_result)
        other = {**sample_result, "student_id": "student_02"}
        store.store(other)

        filtered = store.get_filtered(student_id="student_01")
        assert len(filtered) == 1
        assert filtered[0]["student_id"] == "student_01"

    def test_filter_by_question_id(self, store, sample_result):
        store.store(sample_result)
        other = {**sample_result, "question_id": "Q2"}
        store.store(other)

        filtered = store.get_filtered(question_id="Q1")
        assert len(filtered) == 1

    def test_filter_by_both(self, store, sample_result):
        store.store(sample_result)
        other = {**sample_result, "student_id": "student_02", "question_id": "Q2"}
        store.store(other)

        filtered = store.get_filtered(student_id="student_01", question_id="Q1")
        assert len(filtered) == 1

    def test_filter_no_match_returns_empty(self, store, sample_result):
        store.store(sample_result)
        assert store.get_filtered(student_id="nonexistent") == []
