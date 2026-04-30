"""Tests for QaExtractor — question detection and answer span extraction."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.qa_extractor import QaExtractor


@pytest.fixture
def extractor():
    return QaExtractor()


class TestBasicExtraction:
    def test_simple_qa_pairs(self, extractor):
        pages = ["1. What is AI?\n\nAns → AI is artificial intelligence.\n\n2. What is ML?\n\nAns → ML is machine learning."]
        segments = extractor.extract(pages)
        assert len(segments) == 2
        assert segments[0].sequential_id == "Q1"
        assert segments[1].sequential_id == "Q2"
        assert "artificial intelligence" in segments[0].answer_text

    def test_sequential_relabeling(self, extractor):
        pages = ["5. Explain BigQuery\n\nAns> BigQuery is...\n\n4. Compare models\n\nAns> Models differ..."]
        segments = extractor.extract(pages)
        assert segments[0].sequential_id == "Q1"
        assert segments[0].raw_label == "5."
        assert segments[1].sequential_id == "Q2"
        assert segments[1].raw_label == "4."


class TestMonotonicGuard:
    def test_rejects_inline_numbered_list(self, extractor):
        pages = [
            "5. Explain the lifecycle of serverless functions\n\n"
            "Ans> 1. Deploy code\n2. Register trigger\n3. Trigger fires\n4. Cold start\n5. Execute"
        ]
        segments = extractor.extract(pages)
        assert len(segments) == 1
        assert "Deploy code" in segments[0].answer_text
        assert "Register trigger" in segments[0].answer_text

    def test_tolerance_accepts_mislabeled_questions(self, extractor):
        pages = [
            "1. Explain architecture\n\nAns → Architecture is...\n\n"
            "2. Discuss advantages\n\nAns → Advantages are...\n\n"
            "5. Explain BigQuery\n\nAns> BigQuery handles..."
        ]
        segments = extractor.extract(pages)
        assert len(segments) == 3
        assert segments[2].raw_label == "5."
        assert segments[2].sequential_id == "Q3"


class TestOrphanDetection:
    def test_orphan_prefix_before_first_question(self, extractor):
        pages = ["Name - Alice\nRoll No - 12345\nCloud Computing Assignment\n\n1. Explain Helm charts\n\nAns → Helm charts are..."]
        segments = extractor.extract(pages)
        orphans = [s for s in segments if s.is_orphan]
        non_orphans = [s for s in segments if not s.is_orphan]
        assert len(orphans) == 1
        assert orphans[0].sequential_id == "Q0_orphan"
        assert len(non_orphans) == 1


class TestEmptyAnswer:
    def test_adjacent_questions_produce_empty_answer(self, extractor):
        pages = ["1. Explain first concept\n\nAns → \n\n2. Explain second concept\n\nAns → Answer to second"]
        segments = extractor.extract(pages)
        non_orphans = [s for s in segments if not s.is_orphan]
        assert len(non_orphans) == 2


class TestSingleBlockFallback:
    def test_no_questions_returns_single_segment(self, extractor):
        pages = ["This is just a plain text with no questions at all. It has enough content to be meaningful."]
        segments = extractor.extract(pages)
        assert len(segments) == 1
        assert segments[0].sequential_id == "Q1"


class TestMultiPageAnswers:
    def test_answer_spans_pages(self, extractor):
        pages = [
            "1. Explain serverless advantages\n\nAns → Fast deployment",
            "Cold start latency is a limitation.\n\n2. Next question\n\nAns → Answer here",
        ]
        segments = extractor.extract(pages)
        non_orphans = [s for s in segments if not s.is_orphan]
        assert len(non_orphans) == 2
        assert non_orphans[0].start_page == 0
        assert non_orphans[0].end_page == 1


class TestMarkdownFidelity:
    def test_latex_preserved(self, extractor):
        pages = ["1. Explain alpha decay\n\nAns → The formula is $\\alpha$ decay with $E = mc^2$"]
        segments = extractor.extract(pages)
        assert "$\\alpha$" in segments[0].answer_text

    def test_table_preserved(self, extractor):
        pages = ["1. Compare models\n\nAns> Results:\n| A | B |\n| --- | --- |\n| 1 | 2 |"]
        segments = extractor.extract(pages)
        assert "|" in segments[0].answer_text


class TestExtractQuestions:
    def test_returns_question_dicts(self, extractor):
        pages = ["1. What is AI?\n\nAns → AI is...\n\n2. What is ML?\n\nAns → ML is..."]
        result = extractor.extract_questions(pages)
        assert len(result) == 2
        assert result[0]["sequential_id"] == "Q1"
        assert "AI" in result[0]["question"]


class TestExtractFromText:
    def test_single_string_input(self, extractor):
        text = "1. Explain Helm\n\nAns → Helm is a package manager"
        segments = extractor.extract_from_text(text)
        assert len(segments) >= 1
