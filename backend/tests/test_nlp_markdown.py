"""Tests for preprocess_markdown_for_sbert — markdown-aware SBERT preprocessing."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.nlp import preprocess_markdown_for_sbert


class TestMarkdownStripping:
    def test_strips_heading_markers(self):
        result = preprocess_markdown_for_sbert("## Limitations:")
        assert result == "Limitations:"
        assert "#" not in result

    def test_strips_bold(self):
        result = preprocess_markdown_for_sbert("**Important concept**")
        assert result == "Important concept"
        assert "**" not in result

    def test_strips_italic(self):
        result = preprocess_markdown_for_sbert("*emphasis here*")
        assert result == "emphasis here"

    def test_strips_leading_bullets(self):
        result = preprocess_markdown_for_sbert("- bullet point\n* another\n+ third")
        assert "bullet point" in result
        assert result.startswith("bullet point")

    def test_strips_table_separator(self):
        result = preprocess_markdown_for_sbert("| A | B |\n| --- | --- |\n| 1 | 2 |")
        assert "---" not in result
        assert "| A | B |" in result


class TestPreservation:
    def test_preserves_case(self):
        result = preprocess_markdown_for_sbert("BigQuery uses Dremel Architecture")
        assert "BigQuery" in result
        assert "Dremel" in result

    def test_preserves_math_symbols(self):
        result = preprocess_markdown_for_sbert("Formula: $\\alpha$ and $E = mc^2$")
        assert "\\alpha" in result
        assert "E = mc^2" in result

    def test_preserves_table_pipes(self):
        result = preprocess_markdown_for_sbert("| Col1 | Col2 |")
        assert "|" in result

    def test_preserves_special_chars(self):
        result = preprocess_markdown_for_sbert("Use $, #, *, & in expressions")
        assert "$" in result


class TestHtmlEntities:
    def test_decodes_gt(self):
        result = preprocess_markdown_for_sbert("Ans&gt; answer")
        assert ">" in result
        assert "&gt;" not in result

    def test_decodes_amp(self):
        result = preprocess_markdown_for_sbert("A &amp; B")
        assert "& B" in result
