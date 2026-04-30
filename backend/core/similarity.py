# =============================================================================
# similarity.py — Semantic Similarity Scoring
# =============================================================================
# Dependencies:
#   sentence-transformers, scikit-learn, numpy, transformers (optional, NLI)
# =============================================================================

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

import numpy as np
from huggingface_hub import try_to_load_from_cache
from rapidfuzz import fuzz as _rfuzz
from rapidfuzz import process as _rfuzz_process
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer, util

__all__ = [
    "TFIDFSimilarity",
    "SBERTSimilarity",
    "compute_similarity",
    "extract_phrases",
    "hybrid_match",
    "keyword_score",
    "ConceptCoverageScorer",
    "SentenceSimilarityScorer",
    "NLIScorer",
    "EmbeddingContext",
    "TieredReference",
]

logger = logging.getLogger(__name__)

_FUZZY_KW_THRESHOLD: int = 85      # catches OCR noise: "vales.yaml" → "values.yaml"
_SBERT_KW_THRESHOLD: float = 0.70  # catches synonyms: "configurable" ≈ "overridable"
_MAX_SENTENCES: int = 128


def _resolve_cached_sentence_transformer_dir(model_name: str) -> str:
    """Resolve a cached or local SentenceTransformer directory."""
    expanded_model_name = os.path.expanduser(model_name)
    local_candidates = [expanded_model_name]

    if not os.path.isabs(expanded_model_name):
        local_candidates.append(os.path.abspath(expanded_model_name))

    for candidate in local_candidates:
        modules_path = os.path.join(candidate, "modules.json")
        if os.path.isdir(candidate) and os.path.exists(modules_path):
            return candidate

    cache_candidates = [model_name]
    if "/" not in model_name:
        cache_candidates.append(f"sentence-transformers/{model_name}")

    for cache_name in cache_candidates:
        cached_modules_path = try_to_load_from_cache(cache_name, "modules.json")
        if isinstance(cached_modules_path, str) and os.path.exists(cached_modules_path):
            return os.path.dirname(cached_modules_path)

    raise OSError(
        f"Model '{model_name}' is not cached locally."
        f" Checked: {', '.join(cache_candidates)}"
    )


def _load_sentence_transformer_offline(model_name: str):
    """Load a cached SentenceTransformer without making network requests."""
    model_dir = _resolve_cached_sentence_transformer_dir(model_name)

    return SentenceTransformer(model_dir)


def _load_sentence_transformer(model_name: str):
    """Load a SentenceTransformer from local cache, then bootstrap if needed."""
    try:
        return _load_sentence_transformer_offline(model_name)
    except OSError:
        logger.info(
            "SBERT model '%s' is not cached locally; attempting bootstrap download.",
            model_name,
        )
        return SentenceTransformer(model_name)


@lru_cache(maxsize=1)
def _get_nlp_model():
    """Lazy-load spaCy en_core_web_sm; returns None if model not installed."""
    try:
        import spacy
        return spacy.load("en_core_web_sm")
    except OSError:
        logger.warning(
            "spaCy en_core_web_sm not found; noun-chunk extraction disabled. "
            "Run: python -m spacy download en_core_web_sm"
        )
        return None


# --------------------------------------------------------------------------- #
#  Dataclasses for rich scoring results                                        #
# --------------------------------------------------------------------------- #

@dataclass
class MatchedConcept:
    phrase: str
    weight: float
    match_type: Literal["exact", "fuzzy", "semantic"]
    matched_student_phrase: str
    similarity: float


@dataclass
class MissingConcept:
    phrase: str
    weight: float
    best_candidate: str | None
    best_similarity: float


@dataclass
class TieredReference:
    core: list[str]
    supporting: list[str]
    extended: list[str]
    flat_text: str
    raw_llm_response: str


@dataclass
class ConceptCoverageResult:
    coverage_ratio: float
    matched_concepts: list[MatchedConcept]
    missing_concepts: list[MissingConcept]
    weights: dict[str, float]
    core_recall: float = 0.0
    supporting_bonus: float = 0.0
    enrichment_suggestions: list[MissingConcept] = field(default_factory=list)
    tier_map: dict[str, str] = field(default_factory=dict)


@dataclass
class SentenceSimilarityResult:
    score: float
    matrix: np.ndarray | None = None
    best_matches: list[tuple[str, str, float]] = field(default_factory=list)
    coverage_precision: float = 0.0


@dataclass
class NLIResult:
    score: float
    details: list[dict] = field(default_factory=list)


@dataclass
class EmbeddingContext:
    """Per-call cache for shared embeddings and extracted data."""
    model_phrases: list[str] = field(default_factory=list)
    student_phrases: list[str] = field(default_factory=list)
    model_sentences: list[str] = field(default_factory=list)
    student_sentences: list[str] = field(default_factory=list)
    phrase_sim_matrix: np.ndarray | None = None
    sentence_embeddings_model: np.ndarray | None = None
    sentence_embeddings_student: np.ndarray | None = None
    sentence_sim_matrix: np.ndarray | None = None


# --------------------------------------------------------------------------- #
#  Phrase extraction                                                           #
# --------------------------------------------------------------------------- #

