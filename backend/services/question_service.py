"""Detect and parse questions from raw text using regex patterns."""

import re
from dataclasses import dataclass


@dataclass
class DetectedQuestion:
    """A single detected question with its associated answer text."""

    question_id: str
    text: str           # The question text
    answer_text: str    # Student's answer for that question


# Ordered by specificity: try most specific patterns first
_QUESTION_PATTERNS = [
    # Q1. / Q1) / Q1: / Q1 —
    re.compile(
        r"^(Q\d+)\s*[.):\-—]\s*(.+)",
        re.IGNORECASE | re.MULTILINE,
    ),
    # Question 1: / Question 1. / Question 1)
    re.compile(
        r"^Question\s+(\d+)\s*[.):\-—]\s*(.+)",
        re.IGNORECASE | re.MULTILINE,
    ),
    # 1) / 1. with text after
    re.compile(
        r"^(\d+)\s*[.)]\s+(.+)",
        re.MULTILINE,
    ),
]


class QuestionService:
    """Parse raw text into structured question-answer segments."""

    def detect_questions(self, raw_text: str) -> list[DetectedQuestion]:
        """
        Parse text into structured Q&A segments.

        Detection strategy (layered):
        1. Try regex patterns (Q1., Question 1:, 1., 1))
        2. If no questions found but text exists → single-block fallback

        Returns empty list for empty/whitespace-only text.
        """
        if not raw_text or not raw_text.strip():
            return []

        for pattern in _QUESTION_PATTERNS:
            matches = list(pattern.finditer(raw_text))
            if len(matches) >= 2 or (len(matches) == 1 and self._has_answer_after(matches[0], raw_text)):
                return self._build_segments(matches, raw_text, pattern)

        # Single-block fallback: treat entire text as one answer
        return [
            DetectedQuestion(
                question_id="Q1",
                text="",
                answer_text=raw_text.strip(),
            )
        ]

    def extract_questions_only(self, raw_text: str) -> list[dict]:
        """
        Extract just questions (for question paper input).
        Returns list of {"question_id": ..., "question": ...}
        """
        if not raw_text or not raw_text.strip():
            return []

        for pattern in _QUESTION_PATTERNS:
            matches = list(pattern.finditer(raw_text))
            if matches:
                return self._build_question_list(matches, pattern)

        return []

    def _build_segments(
        self,
        matches: list[re.Match],
        raw_text: str,
        pattern: re.Pattern,
    ) -> list[DetectedQuestion]:
        """Build Q&A segments from regex matches using position-based splitting."""
        segments: list[DetectedQuestion] = []

        for i, match in enumerate(matches):
            question_id = self._normalize_id(match.group(1), i)
            question_text = match.group(2).strip()

            # Answer = text between this match end and next match start
            answer_start = match.end()
            answer_end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
            answer_text = raw_text[answer_start:answer_end].strip()

            segments.append(
                DetectedQuestion(
                    question_id=question_id,
                    text=question_text,
                    answer_text=answer_text,
                )
            )

        return segments

    def _build_question_list(
        self,
        matches: list[re.Match],
        pattern: re.Pattern,
    ) -> list[dict]:
        """Build question-only list from matches."""
        results = []
        for i, match in enumerate(matches):
            question_id = self._normalize_id(match.group(1), i)
            question_text = match.group(2).strip()
            results.append({
                "question_id": question_id,
                "question": question_text,
            })
        return results

    @staticmethod
    def _normalize_id(raw_id: str, index: int) -> str:
        """Normalize question IDs to Q1, Q2, ... format."""
        raw_upper = raw_id.upper()
        if raw_upper.startswith("Q"):
            return raw_upper
        # Numeric only → prefix with Q
        if raw_id.isdigit():
            return f"Q{raw_id}"
        return f"Q{index + 1}"

    @staticmethod
    def _has_answer_after(match: re.Match, raw_text: str) -> bool:
        """Check if there's substantial text after a single match."""
        remaining = raw_text[match.end():].strip()
        return len(remaining) > 10
