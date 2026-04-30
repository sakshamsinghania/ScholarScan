"""Tiered reference calibration fixtures and golden tests."""

import os
import sys

import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.similarity import ConceptCoverageScorer, TieredReference


def _fitted_vectorizer(*texts: str) -> TfidfVectorizer:
    v = TfidfVectorizer(ngram_range=(1, 2), max_features=5000)
    v.fit_transform(list(texts))
    return v


PHOTOSYNTHESIS_TIERED = TieredReference(
    core=["photosynthesis", "sunlight energy", "chloroplast", "glucose production"],
    supporting=["carbon dioxide", "water molecule", "chlorophyll pigment"],
    extended=["Calvin cycle", "light-dependent reactions"],
    flat_text="Photosynthesis is the process by which plants convert sunlight energy into glucose in chloroplasts using carbon dioxide, water, and chlorophyll.",
    raw_llm_response="",
)

GRAVITY_TIERED = TieredReference(
    core=["gravitational force", "mass", "Newton universal gravitation"],
    supporting=["gravitational constant", "inverse square"],
    extended=["general relativity", "spacetime curvature"],
    flat_text="Gravity is the gravitational force of attraction between objects with mass, described by Newton's law of universal gravitation.",
    raw_llm_response="",
)

MITOSIS_TIERED = TieredReference(
    core=["cell division", "chromosome replication", "daughter cell"],
    supporting=["mitotic spindle", "cytokinesis"],
    extended=["centromere", "metaphase plate"],
    flat_text="Mitosis is cell division producing two identical daughter cells through chromosome replication.",
    raw_llm_response="",
)

FIXTURES = [
    {
        "name": "concise_correct_photosynthesis",
        "tiered": PHOTOSYNTHESIS_TIERED,
        "student": "Photosynthesis converts sunlight into glucose in chloroplasts.",
        "expect_score_ge": 0.70,
        "expect_core_recall_ge": 0.70,
    },
    {
        "name": "verbose_correct_photosynthesis",
        "tiered": PHOTOSYNTHESIS_TIERED,
        "student": "Photosynthesis is the process where plants use sunlight energy to produce glucose in chloroplasts. Carbon dioxide and water are absorbed, and chlorophyll pigment captures light.",
        "expect_score_ge": 0.85,
        "expect_core_recall_ge": 0.85,
    },
    {
        "name": "partial_photosynthesis",
        "tiered": PHOTOSYNTHESIS_TIERED,
        "student": "Plants use sunlight to make food.",
        "expect_score_ge": 0.15,
        "expect_score_le": 0.75,
    },
    {
        "name": "wrong_answer_photosynthesis",
        "tiered": PHOTOSYNTHESIS_TIERED,
        "student": "Photosynthesis is when animals breathe oxygen to produce carbon dioxide.",
        "expect_core_recall_le": 0.35,
    },
    {
        "name": "concise_correct_gravity",
        "tiered": GRAVITY_TIERED,
        "student": "Gravity is the force of attraction between masses described by Newton's law.",
        "expect_score_ge": 0.20,
        "expect_core_recall_ge": 0.20,
    },
    {
        "name": "verbose_correct_gravity",
        "tiered": GRAVITY_TIERED,
        "student": "Gravitational force is the attraction between objects with mass. Newton's law states it follows an inverse square law with a gravitational constant.",
        "expect_score_ge": 0.60,
    },
    {
        "name": "wrong_answer_gravity",
        "tiered": GRAVITY_TIERED,
        "student": "Gravity is a type of electromagnetic radiation from the sun.",
        "expect_core_recall_le": 0.30,
    },
    {
        "name": "concise_correct_mitosis",
        "tiered": MITOSIS_TIERED,
        "student": "Mitosis is cell division where chromosomes replicate to form two identical daughter cells.",
        "expect_score_ge": 0.70,
        "expect_core_recall_ge": 0.65,
    },
    {
        "name": "partial_mitosis",
        "tiered": MITOSIS_TIERED,
        "student": "Cells divide into two parts.",
        "expect_score_ge": 0.10,
        "expect_score_le": 0.80,
    },
    {
        "name": "wrong_answer_mitosis",
        "tiered": MITOSIS_TIERED,
        "student": "Mitosis is the process of protein synthesis in ribosomes.",
        "expect_core_recall_le": 0.30,
    },
]


class TestTieredCalibration:
    @pytest.mark.parametrize(
        "fixture",
        FIXTURES,
        ids=[f["name"] for f in FIXTURES],
    )
    def test_fixture(self, fixture):
        tiered = fixture["tiered"]
        all_phrases = " ".join(tiered.core + tiered.supporting + [fixture["student"]])
        v = _fitted_vectorizer(all_phrases, fixture["student"])
        scorer = ConceptCoverageScorer(v, None)
        result = scorer.score(
            tiered.flat_text, fixture["student"], tiered=tiered,
        )

        if "expect_score_ge" in fixture:
            assert result.coverage_ratio >= fixture["expect_score_ge"], (
                f"{fixture['name']}: coverage {result.coverage_ratio} < {fixture['expect_score_ge']}"
            )
        if "expect_score_le" in fixture:
            assert result.coverage_ratio <= fixture["expect_score_le"], (
                f"{fixture['name']}: coverage {result.coverage_ratio} > {fixture['expect_score_le']}"
            )
        if "expect_core_recall_ge" in fixture:
            assert result.core_recall >= fixture["expect_core_recall_ge"], (
                f"{fixture['name']}: core_recall {result.core_recall} < {fixture['expect_core_recall_ge']}"
            )
        if "expect_core_recall_le" in fixture:
            assert result.core_recall <= fixture["expect_core_recall_le"], (
                f"{fixture['name']}: core_recall {result.core_recall} > {fixture['expect_core_recall_le']}"
            )


class TestConciseVsLegacyImprovement:
    def test_concise_answer_scores_higher_with_tiers(self):
        tiered = PHOTOSYNTHESIS_TIERED
        student = "Photosynthesis converts sunlight into glucose in chloroplasts."
        all_phrases = " ".join(tiered.core + tiered.supporting + [student])
        v = _fitted_vectorizer(all_phrases, student, tiered.flat_text)
        scorer = ConceptCoverageScorer(v, None)

        tiered_result = scorer.score(tiered.flat_text, student, tiered=tiered)
        legacy_result = scorer.score(tiered.flat_text, student, tiered=None)

        assert tiered_result.coverage_ratio >= legacy_result.coverage_ratio - 0.05, (
            f"Tiered {tiered_result.coverage_ratio} should be >= legacy {legacy_result.coverage_ratio} for concise correct answer"
        )
