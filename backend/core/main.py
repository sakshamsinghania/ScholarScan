"""Core assessment pipeline: OCR → NLP → Similarity → Scoring."""

from __future__ import annotations

import logging

from core.ocr_google_vision import extract_text
from core.nlp import preprocess_for_tfidf, preprocess_for_sbert
from core.similarity import SBERTSimilarity, compute_similarity
from core.scoring import AssessmentResult, score_answer

__all__ = ["process_single"]

logger = logging.getLogger(__name__)


def process_single(
    image_path: str,
    model_answer: str,
    sbert: SBERTSimilarity,
    question_id: str = "Q1",
    student_id: str = "anonymous",
    max_marks: int = 10,
    tfidf_weight: float = 0.3,
    sbert_weight: float = 0.7,
    debug: bool = False,
    pre_extracted_text: str | None = None,
) -> AssessmentResult | None:
    """Run the full assessment pipeline for one student answer.

    Args:
        image_path: Path to the student's answer image.
        model_answer: Reference answer text.
        sbert: Pre-loaded SBERTSimilarity instance.
        question_id: Question identifier (e.g. 'Q1').
        student_id: Student identifier.
        max_marks: Maximum marks for this question.
        tfidf_weight: Weight for TF-IDF in combined score.
        sbert_weight: Weight for SBERT in combined score.
        debug: Enable verbose logging.
        pre_extracted_text: If provided, skip OCR and use this text directly.

    Returns:
        An AssessmentResult, or None if any step fails.
    """
    logger.info("Processing: %s | %s", student_id, question_id)

    # Step 1: OCR (or use pre-extracted text)
    if pre_extracted_text and pre_extracted_text.strip():
        raw_text = pre_extracted_text
    else:
        try:
            raw_text = extract_text(image_path, debug=debug)
        except Exception as e:
            logger.error("OCR failed for %s: %s", image_path, e)
            return None

    if not raw_text.strip():
        logger.warning("Empty text for %s", image_path)
        return None

    # Step 2: NLP preprocessing
    student_tfidf = preprocess_for_tfidf(raw_text, debug=debug)
    student_sbert = preprocess_for_sbert(raw_text, debug=debug)
    model_tfidf = preprocess_for_tfidf(model_answer, debug=debug)
    model_sbert = preprocess_for_sbert(model_answer, debug=debug)

    # Step 3: Similarity
    sim_result = compute_similarity(
        student_tfidf=student_tfidf,
        model_tfidf=model_tfidf,
        student_sbert=student_sbert,
        model_sbert=model_sbert,
        sbert_model=sbert,
        tfidf_weight=tfidf_weight,
        sbert_weight=sbert_weight,
        debug=debug,
    )

    # Step 4: Scoring
    result = score_answer(
        similarity_result=sim_result,
        question_id=question_id,
        student_id=student_id,
        raw_ocr_text=raw_text,
        cleaned_text=student_sbert,
        max_marks=max_marks,
        debug=debug,
    )

    return result
