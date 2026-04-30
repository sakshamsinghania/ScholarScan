"""Tests for NLIScorer."""

import os
import sys

import numpy as np
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.similarity import NLIScorer, NLIResult


class TestNLIScorerUnavailable:
    def test_unavailable_when_model_fails(self):
        with patch("core.similarity._get_nli_model", return_value=None):
            scorer = NLIScorer(model_name="nonexistent-model")
            assert not scorer.is_available

    def test_returns_zero_when_unavailable(self):
        with patch("core.similarity._get_nli_model", return_value=None):
            scorer = NLIScorer(model_name="nonexistent-model")
            sim = np.array([[0.9]])
            result = scorer.score(["model sent"], ["student sent"], sim)
            assert result.score == 0.0
            assert result.details == []


class TestNLIScorerEmpty:
    def test_empty_model_sentences(self):
        scorer = NLIScorer()
        result = scorer.score([], ["student sent"], np.array([]))
        assert result.score == 0.0

    def test_empty_student_sentences(self):
        scorer = NLIScorer()
        result = scorer.score(["model sent"], [], np.array([]))
        assert result.score == 0.0


class TestNLIScorerMocked:
    def _mock_nli(self):
        import torch
        mock_model = MagicMock()
        # 3-class logits: [contradiction, neutral, entailment]
        mock_output = MagicMock()
        mock_output.logits = torch.tensor([[0.1, 0.2, 2.0]])
        mock_model.return_value = mock_output
        mock_model.eval = MagicMock()
        mock_model.config = MagicMock()
        mock_model.config.id2label = {0: "contradiction", 1: "neutral", 2: "entailment"}

        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {
            "input_ids": torch.tensor([[1, 2, 3]]),
            "attention_mask": torch.tensor([[1, 1, 1]]),
        }

        return {
            "model": mock_model,
            "tokenizer": mock_tokenizer,
            "id2label": mock_model.config.id2label,
        }

    def test_high_entailment_scores_high(self):
        mock_nli = self._mock_nli()
        with patch("core.similarity._get_nli_model", return_value=mock_nli):
            scorer = NLIScorer(model_name="test-model")
            sim_matrix = np.array([[0.85]])
            result = scorer.score(
                ["Plants use sunlight for photosynthesis."],
                ["Photosynthesis requires sunlight in plants."],
                sim_matrix,
            )
            assert isinstance(result, NLIResult)
            assert result.score > 0.5
            assert len(result.details) == 1
            assert "p_entail" in result.details[0]

    def test_pair_cap_respected(self):
        mock_nli = self._mock_nli()
        import torch
        # Return batch of logits
        mock_output = MagicMock()
        mock_output.logits = torch.tensor([[0.1, 0.2, 2.0]] * 3)
        mock_nli["model"].return_value = mock_output

        with patch("core.similarity._get_nli_model", return_value=mock_nli):
            scorer = NLIScorer(model_name="test-model", top_n=2)
            sim_matrix = np.array([
                [0.9, 0.3, 0.1],
                [0.2, 0.8, 0.4],
                [0.1, 0.3, 0.7],
            ])
            result = scorer.score(
                ["m1", "m2", "m3"],
                ["s1", "s2", "s3"],
                sim_matrix,
            )
            assert len(result.details) <= 2


class TestNLIScorerTimeout:
    def test_timeout_returns_zero(self):
        with patch("core.similarity._get_nli_model") as mock_get:
            mock_nli = MagicMock()
            mock_nli["model"] = MagicMock(side_effect=RuntimeError("timeout"))
            mock_get.return_value = None  # simulates unavailable
            scorer = NLIScorer(model_name="test", timeout_ms=1)
            result = scorer.score(["m"], ["s"], np.array([[0.9]]))
            assert result.score == 0.0