def extract_phrases(text: str, nlp) -> list[str]:
    """Extract noun chunks from text, preserving multi-word concepts as units.

    "custom resource definition" stays one phrase rather than three tokens.
    Falls back to lemmatized non-stop tokens when spaCy is unavailable or
    produces no chunks (e.g. very short input).
    """
    if nlp is None:
        return list(dict.fromkeys(t.lower() for t in text.split() if len(t) > 1))

    doc = nlp(text)
    phrases = [
        chunk.lemma_.lower().strip()
        for chunk in doc.noun_chunks
        if len(chunk.text.strip()) > 1
    ]
    phrases = list(dict.fromkeys(phrases))  # deduplicate, preserve order

    if not phrases:
        phrases = list(dict.fromkeys(
            tok.lemma_.lower()
            for tok in doc
            if not tok.is_stop and not tok.is_punct and len(tok.text) > 1
        ))

    return phrases


# --------------------------------------------------------------------------- #
#  Phrase cleaning and filtering (output layer only)                           #
# --------------------------------------------------------------------------- #

_GENERIC_SINGLE_WORDS = frozenset({
    "file", "use", "data", "way", "thing", "type", "kind", "form",
    "part", "case", "example", "item", "point", "set", "lot",
    "number", "value", "name", "list", "group", "level", "area",
})


def clean_phrase(phrase: str) -> str:
    words = phrase.split()
    words = list(dict.fromkeys(words))
    words = words[:5]
    return " ".join(words)


def is_valid_phrase(phrase: str) -> bool:
    words = phrase.split()
    if not words or len(words) > 6:
        return False
    if len(words) == 1:
        w = words[0]
        return "." in w or "-" in w or "_" in w or len(w) >= 6
    return not all(w in _GENERIC_SINGLE_WORDS for w in words)


def dedupe_phrases(
    phrases: list[str],
    sbert_model: SBERTSimilarity | None = None,
    threshold: float = 0.85,
) -> list[str]:
    if len(phrases) <= 1:
        return phrases

    if sbert_model is not None and getattr(sbert_model, "is_available", False):
        try:
            embs = sbert_model._model.encode(phrases, convert_to_tensor=True)
            sim = util.cos_sim(embs, embs).cpu().numpy()
            unique: list[str] = []
            used: set[int] = set()
            for i, p in enumerate(phrases):
                if i in used:
                    continue
                unique.append(p)
                for j in range(i + 1, len(phrases)):
                    if sim[i, j] > threshold:
                        used.add(j)
            return unique
        except Exception:
            pass

    unique = []
    for p in phrases:
        if not any(p in u or u in p for u in unique):
            unique.append(p)
    return unique


def _clean_output_phrases(
    phrases: list[str],
    sbert_model: SBERTSimilarity | None = None,
) -> list[str]:
    cleaned = [clean_phrase(p) for p in phrases]
    filtered = [p for p in cleaned if is_valid_phrase(p)]
    return dedupe_phrases(filtered, sbert_model)


def _format_feedback(
    covered: list[str],
    missing: list[str],
    max_items: int = 5,
    enrichment: list[str] | None = None,
) -> dict:
    top_covered = covered[:max_items]
    top_missing = missing[:max_items]
    top_enrichment = (enrichment or [])[:max_items]
    covered_part = (
        "You covered: " + ", ".join(top_covered) + "."
        if top_covered else "No key concepts covered."
    )
    missing_part = (
        " Missing (required): " + ", ".join(top_missing) + "."
        if top_missing else ""
    )
    enrichment_part = (
        " Could strengthen with: " + ", ".join(top_enrichment) + "."
        if top_enrichment else ""
    )
    return {
        "covered": top_covered,
        "missing": top_missing,
        "enrichment": top_enrichment,
        "summary": covered_part + missing_part + enrichment_part,
    }


def _compute_phrase_weights(
    phrases: list[str], vectorizer: TfidfVectorizer
) -> dict[str, float]:
    """Map each model phrase to a TF-IDF importance weight in [0.3, 1.0].

    Phrases absent from the fitted vocabulary still receive a floor weight (0.3)
    so they are not silently ignored during scoring.
    """
    if not phrases:
        return {}

    try:
        vectorizer.get_feature_names_out()
    except Exception:
        return {p: 1.0 for p in phrases}

    try:
        doc = " ".join(phrases)
        vec_scores = vectorizer.transform([doc]).toarray()[0]
        feature_names = vectorizer.get_feature_names_out()
        fw: dict[str, float] = dict(zip(feature_names, vec_scores))

        raw: dict[str, float] = {}
        for phrase in phrases:
            tokens = phrase.split()
            bigrams = [f"{tokens[i]} {tokens[i + 1]}" for i in range(len(tokens) - 1)]
            scores = [fw.get(c, 0.0) for c in tokens + bigrams]
            raw[phrase] = max(scores) if scores else 0.0

        max_w = max(raw.values()) or 1.0
        return {p: round(0.3 + 0.7 * (raw[p] / max_w), 4) for p in phrases}

    except Exception as exc:
        logger.debug("TF-IDF weight extraction failed: %s", exc)
        return {p: 1.0 for p in phrases}


# --------------------------------------------------------------------------- #
#  Hybrid matching                                                             #
# --------------------------------------------------------------------------- #

