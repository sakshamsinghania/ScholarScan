"""Tests for similarity scoring and offline SBERT fallback behavior."""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.similarity import SBERTSimilarity, compute_similarity


class TestSBERTSimilarityFallback:
    def test_resolves_sentence_transformers_cache_alias(self, monkeypatch, tmp_path):
        modules_path = tmp_path / "modules.json"
        modules_path.write_text("{}", encoding="utf-8")
        loaded_paths: list[str] = []

        class DummySentenceTransformer:
            def __init__(self, model_path: str):
                loaded_paths.append(model_path)

        def cache_lookup(model_name: str, filename: str):
            if model_name == "sentence-transformers/all-MiniLM-L6-v2":
                return str(modules_path)
            return None

        monkeypatch.setattr("core.similarity.try_to_load_from_cache", cache_lookup)
        monkeypatch.setattr("core.similarity.SentenceTransformer", DummySentenceTransformer)

        model = SBERTSimilarity("all-MiniLM-L6-v2")

        assert model.is_available is True
        assert loaded_paths == [str(Path(modules_path).parent)]

    def test_bootstraps_model_from_hub_when_cache_is_missing(self, monkeypatch):
        load_calls: list[str] = []

        def cache_lookup(model_name: str, filename: str):
            return None

        class DummySentenceTransformer:
            def __init__(self, model_path: str):
                load_calls.append(model_path)

        monkeypatch.setattr("core.similarity.try_to_load_from_cache", cache_lookup)
        monkeypatch.setattr("core.similarity.SentenceTransformer", DummySentenceTransformer)

        model = SBERTSimilarity("all-MiniLM-L6-v2")

        assert model.is_available is True
        assert load_calls == ["all-MiniLM-L6-v2"]

    def test_marks_model_unavailable_when_local_load_fails(self, monkeypatch):
        def raise_missing_model(*args, **kwargs):
            raise OSError("model not cached")

        def raise_bootstrap_failure(*args, **kwargs):
            raise OSError("download failed")

        monkeypatch.setattr("core.similarity.try_to_load_from_cache", raise_missing_model)
        monkeypatch.setattr("core.similarity.SentenceTransformer", raise_bootstrap_failure)

        model = SBERTSimilarity("all-MiniLM-L6-v2")

        assert model.is_available is False
        assert model.compute("student answer", "model answer") == 0.0


class TestComputeSimilarityFallback:
    class _UnavailableSBERT:
        is_available = False

        def compute(self, student_text: str, model_text: str) -> float:
            return 0.0

    def test_falls_back_to_tfidf_when_sbert_is_unavailable(self):
        result = compute_similarity(
            student_tfidf="photosynthesis plant sunlight",
            model_tfidf="photosynthesis plant sunlight chlorophyll",
            student_sbert="Plants use sunlight to make food.",
            model_sbert="Photosynthesis lets plants use sunlight to produce food.",
            sbert_model=self._UnavailableSBERT(),
        )

        assert result["sbert_score"] == 0.0
        assert result["combined_score"] == result["tfidf_score"]
