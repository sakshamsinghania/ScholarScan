# =============================================================================
# similarity.py — Semantic Similarity Scoring
# =============================================================================
# Dependencies:
#   sentence-transformers, scikit-learn, numpy
# =============================================================================

from __future__ import annotations

import logging
import os

import numpy as np
from huggingface_hub import try_to_load_from_cache
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer, util

__all__ = ["TFIDFSimilarity", "SBERTSimilarity", "compute_similarity"]

logger = logging.getLogger(__name__)


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


# --------------------------------------------------------------------------- #
#  Method A: TF-IDF Cosine Similarity                                         #
# --------------------------------------------------------------------------- #
#
#  HOW IT WORKS:
#    TF-IDF converts each text into a sparse vector where each dimension
#    represents a word, and the value is how "important" that word is
#    (frequent in this doc, rare across others). Cosine similarity then
#    measures the angle between the two vectors — 1.0 = identical direction.
#
#  LIMITATION:
#    "The dog bit the man" and "The man bit the dog" score 1.0 (same words).
#    It has NO understanding of meaning — only word overlap.
#
#  WHEN TO USE:
#    Fast prototyping, short answers, keyword-heavy subjects (math, coding).
# --------------------------------------------------------------------------- #

class TFIDFSimilarity:
    """Computes cosine similarity between two texts using TF-IDF vectors.

    Accepts text preprocessed with:
    sanitize -> fix_split_words -> domain_correct -> tokenize
    -> remove_stopwords -> lemmatize
    """

    def __init__(self) -> None:
        # ngram_range=(1,2): considers both individual words AND 2-word phrases
        # This captures 'blood pressure' as a unit, not just 'blood' + 'pressure'
        self._vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=5000)

    def compute(self, student_text: str, model_text: str) -> float:
        """Compute cosine similarity between student and model text.

        Returns a score in range [0.0, 1.0].
        Returns 0.0 if either input is empty.
        """
        if not student_text.strip() or not model_text.strip():
            return 0.0

        # Fit vectorizer on both texts so vocabulary is shared
        tfidf_matrix = self._vectorizer.fit_transform([student_text, model_text])

        # tfidf_matrix[0] = student vector, tfidf_matrix[1] = model vector
        score = cosine_similarity(tfidf_matrix[0], tfidf_matrix[1])[0][0]
        return round(float(np.clip(score, 0.0, 1.0)), 4)

    def keyword_overlap(self, student_text: str, model_text: str) -> dict:
        """Compute keyword overlap between student and model answers.

        Returns a dict with:
          - overlap_ratio: fraction of model keywords present in student answer
          - matched_keywords: set intersection
          - missing_keywords: model keywords not found in student answer
        """
        model_words = set(model_text.split())
        student_words = set(student_text.split())

        if not model_words:
            return {
                "overlap_ratio": 0.0,
                "matched_keywords": [],
                "missing_keywords": [],
            }

        matched = model_words & student_words
        missing = model_words - student_words

        return {
            "overlap_ratio": round(len(matched) / len(model_words), 4),
            "matched_keywords": sorted(matched),
            "missing_keywords": sorted(missing),
        }


# --------------------------------------------------------------------------- #
#  Method B: Sentence-BERT Similarity                                          #
# --------------------------------------------------------------------------- #
#
#  HOW IT WORKS:
#    Sentence-BERT encodes each sentence as a 384-dim dense vector in a
#    semantic space — meaning "apple" and "fruit" end up close together.
#    Cosine similarity in this space reflects MEANING, not word overlap.
#
#  ADVANTAGE over TF-IDF:
#    "The dog bit the man" and "A canine attacked a person" → high similarity.
#    Handles paraphrasing, synonyms, and different sentence structures.
#
#  MODELS (trade-off: speed vs accuracy):
#    'all-MiniLM-L6-v2'    → fastest, good accuracy  (use in Colab)
#    'all-mpnet-base-v2'   → slower, best accuracy   (use for final eval)
#    'paraphrase-MiniLM-L6-v2' → optimized for paraphrase detection
# --------------------------------------------------------------------------- #