def hybrid_match(
    model_phrase: str,
    student_phrases: list[str],
    sbert_row=None,
    fuzzy_threshold: int = _FUZZY_KW_THRESHOLD,
    sbert_threshold: float = _SBERT_KW_THRESHOLD,
) -> bool:
    """Return True if model_phrase matches any student phrase.

    Two-stage pipeline:
      1. Fuzzy (token_set_ratio): handles OCR noise and minor spelling errors.
      2. Semantic (SBERT cosine): handles synonyms and paraphrases.
    `sbert_row` is a pre-computed cosine similarity row (avoid per-call encoding).
    """
    if not student_phrases:
        return False

    result = _rfuzz_process.extractOne(
        model_phrase,
        student_phrases,
        scorer=_rfuzz.token_set_ratio,
        score_cutoff=fuzzy_threshold,
    )
    if result is not None:
        return True

    if sbert_row is not None and float(sbert_row.max()) >= sbert_threshold:
        return True

    return False


def _hybrid_match_detailed(
    model_phrase: str,
    student_phrases: list[str],
    sbert_row=None,
    fuzzy_threshold: int = _FUZZY_KW_THRESHOLD,
    sbert_threshold: float = _SBERT_KW_THRESHOLD,
) -> tuple[bool, str, str, float]:
    """Like hybrid_match but returns (matched, match_type, matched_phrase, similarity)."""
    if not student_phrases:
        return False, "", "", 0.0

    result = _rfuzz_process.extractOne(
        model_phrase,
        student_phrases,
        scorer=_rfuzz.token_set_ratio,
        score_cutoff=fuzzy_threshold,
    )
    if result is not None:
        matched_phrase, score, _ = result
        if matched_phrase.lower() == model_phrase.lower():
            return True, "exact", matched_phrase, score / 100.0
        return True, "fuzzy", matched_phrase, score / 100.0

    if sbert_row is not None:
        max_idx = int(np.argmax(sbert_row))
        max_sim = float(sbert_row[max_idx])
        if max_sim >= sbert_threshold:
            return True, "semantic", student_phrases[max_idx], max_sim

    return False, "", "", 0.0


def keyword_score(
    model_phrases: list[str],
    student_phrases: list[str],
    weights: dict[str, float],
    sbert_model: SBERTSimilarity | None = None,
) -> tuple[float, list[str], list[str]]:
    """Compute weighted keyword overlap via hybrid fuzzy + semantic matching.

    Batch-encodes all phrases in one SBERT call to avoid per-phrase overhead.
    Returns (weighted_ratio, matched_phrases, missing_phrases).
    """
    if not model_phrases:
        return 0.0, [], []

    sim_matrix = None
    if sbert_model is not None and sbert_model.is_available and student_phrases:
        try:
            all_embs = sbert_model._model.encode(
                model_phrases + student_phrases, convert_to_tensor=True
            )
            m_embs = all_embs[: len(model_phrases)]
            s_embs = all_embs[len(model_phrases):]
            sim_matrix = util.cos_sim(m_embs, s_embs)  # shape [M, S]
        except Exception as exc:
            logger.warning("Batch SBERT encoding failed in keyword_score: %s", exc)

    matched: list[str] = []
    missing: list[str] = []
    total_weight = sum(weights.values()) or 1.0
    matched_weight = 0.0

    for i, phrase in enumerate(model_phrases):
        w = weights.get(phrase, 1.0)
        sbert_row = sim_matrix[i] if sim_matrix is not None else None
        if hybrid_match(phrase, student_phrases, sbert_row=sbert_row):
            matched.append(phrase)
            matched_weight += w
        else:
            missing.append(phrase)

    ratio = round(matched_weight / total_weight, 4)
    return ratio, matched, missing


# --------------------------------------------------------------------------- #
#  ConceptCoverageScorer                                                       #
# --------------------------------------------------------------------------- #

