"""Tests for compute_similarity response contract — legacy and V2 keys."""

import os
import sys

import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.similarity import compute_similarity


class _UnavailableSBERT:
    is_available = False
    _model = None

    def compute(self, student_text: str, model_text: str) -> float:
        return 0.0


class _MockSBERT:
    is_available = True

    def __init__(self):
        self._model = MagicMock()

        def _encode(texts, convert_to_tensor=True, batch_size=32):
            import torch
            if isinstance(texts, str):
                return torch.randn(384)
            return torch.randn(len(texts), 384)

        self._model.encode = _encode

    def compute(self, student_text: str, model_text: str) -> float:
        return 0.65

    def embed(self, text: str):
        import torch
        return torch.randn(384)


LEGACY_KEYS = {"tfidf_score", "sbert_score", "combined_score", "keyword_overlap", "missing_keywords"}

V2_KEYS = {
    "concept_coverage", "matched_concepts", "missing_concepts",
    "sentence_similarity", "sentence_similarity_precision",
    "entailment_score", "nli_details", "component_weights",
    "core_recall", "supporting_bonus", "enrichment_suggestions", "tier_map",
}


class TestLegacyContract:
    def test_legacy_keys_present(self):
        result = compute_similarity(
            student_tfidf="plant sunlight food",
            model_tfidf="photosynthesis plant sunlight chlorophyll",
            student_sbert="Plants use sunlight to make food.",
            model_sbert="Photosynthesis lets plants use sunlight.",
            sbert_model=_UnavailableSBERT(),
            scoring_v2=False,
        )
        for key in LEGACY_KEYS:
            assert key in result, f"Missing legacy key: {key}"

    def test_legacy_types(self):
        result = compute_similarity(
            student_tfidf="plant sunlight",
            model_tfidf="photosynthesis plant",
            student_sbert="Plants use sunlight.",
            model_sbert="Photosynthesis uses sunlight.",
            sbert_model=_UnavailableSBERT(),
            scoring_v2=False,
        )
        assert isinstance(result["tfidf_score"], float)
        assert isinstance(result["sbert_score"], float)
        assert isinstance(result["combined_score"], float)
        assert isinstance(result["keyword_overlap"], float)
        assert isinstance(result["missing_keywords"], list)

    def test_combined_equals_tfidf_when_sbert_unavailable(self):
        result = compute_similarity(
            student_tfidf="photosynthesis plant sunlight",
            model_tfidf="photosynthesis plant sunlight chlorophyll",
            student_sbert="Plants use sunlight to make food.",
            model_sbert="Photosynthesis uses sunlight.",
            sbert_model=_UnavailableSBERT(),
            scoring_v2=False,
        )
        assert result["sbert_score"] == 0.0
        assert result["combined_score"] == result["tfidf_score"]

    def test_scores_in_range(self):
        result = compute_similarity(
            student_tfidf="plant sunlight glucose",
            model_tfidf="photosynthesis plant sunlight",
            student_sbert="Plants make food with sunlight.",
            model_sbert="Photosynthesis produces glucose.",
            sbert_model=_UnavailableSBERT(),
            scoring_v2=False,
        )
        for key in ("tfidf_score", "sbert_score", "combined_score", "keyword_overlap"):
            assert 0.0 <= result[key] <= 1.0, f"{key} out of range: {result[key]}"


class TestV2Contract:
    def test_v2_keys_present(self):
        result = compute_similarity(
            student_tfidf="plant sunlight food",
            model_tfidf="photosynthesis plant sunlight chlorophyll",
            student_sbert="Plants use sunlight to make food.",
            model_sbert="Photosynthesis lets plants produce glucose.",
            sbert_model=_MockSBERT(),
            scoring_v2=True,
            sentence_sim_enabled=True,
            nli_enabled=False,
        )
        for key in LEGACY_KEYS | V2_KEYS:
            assert key in result, f"Missing key: {key}"

    def test_v2_types(self):
        result = compute_similarity(
            student_tfidf="plant sunlight food",
            model_tfidf="photosynthesis plant sunlight",
            student_sbert="Plants use sunlight to make food.",
            model_sbert="Photosynthesis produces glucose.",
            sbert_model=_MockSBERT(),
            scoring_v2=True,
            sentence_sim_enabled=True,
            nli_enabled=False,
        )
        assert isinstance(result["concept_coverage"], float)
        assert isinstance(result["matched_concepts"], list)
        assert isinstance(result["missing_concepts"], list)
        assert isinstance(result["sentence_similarity"], float)
        assert isinstance(result["sentence_similarity_precision"], float)
        assert result["entailment_score"] is None  # NLI disabled
        assert result["nli_details"] is None
        assert isinstance(result["component_weights"], dict)

    def test_legacy_keys_still_present_in_v2(self):
        result = compute_similarity(
            student_tfidf="plant sunlight",
            model_tfidf="photosynthesis plant",
            student_sbert="Plants use sunlight.",
            model_sbert="Photosynthesis uses sunlight.",
            sbert_model=_MockSBERT(),
            scoring_v2=True,
            nli_enabled=False,
        )
        for key in LEGACY_KEYS:
            assert key in result, f"Legacy key missing in V2: {key}"

    def test_combined_score_in_range_v2(self):
        result = compute_similarity(
            student_tfidf="plant sunlight glucose",
            model_tfidf="photosynthesis plant sunlight",
            student_sbert="Plants make food with sunlight.",
            model_sbert="Photosynthesis produces glucose.",
            sbert_model=_MockSBERT(),
            scoring_v2=True,
            nli_enabled=False,
        )
        assert 0.0 <= result["combined_score"] <= 1.0

    def test_component_weights_sum_to_one(self):
        result = compute_similarity(
            student_tfidf="plant food",
            model_tfidf="photosynthesis plant",
            student_sbert="Plants use sunlight.",
            model_sbert="Photosynthesis uses sunlight.",
            sbert_model=_MockSBERT(),
            scoring_v2=True,
            nli_enabled=False,
        )
        total = sum(result["component_weights"].values())
        assert abs(total - 1.0) < 0.01, f"Component weights sum to {total}, expected ~1.0"


