"""Tests for ConceptCoverageScorer."""

import os
import sys

import pytest
from unittest.mock import MagicMock, patch
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.similarity import ConceptCoverageScorer, ConceptCoverageResult


def _fitted_vectorizer(*texts: str) -> TfidfVectorizer:
    v = TfidfVectorizer(ngram_range=(1, 2), max_features=5000)
    v.fit_transform(list(texts))
    return v


class _FakeSBERT:
    is_available = False
    _model = None


class TestConceptCoverageEmpty:
    def test_empty_model_text(self):
        v = _fitted_vectorizer("some text")
        scorer = ConceptCoverageScorer(v, None)
        result = scorer.score("", "student wrote something")
        assert result.coverage_ratio == 0.0
        assert result.matched_concepts == []
        assert result.missing_concepts == []

    def test_empty_student_text(self):
        v = _fitted_vectorizer("photosynthesis plant sunlight")
        scorer = ConceptCoverageScorer(v, None)
        result = scorer.score("photosynthesis plant sunlight", "")
        assert result.coverage_ratio == 0.0
        assert len(result.missing_concepts) > 0

    def test_both_empty(self):
        v = TfidfVectorizer(ngram_range=(1, 2))
        scorer = ConceptCoverageScorer(v, None)
        result = scorer.score("", "")
        assert result.coverage_ratio == 0.0


class TestConceptCoverageFuzzy:
    def test_exact_match_full_coverage(self):
        model = "photosynthesis produces glucose"
        student = "photosynthesis produces glucose"
        v = _fitted_vectorizer(model, student)
        scorer = ConceptCoverageScorer(v, None)
        result = scorer.score(model, student)
        assert result.coverage_ratio > 0.0
        assert len(result.missing_concepts) == 0 or result.coverage_ratio == 1.0

    def test_fuzzy_catches_ocr_noise(self):
        model = "photosynthesis chloroplast"
        student = "photosynthsis chloroplast"
        v = _fitted_vectorizer(model, student)
        scorer = ConceptCoverageScorer(v, None)
        result = scorer.score(model, student)
        assert result.coverage_ratio > 0.5

    def test_result_type(self):
        v = _fitted_vectorizer("test data")
        scorer = ConceptCoverageScorer(v, None)
        result = scorer.score("test data", "test data")
        assert isinstance(result, ConceptCoverageResult)
        assert isinstance(result.weights, dict)


class TestConceptCoverageSBERTUnavailable:
    def test_falls_back_to_fuzzy_only(self):
        v = _fitted_vectorizer("kubernetes deployment")
        scorer = ConceptCoverageScorer(v, _FakeSBERT())
        result = scorer.score("kubernetes deployment", "kubernetes deploy")
        assert isinstance(result, ConceptCoverageResult)

    def test_no_sbert_model(self):
        v = _fitted_vectorizer("testing data")
        scorer = ConceptCoverageScorer(v, None)
        result = scorer.score("testing data", "testing data")
        assert result.coverage_ratio > 0.0


class TestConceptCoverageVectorizerNotFitted:
    def test_unfitted_vectorizer_uses_uniform_weights(self):
        v = TfidfVectorizer(ngram_range=(1, 2))
        scorer = ConceptCoverageScorer(v, None)
        result = scorer.score("some model text", "some student text")
        assert isinstance(result, ConceptCoverageResult)
        for w in result.weights.values():
            assert w == 1.0