class ConceptCoverageScorer:
    """Wraps keyword_overlap with richer, concept-level structure."""

    def __init__(
        self,
        vectorizer: TfidfVectorizer,
        sbert_model: SBERTSimilarity | None,
    ) -> None:
        self._vectorizer = vectorizer
        self._sbert = sbert_model

    def score(
        self,
        model_text: str,
        student_text: str,
        *,
        phrase_sim_matrix: np.ndarray | None = None,
        model_phrases: list[str] | None = None,
        student_phrases: list[str] | None = None,
        tiered: TieredReference | None = None,
        supporting_bonus_cap: float = 0.15,
    ) -> ConceptCoverageResult:
        nlp = _get_nlp_model()
        if student_phrases is None:
            student_phrases = extract_phrases(student_text, nlp)

        use_tiered = tiered is not None and len(tiered.core) > 0
        tier_map: dict[str, str] = {}

        if use_tiered:
            model_phrases = list(tiered.core) + list(tiered.supporting)
            for p in tiered.core:
                tier_map[p] = "core"
            for p in tiered.supporting:
                tier_map[p] = "supporting"
        elif model_phrases is None:
            model_phrases = extract_phrases(model_text, nlp)

        if not model_phrases:
            return ConceptCoverageResult(
                coverage_ratio=0.0,
                matched_concepts=[],
                missing_concepts=[],
                weights={},
            )

        weights = _compute_phrase_weights(model_phrases, self._vectorizer)

        sim_matrix = phrase_sim_matrix
        if sim_matrix is None and self._sbert is not None and self._sbert.is_available and student_phrases:
            try:
                all_embs = self._sbert._model.encode(
                    model_phrases + student_phrases, convert_to_tensor=True
                )
                m_embs = all_embs[: len(model_phrases)]
                s_embs = all_embs[len(model_phrases):]
                sim_matrix = util.cos_sim(m_embs, s_embs).cpu().numpy()
            except Exception as exc:
                logger.warning("Batch SBERT encoding failed in ConceptCoverageScorer: %s", exc)

        matched_concepts: list[MatchedConcept] = []
        missing_concepts: list[MissingConcept] = []
        total_weight = sum(weights.values()) or 1.0
        matched_weight = 0.0

        for i, phrase in enumerate(model_phrases):
            w = weights.get(phrase, 1.0)
            sbert_row = sim_matrix[i] if sim_matrix is not None else None

            is_match, match_type, matched_phrase, similarity = _hybrid_match_detailed(
                phrase, student_phrases, sbert_row=sbert_row,
            )

            if is_match:
                matched_concepts.append(MatchedConcept(
                    phrase=phrase,
                    weight=w,
                    match_type=match_type,
                    matched_student_phrase=matched_phrase,
                    similarity=similarity,
                ))
                matched_weight += w
            else:
                best_candidate = None
                best_similarity = 0.0
                if sbert_row is not None and len(student_phrases) > 0:
                    max_idx = int(np.argmax(sbert_row))
                    best_similarity = float(sbert_row[max_idx])
                    best_candidate = student_phrases[max_idx]
                missing_concepts.append(MissingConcept(
                    phrase=phrase,
                    weight=w,
                    best_candidate=best_candidate,
                    best_similarity=best_similarity,
                ))

        coverage_ratio = round(matched_weight / total_weight, 4)

        core_recall = 0.0
        supporting_bonus = 0.0
        enrichment_suggestions: list[MissingConcept] = []

        if use_tiered:
            core_matched_w = sum(
                weights.get(mc.phrase, 1.0) for mc in matched_concepts
                if tier_map.get(mc.phrase) == "core"
            )
            core_total_w = sum(
                weights.get(p, 1.0) for p in model_phrases
                if tier_map.get(p) == "core"
            ) or 1.0
            core_recall = core_matched_w / core_total_w

            supp_phrases = [p for p in model_phrases if tier_map.get(p) == "supporting"]
            if supp_phrases:
                supp_matched_w = sum(
                    weights.get(mc.phrase, 1.0) for mc in matched_concepts
                    if tier_map.get(mc.phrase) == "supporting"
                )
                supp_total_w = sum(weights.get(p, 1.0) for p in supp_phrases) or 1.0
                supporting_bonus = supp_matched_w / supp_total_w

            coverage_ratio = round(
                min(1.0, core_recall + supporting_bonus_cap * supporting_bonus), 4,
            )

            core_missing = [
                mc for mc in missing_concepts if tier_map.get(mc.phrase) == "core"
            ]
            enrichment_suggestions = [
                mc for mc in missing_concepts if tier_map.get(mc.phrase) == "supporting"
            ]
            missing_concepts = core_missing

        return ConceptCoverageResult(
            coverage_ratio=coverage_ratio,
            matched_concepts=matched_concepts,
            missing_concepts=missing_concepts,
            weights=weights,
            core_recall=round(core_recall, 4),
            supporting_bonus=round(supporting_bonus, 4),
            enrichment_suggestions=enrichment_suggestions,
            tier_map=tier_map,
        )


# --------------------------------------------------------------------------- #
#  SentenceSimilarityScorer                                                    #
# --------------------------------------------------------------------------- #

class SentenceSimilarityScorer:
    """Sentence-level semantic similarity (mean-of-max recall aggregation)."""

    def __init__(self, sbert_model: SBERTSimilarity) -> None:
        self._sbert = sbert_model

    def score(
        self,
        student_text: str,
        model_text: str,
        *,
        model_sentences: list[str] | None = None,
        student_sentences: list[str] | None = None,
        sentence_sim_matrix: np.ndarray | None = None,
    ) -> SentenceSimilarityResult:
        from core.nlp import split_sentences

        if model_sentences is None:
            model_sentences = split_sentences(model_text)
        if student_sentences is None:
            student_sentences = split_sentences(student_text)

        if not model_sentences or not student_sentences:
            return SentenceSimilarityResult(score=0.0)

        model_sentences = model_sentences[:_MAX_SENTENCES]
        student_sentences = student_sentences[:_MAX_SENTENCES]

        sim_matrix = sentence_sim_matrix
        if sim_matrix is None:
            if not self._sbert.is_available:
                return SentenceSimilarityResult(score=0.0)
            try:
                all_sents = model_sentences + student_sentences
                all_embs = self._sbert._model.encode(
                    all_sents, batch_size=32, convert_to_tensor=True,
                )
                m_embs = all_embs[: len(model_sentences)]
                s_embs = all_embs[len(model_sentences):]
                sim_matrix = util.cos_sim(m_embs, s_embs).cpu().numpy()
            except Exception as exc:
                logger.warning("Sentence similarity encoding failed: %s", exc)
                return SentenceSimilarityResult(score=0.0)

        sim_matrix = np.clip(sim_matrix, 0.0, 1.0)

        # Recall: for each model sentence, best student match
        best_per_model = sim_matrix.max(axis=1)
        recall_score = float(np.mean(best_per_model))

        # Precision: for each student sentence, best model match
        best_per_student = sim_matrix.max(axis=0)
        precision_score = float(np.mean(best_per_student))

        best_matches = []
        for i, m_sent in enumerate(model_sentences):
            best_idx = int(np.argmax(sim_matrix[i]))
            best_matches.append((
                m_sent,
                student_sentences[best_idx],
                float(sim_matrix[i, best_idx]),
            ))

        return SentenceSimilarityResult(
            score=round(recall_score, 4),
            matrix=sim_matrix,
            best_matches=best_matches,
            coverage_precision=round(precision_score, 4),
        )