class TestV2FallbackToLegacy:
    def test_v2_disabled_uses_legacy_formula(self):
        result = compute_similarity(
            student_tfidf="plant sunlight",
            model_tfidf="photosynthesis plant",
            student_sbert="Plants use sunlight.",
            model_sbert="Photosynthesis uses sunlight.",
            sbert_model=_UnavailableSBERT(),
            scoring_v2=False,
        )
        assert "concept_coverage" not in result
        assert "sentence_similarity" not in result

    def test_sbert_unavailable_v2_falls_back(self):
        result = compute_similarity(
            student_tfidf="plant sunlight",
            model_tfidf="photosynthesis plant",
            student_sbert="Plants use sunlight.",
            model_sbert="Photosynthesis uses sunlight.",
            sbert_model=_UnavailableSBERT(),
            scoring_v2=True,
        )
        assert result["combined_score"] == result["tfidf_score"]


class TestDebugMode:
    def test_debug_key_present_when_enabled(self):
        result = compute_similarity(
            student_tfidf="plant sunlight",
            model_tfidf="photosynthesis plant",
            student_sbert="Plants use sunlight.",
            model_sbert="Photosynthesis uses sunlight.",
            sbert_model=_MockSBERT(),
            debug=True,
            scoring_v2=True,
            nli_enabled=False,
        )
        assert "debug" in result
        assert "concept" in result["debug"]
        assert "sentence" in result["debug"]
        assert "nli" in result["debug"]
        assert "component_weights" in result["debug"]
        assert "timings" in result["debug"]

    def test_no_debug_key_when_disabled(self):
        result = compute_similarity(
            student_tfidf="plant sunlight",
            model_tfidf="photosynthesis plant",
            student_sbert="Plants use sunlight.",
            model_sbert="Photosynthesis uses sunlight.",
            sbert_model=_MockSBERT(),
            debug=False,
            scoring_v2=True,
            nli_enabled=False,
        )
        assert "debug" not in result


class TestTieredReferenceContract:
    def test_tiered_keys_present_when_tiered(self):
        from core.similarity import TieredReference
        tiered = TieredReference(
            core=["photosynthesis", "chloroplast"],
            supporting=["glucose"],
            extended=[],
            flat_text="Photosynthesis occurs in chloroplasts.",
            raw_llm_response="",
        )
        result = compute_similarity(
            student_tfidf="photosynthesis chloroplast",
            model_tfidf="photosynthesis chloroplast glucose",
            student_sbert="Photosynthesis in chloroplasts.",
            model_sbert="Photosynthesis occurs in chloroplasts.",
            sbert_model=_MockSBERT(),
            scoring_v2=True,
            nli_enabled=False,
            tiered_reference=tiered,
        )
        assert "core_recall" in result
        assert "supporting_bonus" in result
        assert "enrichment_suggestions" in result
        assert "tier_map" in result
        assert isinstance(result["core_recall"], float)
        assert isinstance(result["tier_map"], dict)

    def test_tiered_keys_present_without_tiered(self):
        result = compute_similarity(
            student_tfidf="plant sunlight",
            model_tfidf="photosynthesis plant",
            student_sbert="Plants use sunlight.",
            model_sbert="Photosynthesis uses sunlight.",
            sbert_model=_MockSBERT(),
            scoring_v2=True,
            nli_enabled=False,
        )
        assert result["core_recall"] == 0.0
        assert result["supporting_bonus"] == 0.0
        assert result["enrichment_suggestions"] == []
        assert result["tier_map"] == {}
