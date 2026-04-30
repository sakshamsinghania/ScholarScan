"""Tests for core.markdown_parser — Mistral markdown to Block stream."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.markdown_parser import parse_pages, BlockKind


class TestBlockKindClassification:
    def test_heading(self):
        blocks = parse_pages(["## Hello World"])
        assert blocks[0].kind == BlockKind.HEADING
        assert blocks[0].text == "Hello World"

    def test_bold_line(self):
        blocks = parse_pages(["**Question 1**"])
        assert blocks[0].kind == BlockKind.BOLD_LINE
        assert blocks[0].text == "Question 1"

    def test_numbered_item(self):
        blocks = parse_pages(["1. Explain the architecture"])
        assert blocks[0].kind == BlockKind.NUMBERED_ITEM
        assert blocks[0].leading_number == 1
        assert blocks[0].text == "Explain the architecture"

    def test_paragraph(self):
        blocks = parse_pages(["Some regular text here"])
        assert blocks[0].kind == BlockKind.PARAGRAPH

    def test_table_row(self):
        blocks = parse_pages(["| Col1 | Col2 | Col3 |"])
        assert blocks[0].kind == BlockKind.TABLE_ROW

    def test_code_block(self):
        blocks = parse_pages(["```python\nprint('hi')\n```"])
        assert all(b.kind == BlockKind.CODE_BLOCK for b in blocks)

    def test_math_block(self):
        blocks = parse_pages(["$$\nx = y + z\n$$"])
        assert blocks[0].kind == BlockKind.MATH_BLOCK

    def test_blank(self):
        blocks = parse_pages(["line1\n\nline2"])
        assert blocks[1].kind == BlockKind.BLANK


class TestPageIndex:
    def test_preserves_page_index_across_pages(self):
        blocks = parse_pages(["Page 0 text", "Page 1 text", "Page 2 text"])
        assert blocks[0].page_index == 0
        assert blocks[1].page_index == 1
        assert blocks[2].page_index == 2

    def test_multiline_page(self):
        blocks = parse_pages(["line1\nline2\nline3"])
        assert all(b.page_index == 0 for b in blocks)
        assert blocks[0].line_index == 0
        assert blocks[1].line_index == 1
        assert blocks[2].line_index == 2


class TestHtmlEntity:
    def test_ans_gt_entity(self):
        blocks = parse_pages(["Ans&gt; some answer"])
        assert blocks[0].kind == BlockKind.PARAGRAPH
        assert "&gt;" in blocks[0].raw
