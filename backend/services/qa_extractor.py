"""Extract Q&A segments from Mistral OCR markdown pages.

Replaces question_service.py with markdown-aware, sequential-ID extraction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from core.markdown_parser import Block, BlockKind, parse_pages

# ---------------------------------------------------------------------------
#  Question detection patterns (ordered by specificity)
# ---------------------------------------------------------------------------

_P1 = re.compile(r"^#{1,3}\s+(?:Q(?:uestion)?\s*)?(\d+)[.):]?\s+(.+)", re.IGNORECASE)
_P2 = re.compile(r"^\*\*(?:Q(?:uestion)?\s*)?(\d+)[.):]?\s*(.+?)\*\*", re.IGNORECASE)
_P3 = re.compile(r"^(?:Q\.?\s*)(\d+)\s*[.):\-—]\s*(.+)", re.IGNORECASE)
_P4 = re.compile(r"^Question\s+(\d+)\s*[.):\-—]\s*(.+)", re.IGNORECASE)
_P5 = re.compile(r"^(\d+)\s*[.)]\s+(\S.+)")

_ANS_PREFIX_RE = re.compile(
    r"^Ans(?:wer)?\s*[→>:&]|^Ans&gt;",
    re.IGNORECASE,
)

_QUESTION_STEMS = frozenset({
    "explain", "discuss", "describe", "define", "compare",
    "state", "list", "what", "how", "why", "give", "show",
})


@dataclass
class QaSegment:
    sequential_id: str
    raw_label: str | None
    question_text: str
    answer_text: str
    start_page: int
    end_page: int
    is_orphan: bool = False
    warnings: list[str] = field(default_factory=list)


class QaExtractor:
    def __init__(self, monotonic_tolerance: int = 3) -> None:
        self._tolerance = monotonic_tolerance

    def extract(self, pages: list[str]) -> list[QaSegment]:
        blocks = parse_pages(pages)
        question_indices = self._find_question_indices(blocks)

        segments: list[QaSegment] = []
        for rank, start in enumerate(question_indices):
            end = question_indices[rank + 1] if rank + 1 < len(question_indices) else len(blocks)
            q_block = blocks[start]
            answer_blocks = blocks[start + 1:end]
            answer_text = _strip_ans_prefix(_reassemble(answer_blocks))

            segments.append(QaSegment(
                sequential_id=f"Q{rank + 1}",
                raw_label=f"{q_block.leading_number}." if q_block.leading_number is not None else None,
                question_text=_question_body(q_block),
                answer_text=answer_text,
                start_page=q_block.page_index,
                end_page=answer_blocks[-1].page_index if answer_blocks else q_block.page_index,
            ))

        if question_indices and question_indices[0] > 0:
            prefix = _reassemble(blocks[:question_indices[0]])
            if _has_substantive_content(prefix):
                segments.insert(0, QaSegment(
                    sequential_id="Q0_orphan",
                    raw_label=None,
                    question_text="",
                    answer_text=prefix,
                    start_page=0,
                    end_page=blocks[question_indices[0] - 1].page_index,
                    is_orphan=True,
                    warnings=["document starts with content before any detected question"],
                ))

        if not segments and blocks:
            full_text = _reassemble(blocks)
            if full_text.strip():
                segments.append(QaSegment(
                    sequential_id="Q1",
                    raw_label=None,
                    question_text="",
                    answer_text=full_text.strip(),
                    start_page=0,
                    end_page=blocks[-1].page_index,
                ))

        return segments

    def extract_from_text(self, text: str) -> list[QaSegment]:
        return self.extract([text])

    def extract_questions(self, pages: list[str]) -> list[dict]:
        segments = self.extract(pages)
        return [
            {"sequential_id": s.sequential_id, "question": s.question_text}
            for s in segments
            if not s.is_orphan and s.question_text
        ]

    # ------------------------------------------------------------------
    #  Question detection
    # ------------------------------------------------------------------

    def _find_question_indices(self, blocks: list[Block]) -> list[int]:
        accepted: list[int] = []
        last_number: int | None = None

        for i, block in enumerate(blocks):
            result = self._try_match(block)
            if result is None:
                continue

            pattern_rank, number, _body = result

            if pattern_rank < 5:
                accepted.append(i)
                last_number = number
                continue

            if self._p5_accepted(block, blocks, i, last_number):
                accepted.append(i)
                last_number = number

        return accepted

    @staticmethod
    def _try_match(block: Block) -> tuple[int, int, str] | None:
        if block.kind == BlockKind.HEADING:
            m = _P1.match(block.raw.strip())
            if m:
                return (1, int(m.group(1)), m.group(2).strip())

        if block.kind == BlockKind.BOLD_LINE:
            m = _P2.match(block.raw.strip())
            if m:
                return (2, int(m.group(1)), m.group(2).strip())

        raw = block.raw.strip()
        m = _P3.match(raw)
        if m:
            return (3, int(m.group(1)), m.group(2).strip())

        m = _P4.match(raw)
        if m:
            return (4, int(m.group(1)), m.group(2).strip())

        if block.kind == BlockKind.NUMBERED_ITEM and block.leading_number is not None:
            m = _P5.match(raw)
            if m:
                return (5, int(m.group(1)), m.group(2).strip())

        return None

    def _p5_accepted(
        self,
        block: Block,
        blocks: list[Block],
        idx: int,
        last_accepted_number: int | None,
    ) -> bool:
        score = 0
        has_strong_signal = False

        # Rule 1: Monotonic number
        if last_accepted_number is not None:
            if abs(block.leading_number - last_accepted_number) <= self._tolerance:
                score += 1
        else:
            score += 1

        # Rule 2: Ans prefix within 6 blocks after (STRONG)
        # Stop at next numbered item — Ans beyond it belongs to that item
        lookahead = blocks[idx + 1: idx + 7]
        for lb in lookahead:
            if lb.kind == BlockKind.NUMBERED_ITEM and lb.leading_number is not None:
                break
            if _ANS_PREFIX_RE.search(lb.text) or _ANS_PREFIX_RE.search(lb.raw):
                score += 1
                has_strong_signal = True
                break

        # Rule 3: Question stem (STRONG)
        body = block.text.strip()
        first_word = body.split()[0].lower().rstrip(":.,") if body else ""
        if first_word in _QUESTION_STEMS:
            score += 1
            has_strong_signal = True

        # Rule 4: Preceded by blank line
        if idx > 0 and blocks[idx - 1].kind == BlockKind.BLANK:
            score += 1

        # Rule 5: Length floor
        if len(body) >= 20:
            score += 1

        return score >= 2 and has_strong_signal


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _question_body(block: Block) -> str:
    result = QaExtractor._try_match(block)
    if result:
        return result[2]
    return block.text


def _reassemble(blocks: list[Block]) -> str:
    return "\n".join(b.raw for b in blocks if b.kind != BlockKind.BLANK or True).strip()


def _strip_ans_prefix(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        m = _ANS_PREFIX_RE.match(stripped)
        if m:
            remainder = stripped[m.end():].strip()
            if remainder:
                out.append(remainder)
        else:
            out.append(line)
    return "\n".join(out).strip()


def _has_substantive_content(text: str) -> bool:
    cleaned = re.sub(r"\s+", " ", text).strip()
    return len(cleaned) > 30
