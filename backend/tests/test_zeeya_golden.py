"""Golden test: QaExtractor against zeeya_extracted.md fixture.

Verifies the exact extraction specified in OCR_POSTPROCESS_REDESIGN_PLAN.md §4–5.
"""

import os
import sys
import re
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.qa_extractor import QaExtractor

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "zeeya_extracted.md")
_PAGE_DELIMITER_RE = re.compile(r"^---\s*Page\s+\d+\s*---\s*$", re.MULTILINE)


def _load_pages() -> list[str]:
    with open(FIXTURE_PATH) as f:
        raw = f.read()
    parts = _PAGE_DELIMITER_RE.split(raw)
    return [p.strip() for p in parts if p.strip()]


@pytest.fixture
def segments():
    extractor = QaExtractor()
    pages = _load_pages()
    result = extractor.extract(pages)
    return [s for s in result if not s.is_orphan]


class TestSegmentCount:
    def test_exactly_7_segments(self, segments):
        assert len(segments) == 7


class TestSequentialIds:
    def test_sequential_ids(self, segments):
        ids = [s.sequential_id for s in segments]
        assert ids == ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7"]


class TestRawLabels:
    def test_raw_labels(self, segments):
        labels = [s.raw_label for s in segments]
        assert labels == ["1.", "2.", "5.", "4.", "5.", "6.", "7."]


class TestQuestionPrefixes:
    def test_q1_prefix(self, segments):
        assert segments[0].question_text.startswith("Explain the architecture of a Helm chart")

    def test_q2_prefix(self, segments):
        assert segments[1].question_text.startswith("Discuss the advantages and limitations of serverless")

    def test_q3_prefix(self, segments):
        assert segments[2].question_text.startswith("Explain how Google BigQuery")

    def test_q4_prefix(self, segments):
        assert "Compare" in segments[3].question_text

    def test_q5_prefix(self, segments):
        assert segments[4].question_text.startswith("Explain the complete lifecycle")

    def test_q6_prefix(self, segments):
        assert segments[5].question_text.startswith("Discuss the role of Helm")

    def test_q7_prefix(self, segments):
        assert segments[6].question_text.startswith("Explain the working of edge inference")


class TestAnswerContent:
    def test_q1_answer_starts(self, segments):
        assert "Helm Chart" in segments[0].answer_text or "Helm chart" in segments[0].answer_text.lower()

    def test_q3_answer_mentions_bigquery(self, segments):
        assert "BigQuery" in segments[2].answer_text or "columnar" in segments[2].answer_text.lower()

    def test_q5_inline_list_not_split(self, segments):
        """Q5's answer contains numbered inline list that must NOT be split as questions."""
        assert "Register trigger" in segments[4].answer_text
        assert "Trigger fires" in segments[4].answer_text

    def test_q2_spans_two_pages(self, segments):
        """Q2 answer should contain content from both page 1 and page 2."""
        ans = segments[1].answer_text
        assert "event" in ans.lower() or "deployment" in ans.lower()
        assert "Cold start" in ans or "cold start" in ans.lower()


class TestPageSpans:
    def test_q1_pages(self, segments):
        assert segments[0].start_page == 0

    def test_q2_spans_pages(self, segments):
        assert segments[1].start_page == 0
        assert segments[1].end_page >= 1

    def test_q7_last_page(self, segments):
        assert segments[6].start_page == 4
