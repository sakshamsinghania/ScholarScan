"""Tests for tier-aware ConceptCoverageScorer."""

import os
import sys

import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.similarity import (
    ConceptCoverageScorer,
    ConceptCoverageResult,
    TieredReference,
)


def _fitted_vectorizer(*texts: str) -> TfidfVectorizer:
    v = TfidfVectorizer(ngram_range=(1, 2), max_features=5000)
    v.fit_transform(list(texts))
    return v


def _tiered(core, supporting=None, extended=None, flat=""):
    return TieredReference(
        core=core,
        supporting=supporting or [],
        extended=extended or [],
        flat_text=flat or ". ".join(core),
        raw_llm_response="",
    )


class TestTieredAllCoreMatched:
    def test_full_core_no_supporting_equals_one(self):
        v = _fitted_vectorizer("photosynthesis chloroplast sunlight")
        scorer = ConceptCoverageScorer(v, None)
        tiered = _tiered(["photosynthesis", "chloroplast", "sunlight"])
        result = scorer.score(
            "", "photosynthesis chloroplast sunlight",
            tiered=tiered,
        )
        assert result.coverage_ratio == 1.0
        assert result.core_recall == 1.0
        assert result.supporting_bonus == 0.0

    def test_full_core_half_supporting_capped_at_one(self):
        v = _fitted_vectorizer("photosynthesis chloroplast glucose carbon")
        scorer = ConceptCoverageScorer(v, None)
        tiered = _tiered(
            ["photosynthesis", "chloroplast"],
            ["glucose", "carbon"],
        )
        result = scorer.score(
            "", "photosynthesis chloroplast glucose",
            tiered=tiered,
        )
        assert result.coverage_ratio == 1.0
        assert result.core_recall == 1.0


class TestTieredPartialCore:
    def test_half_core_full_supporting(self):
        v = _fitted_vectorizer("photosynthesis chloroplast glucose carbon")
        scorer = ConceptCoverageScorer(v, None)
        tiered = _tiered(
            ["photosynthesis", "chloroplast"],
            ["glucose", "carbon"],
        )
        result = scorer.score(
            "", "photosynthesis glucose carbon",
            tiered=tiered,
        )
        assert 0.55 <= result.coverage_ratio <= 0.75
        assert 0.3 <= result.core_recall <= 0.7
        assert result.supporting_bonus > 0.0

    def test_zero_core_full_supporting(self):
        v = _fitted_vectorizer("photosynthesis chloroplast glucose")
        scorer = ConceptCoverageScorer(v, None)
        tiered = _tiered(
            ["photosynthesis", "chloroplast"],
            ["glucose"],
        )
        result = scorer.score(
            "", "glucose",
            tiered=tiered,
        )
        assert result.core_recall == 0.0
        assert result.coverage_ratio <= 0.15
        assert result.supporting_bonus > 0.0


class TestTieredEmptySupporting:
    def test_no_supporting_no_bonus_explosion(self):
        v = _fitted_vectorizer("photosynthesis chloroplast")
        scorer = ConceptCoverageScorer(v, None)
        tiered = _tiered(["photosynthesis", "chloroplast"], [])
        result = scorer.score(
            "", "photosynthesis",
            tiered=tiered,
        )
        assert result.supporting_bonus == 0.0
        assert 0.0 < result.coverage_ratio < 1.0


class TestTieredMissingSeparation:
    def test_missing_concepts_only_core(self):
        v = _fitted_vectorizer("photosynthesis chloroplast glucose")
        scorer = ConceptCoverageScorer(v, None)
        tiered = _tiered(
            ["photosynthesis", "chloroplast"],
            ["glucose"],
        )
        result = scorer.score("", "nothing relevant", tiered=tiered)
        core_missing_phrases = {mc.phrase for mc in result.missing_concepts}
        enrichment_phrases = {mc.phrase for mc in result.enrichment_suggestions}
        assert "photosynthesis" in core_missing_phrases
        assert "chloroplast" in core_missing_phrases
        assert "glucose" in enrichment_phrases
        assert "glucose" not in core_missing_phrases


class TestTieredLegacyFallback:
    def test_none_tiered_uses_legacy(self):
        v = _fitted_vectorizer("photosynthesis plant sunlight")
        scorer = ConceptCoverageScorer(v, None)
        result = scorer.score(
            "photosynthesis plant sunlight",
            "photosynthesis plant sunlight",
            tiered=None,
        )
        assert result.coverage_ratio > 0.0
        assert result.core_recall == 0.0
        assert result.tier_map == {}

    def test_empty_core_tiered_uses_legacy(self):
        v = _fitted_vectorizer("photosynthesis plant sunlight")
        scorer = ConceptCoverageScorer(v, None)
        tiered = _tiered([], ["bonus"])
        result = scorer.score(
            "photosynthesis plant sunlight",
            "photosynthesis plant sunlight",
            tiered=tiered,
        )
        assert result.coverage_ratio > 0.0
        assert result.core_recall == 0.0
        assert result.tier_map == {}


class TestTieredTierMap:
    def test_tier_map_populated(self):
        v = _fitted_vectorizer("photosynthesis glucose")
        scorer = ConceptCoverageScorer(v, None)
        tiered = _tiered(["photosynthesis"], ["glucose"])
        result = scorer.score("", "photosynthesis glucose", tiered=tiered)
        assert result.tier_map["photosynthesis"] == "core"
        assert result.tier_map["glucose"] == "supporting"


class TestTieredBonusCap:
    def test_custom_bonus_cap(self):
        v = _fitted_vectorizer("photosynthesis chloroplast glucose carbon")
        scorer = ConceptCoverageScorer(v, None)
        tiered = _tiered(
            ["photosynthesis", "chloroplast"],
            ["glucose", "carbon"],
        )
        result_low = scorer.score(
            "", "photosynthesis glucose carbon",
            tiered=tiered,
            supporting_bonus_cap=0.05,
        )
        result_high = scorer.score(
            "", "photosynthesis glucose carbon",
            tiered=tiered,
            supporting_bonus_cap=0.25,
        )
        assert result_high.coverage_ratio >= result_low.coverage_ratio
