# =============================================================================
# scoring.py — Marks Assignment & Feedback Generation
# =============================================================================
# No extra installs needed beyond what similarity.py uses.
# =============================================================================

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import NamedTuple

__all__ = ["AssessmentResult", "score_answer"]

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  Data class for a single assessment result                                   #
# --------------------------------------------------------------------------- #

@dataclass(frozen=True, slots=True)
class AssessmentResult:
    """Immutable result for one student's answer assessment."""

    question_id: str
    student_id: str
    raw_ocr_text: str           # Raw OCR output (Google Vision)
    cleaned_text: str           # Semantic-cleaned text used for similarity/scoring
    tfidf_score: float          # 0.0 – 1.0
    sbert_score: float          # 0.0 – 1.0
    combined_score: float       # weighted combination
    keyword_overlap: float      # fraction of model keywords present
    missing_keywords: tuple[str, ...]  # key terms absent from student answer
    marks: float                # final marks awarded
    max_marks: int              # total marks for this question
    grade: str                  # letter grade band (A/B/C/D/F)
    feedback: str               # feedback string for the student

    def summary(self) -> str:
        """Pretty-print summary for CLI / Colab output."""
        return (
            f"\n{'='*55}\n"
            f"  Question : {self.question_id}\n"
            f"  Student  : {self.student_id}\n"
            f"{'─'*55}\n"
            f"  Cleaned answer : {self.cleaned_text[:80]}...\n"
            f"{'─'*55}\n"
            f"  TF-IDF score   : {self.tfidf_score:.4f}\n"
            f"  SBERT score    : {self.sbert_score:.4f}\n"
            f"  Combined score : {self.combined_score:.4f}\n"
            f"  Keyword overlap: {self.keyword_overlap:.2%}\n"
            f"{'─'*55}\n"
            f"  MARKS   : {self.marks} / {self.max_marks}   [{self.grade}]\n"
            f"  FEEDBACK: {self.feedback}\n"
            f"{'='*55}\n"
        )


# --------------------------------------------------------------------------- #
#  Grade band configuration                                                    #
# --------------------------------------------------------------------------- #

class _GradeBand(NamedTuple):
    """A single grade band definition."""
    min_score: float       # inclusive lower bound
    max_score: float       # exclusive upper bound
    letter: str            # grade letter (A/B/C/D/F)
    marks_fraction: float  # fraction of max_marks awarded
    feedback_key: str      # key into FEEDBACK_TEMPLATES


# Bands are calibrated for COMBINED score (SBERT 70% + TF-IDF 30%).
# Adjust thresholds based on your subject and marking scheme.
_GRADE_BANDS: tuple[_GradeBand, ...] = (
    _GradeBand(0.80, 1.01, "A", 1.00, "excellent"),
    _GradeBand(0.65, 0.80, "B", 0.75, "good"),
    _GradeBand(0.50, 0.65, "C", 0.55, "partial"),
    _GradeBand(0.35, 0.50, "D", 0.35, "weak"),
    _GradeBand(0.00, 0.35, "F", 0.10, "insufficient"),
)

_FALLBACK_BAND = _GradeBand(0.00, 0.01, "F", 0.00, "insufficient")


def _find_band(combined_score: float) -> _GradeBand:
    """Find the grade band matching a combined similarity score."""
    for band in _GRADE_BANDS:
        if band.min_score <= combined_score < band.max_score:
            return band
    return _FALLBACK_BAND


# --------------------------------------------------------------------------- #
#  Feedback templates                                                          #
# --------------------------------------------------------------------------- #

_FEEDBACK_TEMPLATES: dict[str, str] = {
    "excellent": (
        "Excellent work! Your answer closely matches the model solution and "
        "covers all key concepts accurately."
    ),
    "good": (
        "Good answer. You've grasped the main idea, but your response is "
        "missing some detail. Consider elaborating on: {missing}."
    ),
    "partial": (
        "Partial credit awarded. Your answer shows some understanding "
        "({overlap:.0%} keyword coverage), but key points are missing. "
        "Review: {missing}."
    ),
    "weak": (
        "Weak response. Only {overlap:.0%} of the expected terms were present. "
        "You need to revisit the core concepts, particularly: {missing}."
    ),
    "insufficient": (
        "Insufficient. The answer does not adequately address the question. "
        "Please review the topic thoroughly, focusing on: {missing}."
    ),
}


# --------------------------------------------------------------------------- #
#  Internal scoring helpers                                                    #
# --------------------------------------------------------------------------- #