class SBERTSimilarity:
    """Computes semantic similarity using Sentence-BERT embeddings.

    Accepts text preprocessed with:
    sanitize -> fix_split_words -> domain_correct
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        logger.info("Loading SBERT model from local cache: %s ...", model_name)
        self._model = None
        self._model_name = model_name

        try:
            self._model = _load_sentence_transformer_offline(model_name)
            logger.info("SBERT model ready.")
        except Exception as e:
            logger.warning(
                "SBERT model '%s' is unavailable locally; semantic similarity is disabled until the model is installed. Error: %s",
                model_name,
                e,
            )

    @property
    def is_available(self) -> bool:
        """Whether the SBERT model loaded successfully."""
        return self._model is not None

    def embed(self, text: str):
        """Return the sentence embedding vector for a given text."""
        if self._model is None:
            raise RuntimeError(
                f"SBERT model '{self._model_name}' is not available locally."
            )
        return self._model.encode(text, convert_to_tensor=True)

    def compute(self, student_text: str, model_text: str) -> float:
        """Compute semantic similarity between student and model text.

        Returns a score clamped to [0.0, 1.0].
        Raw cosine similarity can be in [-1.0, 1.0] but negative values
        are extremely rare for natural text.
        """
        if not student_text.strip() or not model_text.strip():
            return 0.0
        if self._model is None:
            return 0.0

        emb_student = self.embed(student_text)
        emb_model = self.embed(model_text)

        score = util.cos_sim(emb_student, emb_model).item()
        # Clamp to [0, 1] — negative similarity is meaningless for grading
        return round(float(np.clip(score, 0.0, 1.0)), 4)

    def batch_compute(self, student_answers: list[str], model_answer: str) -> list[float]:
        """Score a batch of student answers against ONE model answer.

        Much faster than calling compute() in a loop because the model
        answer is encoded only once.

        Returns:
            List of similarity scores (same order as input), clamped to [0.0, 1.0].
        """
        if not model_answer.strip():
            return [0.0] * len(student_answers)
        if self._model is None:
            return [0.0] * len(student_answers)

        emb_model = self.embed(model_answer)
        emb_students = self._model.encode(student_answers, convert_to_tensor=True)

        scores = util.cos_sim(emb_students, emb_model).squeeze().tolist()

        # Handle edge case: single student → cos_sim returns a scalar
        if isinstance(scores, float):
            scores = [scores]

        return [round(float(np.clip(s, 0.0, 1.0)), 4) for s in scores]


# --------------------------------------------------------------------------- #
#  Combined scorer: run both methods and return a weighted result              #
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
) -> dict:
    """Run TF-IDF + SBERT similarity and return a weighted combined score.

    The combined score uses SBERT as the primary signal (70%) and
    TF-IDF keyword overlap as a secondary signal (30%).
    This prevents pure paraphrasing from scoring 10/10 if key technical
    terms from the model answer are missing.

    Args:
        student_tfidf: Student answer preprocessed for TF-IDF.
        model_tfidf:   Model answer preprocessed for TF-IDF.
        student_sbert: Student answer preprocessed for SBERT.
        model_sbert:   Model answer preprocessed for SBERT.
        sbert_model:   An instantiated SBERTSimilarity object.
        tfidf_weight:  Weight for TF-IDF score in final combined score.
        sbert_weight:  Weight for SBERT score in final combined score.

    Returns:
        Dict with individual scores, keyword analysis, and combined score.
    """
    tfidf_scorer = TFIDFSimilarity()

    tfidf_score = tfidf_scorer.compute(student_tfidf, model_tfidf)
    keyword_info = tfidf_scorer.keyword_overlap(student_tfidf, model_tfidf)
    sbert_score = sbert_model.compute(student_sbert, model_sbert)
    use_sbert = getattr(sbert_model, "is_available", True)

    if use_sbert:
        combined = round(
            (tfidf_weight * tfidf_score) + (sbert_weight * sbert_score), 4
        )
    else:
        # Fall back to keyword/phrase overlap scoring when the semantic model
        # is unavailable so offline deployments still function in degraded mode.
        combined = tfidf_score

    # Clamp combined score to valid range
    combined = float(np.clip(combined, 0.0, 1.0))

    result = {
        "tfidf_score": tfidf_score,
        "sbert_score": sbert_score,
        "combined_score": combined,
        "keyword_overlap": keyword_info["overlap_ratio"],
        "missing_keywords": keyword_info["missing_keywords"],
    }

    if debug:
        logger.debug("TF-IDF:   %.4f", tfidf_score)
        logger.debug("SBERT:    %.4f", sbert_score)
        logger.debug("Combined: %.4f", combined)
        logger.debug("Keyword overlap: %.2f%%", keyword_info["overlap_ratio"] * 100)
        logger.debug("Missing terms:   %s", keyword_info["missing_keywords"][:5])

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