# --------------------------------------------------------------------------- #
#  NLI Scorer                                                                  #
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=1)
def _get_nli_model(model_name: str):
    """Lazy-load NLI cross-encoder model. Returns None on failure."""
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        import torch

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        model.eval()

        expected_labels = {"contradiction", "neutral", "entailment"}
        actual_labels = set(model.config.id2label.values())
        if not expected_labels.issubset({l.lower() for l in actual_labels}):
            logger.error(
                "NLI model label mismatch: expected %s, got %s",
                expected_labels, actual_labels,
            )
            return None

        return {"model": model, "tokenizer": tokenizer, "id2label": model.config.id2label}
    except Exception as exc:
        logger.warning("NLI model '%s' failed to load: %s", model_name, exc)
        return None


class NLIScorer:
    """Entailment scoring via NLI cross-encoder."""

    def __init__(
        self,
        model_name: str = "cross-encoder/nli-deberta-v3-base",
        top_n: int = 16,
        top_k_per_model: int = 1,
        timeout_ms: int = 4000,
    ) -> None:
        self._model_name = model_name
        self._top_n = top_n
        self._top_k = top_k_per_model
        self._timeout_ms = timeout_ms

    @property
    def is_available(self) -> bool:
        return _get_nli_model(self._model_name) is not None

    def score(
        self,
        model_sentences: list[str],
        student_sentences: list[str],
        sim_matrix: np.ndarray,
    ) -> NLIResult:
        if not model_sentences or not student_sentences:
            return NLIResult(score=0.0)

        nli = _get_nli_model(self._model_name)
        if nli is None:
            return NLIResult(score=0.0)

        import torch

        # Select top-K student sentences per model sentence by cosine
        pairs: list[tuple[int, int]] = []
        for i in range(len(model_sentences)):
            row = sim_matrix[i]
            top_indices = np.argsort(row)[::-1][: self._top_k]
            for j in top_indices:
                pairs.append((i, int(j)))

        # Deduplicate and cap
        seen = set()
        unique_pairs = []
        for p in pairs:
            if p not in seen:
                seen.add(p)
                unique_pairs.append(p)
        unique_pairs = unique_pairs[: self._top_n]

        if not unique_pairs:
            return NLIResult(score=0.0)

        model = nli["model"]
        tokenizer = nli["tokenizer"]
        id2label = nli["id2label"]

        # Build label index mapping
        label_to_idx: dict[str, int] = {}
        for idx, label in id2label.items():
            label_to_idx[label.lower()] = int(idx)

        entail_idx = label_to_idx.get("entailment", 2)
        contra_idx = label_to_idx.get("contradiction", 0)

        text_pairs = [
            (model_sentences[i], student_sentences[j]) for i, j in unique_pairs
        ]

        start = time.monotonic()
        try:
            inputs = tokenizer(
                [p[0] for p in text_pairs],
                [p[1] for p in text_pairs],
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )

            with torch.inference_mode():
                logits = model(**inputs).logits
                probs = torch.softmax(logits, dim=-1).cpu().numpy()

            elapsed_ms = (time.monotonic() - start) * 1000
            if elapsed_ms > self._timeout_ms:
                logger.warning("NLI scoring took %.0fms (limit %dms)", elapsed_ms, self._timeout_ms)

        except Exception as exc:
            logger.warning("NLI forward pass failed: %s", exc)
            return NLIResult(score=0.0)

        details = []
        weighted_scores = []
        for k, (i, j) in enumerate(unique_pairs):
            p_entail = float(probs[k, entail_idx])
            p_contra = float(probs[k, contra_idx])
            p_neutral = 1.0 - p_entail - p_contra

            # Map p_entailment - p_contradiction from [-1, 1] to [0, 1]
            pair_score = (p_entail - p_contra + 1.0) / 2.0

            cosine_weight = float(sim_matrix[i, j])
            weighted_scores.append(pair_score * cosine_weight)

            details.append({
                "model_sent": model_sentences[i],
                "student_sent": student_sentences[j],
                "p_entail": round(p_entail, 4),
                "p_neutral": round(p_neutral, 4),
                "p_contradict": round(p_contra, 4),
                "weighted_score": round(pair_score * cosine_weight, 4),
            })

        total_weight = sum(float(sim_matrix[i, j]) for i, j in unique_pairs) or 1.0
        aggregated = sum(weighted_scores) / total_weight

        return NLIResult(
            score=round(float(np.clip(aggregated, 0.0, 1.0)), 4),
            details=details,
        )


# --------------------------------------------------------------------------- #
#  Method A: TF-IDF Cosine Similarity                                         #
# --------------------------------------------------------------------------- #