def _compute_marks(
    band: _GradeBand,
    max_marks: int,
    keyword_overlap: float,
    keyword_penalty: float = 0.1,
) -> float:
    """Convert a grade band to a numeric mark.

    Applies a small keyword-coverage penalty to handle the edge case where
    SBERT gives a high score (paraphrase detected) but critical domain terms
    are absent from the student answer.

    Args:
        band: The grade band for this score.
        max_marks: Maximum marks available for the question.
        keyword_overlap: Fraction of model-answer keywords present (0.0 – 1.0).
        keyword_penalty: Fraction by which marks are reduced per unit of
                         missing keyword coverage (default: 10%).

    Returns:
        Final marks (float, >= 0.0).
    """
    raw_marks = band.marks_fraction * max_marks

    # Keyword penalty: if many key terms are missing, reduce slightly
    # Max penalty is keyword_penalty * max_marks (e.g. 1 mark out of 10)
    coverage_deficit = max(0.0, 1.0 - keyword_overlap)
    penalty = coverage_deficit * keyword_penalty * max_marks

    return max(0.0, round(raw_marks - penalty, 1))


def _generate_feedback(
    feedback_key: str,
    missing_keywords: list[str] | tuple[str, ...],
    keyword_overlap: float,
) -> str:
    """Fill in the feedback template with missing keywords and overlap ratio.

    Args:
        feedback_key: One of: 'excellent', 'good', 'partial', 'weak', 'insufficient'
        missing_keywords: Key terms the student didn't mention.
        keyword_overlap: Fraction of model keywords covered.

    Returns:
        Formatted feedback string.
    """
    template = _FEEDBACK_TEMPLATES.get(
        feedback_key, _FEEDBACK_TEMPLATES["insufficient"]
    )

    # Take top 3 most important missing terms
    top_missing = ", ".join(missing_keywords[:3]) if missing_keywords else "none"

    return template.format(missing=top_missing, overlap=keyword_overlap)


# --------------------------------------------------------------------------- #
#  Public API                                                                  #
# --------------------------------------------------------------------------- #

def score_answer(
    similarity_result: dict,
    question_id: str,
    student_id: str,
    raw_ocr_text: str,
    cleaned_text: str,
    max_marks: int = 10,
    debug: bool = False,
) -> AssessmentResult:
    """Take the output of compute_similarity() and produce a full AssessmentResult.

    Args:
        similarity_result: Dict returned by compute_similarity().
        question_id: Identifier for the question (e.g. 'Q1').
        student_id: Student name or roll number.
        raw_ocr_text: Raw OCR output (for records).
        cleaned_text: Semantic-cleaned student answer used downstream.
        max_marks: Marks available for this question.
        debug: Print result summary if True.

    Returns:
        A populated AssessmentResult object.
    """
    combined = similarity_result["combined_score"]
    tfidf = similarity_result["tfidf_score"]
    sbert = similarity_result["sbert_score"]
    overlap = similarity_result["keyword_overlap"]
    missing = similarity_result["missing_keywords"]

    # Single lookup — no duplicate iteration
    band = _find_band(combined)
    marks = _compute_marks(band, max_marks, overlap)
    feedback = _generate_feedback(band.feedback_key, missing, overlap)

    result = AssessmentResult(
        question_id=question_id,
        student_id=student_id,
        raw_ocr_text=raw_ocr_text,
        cleaned_text=cleaned_text,
        tfidf_score=tfidf,
        sbert_score=sbert,
        combined_score=combined,
        keyword_overlap=overlap,
        missing_keywords=tuple(missing),
        marks=marks,
        max_marks=max_marks,
        grade=band.letter,
        feedback=feedback,
    )

    if debug:
        logger.debug(result.summary())

    return result


# --------------------------------------------------------------------------- #
#  CLI quick-test                                                              #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Simulate a similarity result coming from similarity.py
    mock_similarity = {
        "tfidf_score": 0.52,
        "sbert_score": 0.73,
        "combined_score": 0.67,  # 0.3*0.52 + 0.7*0.73
        "keyword_overlap": 0.60,
        "missing_keywords": ["chlorophyll", "glucose", "carbon dioxide"],
    }

    result = score_answer(
        similarity_result=mock_similarity,
        question_id="Q1",
        student_id="Student_01",
        raw_ocr_text="Plants make food from sunlight...",
        cleaned_text="plant make food sunlight oxygen",
        max_marks=10,
        debug=True,
    )
