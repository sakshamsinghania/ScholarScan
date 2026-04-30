"""Tests for SentenceSimilarityScorer."""

import os
import sys

import numpy as np
import pytest
from unittest.mock import MagicMock, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.similarity import SentenceSimilarityScorer, SentenceSimilarityResult


class _FakeSBERT:
    is_available = False
    _model = None


class _MockSBERT:
    is_available = True

    def __init__(self):
        self._model = MagicMock()
        # encode returns stacked random vectors
        def _encode(texts, batch_size=32, convert_to_tensor=True):
            import torch
            n = len(texts)
            return torch.randn(n, 384)
        self._model.encode = _encode


class TestSentenceSimilarityEmpty:
    def test_empty_model_text(self):
        scorer = SentenceSimilarityScorer(_FakeSBERT())
        result = scorer.score("student answer here.", "", model_sentences=[], student_sentences=["student answer here."])
        assert result.score == 0.0

    def test_empty_student_text(self):
        scorer = SentenceSimilarityScorer(_FakeSBERT())
        result = scorer.score("", "model answer here.", model_sentences=["model answer here."], student_sentences=[])
        assert result.score == 0.0

    def test_both_empty(self):
        scorer = SentenceSimilarityScorer(_FakeSBERT())
        result = scorer.score("", "")
        assert result.score == 0.0


class TestSentenceSimilaritySBERTUnavailable:
    def test_returns_zero_when_sbert_down(self):
        scorer = SentenceSimilarityScorer(_FakeSBERT())
        result = scorer.score(
            "Plants make food using sunlight.",
            "Photosynthesis is the process plants use.",
        )
        assert result.score == 0.0


class TestSentenceSimilarityWithMatrix:
    def test_precomputed_matrix(self):
        scorer = SentenceSimilarityScorer(_FakeSBERT())
        sim_matrix = np.array([[0.9, 0.3], [0.4, 0.8]])
        result = scorer.score(
            "s1. s2.",
            "m1. m2.",
            model_sentences=["m1", "m2"],
            student_sentences=["s1", "s2"],
            sentence_sim_matrix=sim_matrix,
        )
        assert result.score > 0.0
        assert result.matrix is not None
        assert result.matrix.shape == (2, 2)
        assert len(result.best_matches) == 2

    def test_single_sentence_each_side(self):
        scorer = SentenceSimilarityScorer(_FakeSBERT())
        sim_matrix = np.array([[0.85]])
        result = scorer.score(
            "student text",
            "model text",
            model_sentences=["model text"],
            student_sentences=["student text"],
            sentence_sim_matrix=sim_matrix,
        )
        assert result.score == 0.85

    def test_precision_computed(self):
        scorer = SentenceSimilarityScorer(_FakeSBERT())
        sim_matrix = np.array([[0.9, 0.2], [0.1, 0.8]])
        result = scorer.score(
            "s", "m",
            model_sentences=["m1", "m2"],
            student_sentences=["s1", "s2"],
            sentence_sim_matrix=sim_matrix,
        )
        assert result.coverage_precision > 0.0


class TestSentenceSimilarityResult:
    def test_result_type(self):
        scorer = SentenceSimilarityScorer(_FakeSBERT())
        sim_matrix = np.array([[0.5]])
        result = scorer.score(
            "s", "m",
            model_sentences=["m"],
            student_sentences=["s"],
            sentence_sim_matrix=sim_matrix,
        )
        assert isinstance(result, SentenceSimilarityResult)