class TFIDFSimilarity:
    """Computes cosine similarity between two texts using TF-IDF vectors."""

    def __init__(self) -> None:
        self._vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=5000)

    def compute(self, student_text: str, model_text: str) -> float:
        if not student_text.strip() or not model_text.strip():
            return 0.0

        tfidf_matrix = self._vectorizer.fit_transform([student_text, model_text])
        score = cosine_similarity(tfidf_matrix[0], tfidf_matrix[1])[0][0]
        return round(float(np.clip(score, 0.0, 1.0)), 4)

    def keyword_overlap(
        self,
        student_text: str,
        model_text: str,
        sbert_model: SBERTSimilarity | None = None,
    ) -> dict:
        """Hybrid keyword overlap — backward-compatible 3-key dict."""
        nlp = _get_nlp_model()
        model_phrases = extract_phrases(model_text, nlp)
        student_phrases = extract_phrases(student_text, nlp)

        if not model_phrases:
            return {"overlap_ratio": 0.0, "matched_keywords": [], "missing_keywords": []}

        weights = _compute_phrase_weights(model_phrases, self._vectorizer)
        ratio, matched, missing = keyword_score(
            model_phrases, student_phrases, weights, sbert_model=sbert_model
        )

        matched = _clean_output_phrases(matched, sbert_model)
        missing = _clean_output_phrases(missing, sbert_model)

        return {
            "overlap_ratio": ratio,
            "matched_keywords": sorted(matched),
            "missing_keywords": sorted(missing),
        }


# --------------------------------------------------------------------------- #
#  Method B: Sentence-BERT Similarity                                          #
# --------------------------------------------------------------------------- #

class SBERTSimilarity:
    """Computes semantic similarity using Sentence-BERT embeddings."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        logger.info("Loading SBERT model from local cache: %s ...", model_name)
        self._model = None
        self._model_name = model_name

        try:
            self._model = _load_sentence_transformer(model_name)
            logger.info("SBERT model ready.")
        except Exception as e:
            logger.warning(
                "SBERT model '%s' could not be loaded; semantic similarity is disabled. Error: %s",
                model_name,
                e,
            )

    @property
    def is_available(self) -> bool:
        return self._model is not None

    def embed(self, text: str):
        if self._model is None:
            raise RuntimeError(
                f"SBERT model '{self._model_name}' is not available locally."
            )
        return self._model.encode(text, convert_to_tensor=True)

    def compute(self, student_text: str, model_text: str) -> float:
        if not student_text.strip() or not model_text.strip():
            return 0.0
        if self._model is None:
            return 0.0

        emb_student = self.embed(student_text)
        emb_model = self.embed(model_text)

        score = util.cos_sim(emb_student, emb_model).item()
        return round(float(np.clip(score, 0.0, 1.0)), 4)

    def batch_compute(self, student_answers: list[str], model_answer: str) -> list[float]:
        if not model_answer.strip():
            return [0.0] * len(student_answers)
        if self._model is None:
            return [0.0] * len(student_answers)

        emb_model = self.embed(model_answer)
        emb_students = self._model.encode(student_answers, convert_to_tensor=True)

        scores = util.cos_sim(emb_students, emb_model).squeeze().tolist()

        if isinstance(scores, float):
            scores = [scores]

        return [round(float(np.clip(s, 0.0, 1.0)), 4) for s in scores]


# --------------------------------------------------------------------------- #
#  Weight redistribution helper                                                #
# --------------------------------------------------------------------------- #

def _redistribute_weights(
    base_weights: dict[str, float],
    available: dict[str, bool],
) -> dict[str, float]:
    """Redistribute unavailable component weights proportionally."""
    active = {k: v for k, v in base_weights.items() if available.get(k, True)}
    if not active:
        return base_weights

    total = sum(active.values())
    if total == 0:
        return active

    return {k: round(v / total, 4) for k, v in active.items()}


# --------------------------------------------------------------------------- #
#  Combined scorer                                                             #
# --------------------------------------------------------------------------- #

def compute_similarity(
    student_tfidf: str,
    model_tfidf: str,
    student_sbert: str,
    model_sbert: str,
    sbert_model: SBERTSimilarity,
    tfidf_weight: float = 0.3,
    sbert_weight: float = 0.7,
    debug: bool = False,
    *,
    scoring_v2: bool | None = None,
    sentence_sim_enabled: bool | None = None,
    nli_enabled: bool | None = None,
    nli_model_name: str | None = None,
    nli_top_n: int | None = None,
    nli_timeout_ms: int | None = None,
    weight_sbert: float | None = None,
    weight_sentence: float | None = None,
    weight_concept: float | None = None,
    weight_tfidf: float | None = None,
    weight_nli: float | None = None,
    tiered_reference: TieredReference | None = None,
    supporting_bonus_cap: float | None = None,
) -> dict:
    """Run TF-IDF + SBERT + (optionally) sentence, concept, NLI scoring.

    When scoring_v2=True (default from config), uses the 5-component formula.
    When False, falls back to the legacy 0.3*tfidf + 0.7*sbert formula.
    All legacy keys preserved.
    """
    # Resolve config defaults
    try:
        from config import Config
        if scoring_v2 is None:
            scoring_v2 = Config.SCORING_V2_ENABLED
        if sentence_sim_enabled is None:
            sentence_sim_enabled = Config.SENTENCE_SIM_ENABLED
        if nli_enabled is None:
            nli_enabled = Config.NLI_ENABLED
        if nli_model_name is None:
            nli_model_name = Config.NLI_MODEL_NAME
        if nli_top_n is None:
            nli_top_n = Config.NLI_TOP_N
        if nli_timeout_ms is None:
            nli_timeout_ms = Config.NLI_TIMEOUT_MS
        if weight_sbert is None:
            weight_sbert = Config.SCORE_WEIGHT_SBERT
        if weight_sentence is None:
            weight_sentence = Config.SCORE_WEIGHT_SENTENCE
        if weight_concept is None:
            weight_concept = Config.SCORE_WEIGHT_CONCEPT
        if weight_tfidf is None:
            weight_tfidf = Config.SCORE_WEIGHT_TFIDF
        if weight_nli is None:
            weight_nli = Config.SCORE_WEIGHT_NLI
        if supporting_bonus_cap is None:
            supporting_bonus_cap = getattr(Config, "SUPPORTING_BONUS_CAP", 0.15)
    except Exception:
        if scoring_v2 is None:
            scoring_v2 = True
        if sentence_sim_enabled is None:
            sentence_sim_enabled = True
        if nli_enabled is None:
            nli_enabled = False
        if nli_model_name is None:
            nli_model_name = "cross-encoder/nli-deberta-v3-base"
        if nli_top_n is None:
            nli_top_n = 16
        if nli_timeout_ms is None:
            nli_timeout_ms = 4000
        if weight_sbert is None:
            weight_sbert = 0.35
        if weight_sentence is None:
            weight_sentence = 0.25
        if weight_concept is None:
            weight_concept = 0.25
        if weight_tfidf is None:
            weight_tfidf = 0.10
        if weight_nli is None:
            weight_nli = 0.05
        if supporting_bonus_cap is None:
            supporting_bonus_cap = 0.15

    timings: dict[str, float] = {}
    t0 = time.monotonic()

    tfidf_scorer = TFIDFSimilarity()

    # Core scores (always computed)
    tfidf_score = tfidf_scorer.compute(student_tfidf, model_tfidf)
    sbert_score = sbert_model.compute(student_sbert, model_sbert)
    keyword_info = tfidf_scorer.keyword_overlap(
        student_tfidf, model_tfidf, sbert_model=sbert_model,
    )
    timings["tfidf+sbert+keyword"] = time.monotonic() - t0

    use_sbert = getattr(sbert_model, "is_available", True)

    # --- V2 scoring path ---
    concept_coverage_val: float = keyword_info["overlap_ratio"]
    sentence_sim_val: float = 0.0
    entailment_val: float | None = None
    concept_result: ConceptCoverageResult | None = None
    sentence_result: SentenceSimilarityResult | None = None
    nli_result: NLIResult | None = None

    if scoring_v2 and use_sbert:
        # Concept coverage
        t1 = time.monotonic()
        concept_scorer = ConceptCoverageScorer(tfidf_scorer._vectorizer, sbert_model)
        concept_result = concept_scorer.score(
            model_tfidf, student_tfidf,
            tiered=tiered_reference,
            supporting_bonus_cap=supporting_bonus_cap,
        )
        concept_coverage_val = concept_result.coverage_ratio
        timings["concept_coverage"] = time.monotonic() - t1

        # Sentence similarity
        if sentence_sim_enabled and sbert_model.is_available:
            t2 = time.monotonic()
            sent_scorer = SentenceSimilarityScorer(sbert_model)
            sentence_result = sent_scorer.score(student_sbert, model_sbert)
            sentence_sim_val = sentence_result.score
            timings["sentence_similarity"] = time.monotonic() - t2

        # NLI
        if (
            nli_enabled
            and sentence_result is not None
            and sentence_result.matrix is not None
            and sentence_sim_val >= 0.2
        ):
            t3 = time.monotonic()
            nli_scorer = NLIScorer(
                model_name=nli_model_name,
                top_n=nli_top_n,
                timeout_ms=nli_timeout_ms,
            )
            if nli_scorer.is_available:
                from core.nlp import split_sentences
                model_sents = split_sentences(model_sbert)[:_MAX_SENTENCES]
                student_sents = split_sentences(student_sbert)[:_MAX_SENTENCES]
                nli_result = nli_scorer.score(
                    model_sents, student_sents, sentence_result.matrix,
                )
                entailment_val = nli_result.score
            timings["nli"] = time.monotonic() - t3

    # --- Compute combined score ---
    if scoring_v2 and use_sbert:
        available = {
            "sbert": True,
            "sentence": sentence_sim_enabled and sentence_result is not None,
            "concept": True,
            "tfidf": True,
            "nli": nli_enabled and entailment_val is not None,
        }
        base_weights = {
            "sbert": weight_sbert,
            "sentence": weight_sentence,
            "concept": weight_concept,
            "tfidf": weight_tfidf,
            "nli": weight_nli,
        }
        effective_weights = _redistribute_weights(base_weights, available)

        combined = (
            effective_weights.get("sbert", 0) * sbert_score
            + effective_weights.get("sentence", 0) * sentence_sim_val
            + effective_weights.get("concept", 0) * concept_coverage_val
            + effective_weights.get("tfidf", 0) * tfidf_score
            + effective_weights.get("nli", 0) * (entailment_val or 0.0)
        )
        combined = round(float(np.clip(combined, 0.0, 1.0)), 4)
    elif use_sbert:
        combined = round(
            (tfidf_weight * tfidf_score) + (sbert_weight * sbert_score), 4,
        )
        combined = float(np.clip(combined, 0.0, 1.0))
        effective_weights = {"tfidf": tfidf_weight, "sbert": sbert_weight}
    else:
        combined = tfidf_score
        effective_weights = {"tfidf": 1.0}

    # --- Build result dict (legacy keys preserved) ---
    result: dict = {
        "tfidf_score": tfidf_score,
        "sbert_score": sbert_score,
        "combined_score": combined,
        "keyword_overlap": keyword_info["overlap_ratio"],
        "missing_keywords": keyword_info["missing_keywords"],
    }

    # V2 new keys
    if scoring_v2:
        result["concept_coverage"] = concept_coverage_val
        _matched_seen: set[str] = set()
        _matched_clean: list[dict] = []
        for mc in sorted(
            (concept_result.matched_concepts if concept_result else []),
            key=lambda c: c.weight, reverse=True,
        ):
            p = clean_phrase(mc.phrase)
            if is_valid_phrase(p) and p not in _matched_seen:
                _matched_seen.add(p)
                _matched_clean.append({
                    "phrase": p,
                    "weight": mc.weight,
                    "match_type": mc.match_type,
                    "matched_student_phrase": mc.matched_student_phrase,
                    "similarity": mc.similarity,
                })
        result["matched_concepts"] = _matched_clean

        _missing_seen: set[str] = set()
        _missing_clean: list[dict] = []
        for mc in sorted(
            (concept_result.missing_concepts if concept_result else []),
            key=lambda c: c.weight, reverse=True,
        ):
            p = clean_phrase(mc.phrase)
            if is_valid_phrase(p) and p not in _missing_seen:
                _missing_seen.add(p)
                _missing_clean.append({
                    "phrase": p,
                    "weight": mc.weight,
                    "best_candidate": mc.best_candidate,
                    "best_similarity": mc.best_similarity,
                })
        result["missing_concepts"] = _missing_clean

        result["feedback"] = _format_feedback(
            [c["phrase"] for c in _matched_clean],
            [c["phrase"] for c in _missing_clean],
            enrichment=[
                clean_phrase(mc.phrase)
                for mc in (concept_result.enrichment_suggestions if concept_result else [])
                if is_valid_phrase(clean_phrase(mc.phrase))
            ] or None,
        )
        result["sentence_similarity"] = sentence_sim_val
        result["sentence_similarity_precision"] = (
            sentence_result.coverage_precision if sentence_result else 0.0
        )
        result["entailment_score"] = entailment_val
        result["nli_details"] = (
            nli_result.details if nli_result else None
        )
        result["component_weights"] = effective_weights

        if concept_result:
            result["core_recall"] = concept_result.core_recall
            result["supporting_bonus"] = concept_result.supporting_bonus
            result["enrichment_suggestions"] = [
                {
                    "phrase": clean_phrase(mc.phrase),
                    "weight": mc.weight,
                    "best_candidate": mc.best_candidate,
                    "best_similarity": mc.best_similarity,
                }
                for mc in concept_result.enrichment_suggestions
                if is_valid_phrase(clean_phrase(mc.phrase))
            ]
            result["tier_map"] = concept_result.tier_map
        else:
            result["core_recall"] = 0.0
            result["supporting_bonus"] = 0.0
            result["enrichment_suggestions"] = []
            result["tier_map"] = {}

    if debug:
        logger.debug("TF-IDF:   %.4f", tfidf_score)
        logger.debug("SBERT:    %.4f", sbert_score)
        logger.debug("Combined: %.4f", combined)
        logger.debug("Keyword overlap:  %.2f%%", keyword_info["overlap_ratio"] * 100)
        logger.debug("Matched phrases:  %s", keyword_info["matched_keywords"][:5])
        logger.debug("Missing phrases:  %s", keyword_info["missing_keywords"][:5])

        if scoring_v2:
            logger.debug("Concept coverage: %.4f", concept_coverage_val)
            logger.debug("Sentence sim:     %.4f", sentence_sim_val)
            logger.debug("Entailment:       %s", entailment_val)
            logger.debug("Weights:          %s", effective_weights)
            logger.debug("Timings:          %s", timings)

        result["debug"] = {
            "concept": {
                "weights": concept_result.weights if concept_result else {},
                "matched": [
                    {
                        "phrase": mc.phrase,
                        "match_type": mc.match_type,
                        "similarity": mc.similarity,
                    }
                    for mc in (concept_result.matched_concepts if concept_result else [])
                ],
                "missing": [
                    {
                        "phrase": mc.phrase,
                        "best_candidate": mc.best_candidate,
                        "best_similarity": mc.best_similarity,
                    }
                    for mc in (concept_result.missing_concepts if concept_result else [])
                ],
            },
            "sentence": {
                "matrix_shape": list(sentence_result.matrix.shape) if sentence_result and sentence_result.matrix is not None else [],
                "best_matches": sentence_result.best_matches[:10] if sentence_result else [],
                "precision": sentence_result.coverage_precision if sentence_result else 0.0,
            },
            "nli": {
                "pairs": nli_result.details if nli_result else [],
                "aggregated": nli_result.score if nli_result else 0.0,
            },
            "component_weights": effective_weights,
            "timings": timings,
        }

    return result


# --------------------------------------------------------------------------- #
#  CLI quick-test                                                              #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    from nlp import preprocess_for_tfidf, preprocess_for_sbert

    model_answer = (
        "Photosynthesis is the process by which green plants use sunlight, "
        "water, and carbon dioxide to produce glucose and oxygen. "
        "It occurs in the chloroplasts using the pigment chlorophyll."
    )

    student_answer = (
        "Plants make food using sunlight and CO2. "
        "This happens in chloroplasts and produces sugar and oxygen."
    )

    m_tfidf = preprocess_for_tfidf(model_answer)
    s_tfidf = preprocess_for_tfidf(student_answer)
    m_sbert = preprocess_for_sbert(model_answer)
    s_sbert = preprocess_for_sbert(student_answer)

    sbert = SBERTSimilarity()

    scores = compute_similarity(s_tfidf, m_tfidf, s_sbert, m_sbert, sbert, debug=True)
    print("\nFull result:", scores)
