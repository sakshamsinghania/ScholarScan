"""Parse Mistral OCR markdown into a typed Block stream."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class BlockKind(str, Enum):
    HEADING = "heading"
    BOLD_LINE = "bold_line"
    NUMBERED_ITEM = "numbered"
    PARAGRAPH = "paragraph"
    TABLE_ROW = "table_row"
    MATH_BLOCK = "math_block"
    CODE_BLOCK = "code_block"
    BLANK = "blank"


@dataclass(frozen=True)
class Block:
    kind: BlockKind
    text: str
    raw: str
    page_index: int
    line_index: int
    leading_number: int | None = None


_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)")
_BOLD_LINE_RE = re.compile(r"^\*\*(.+?)\*\*\s*$")
_NUMBERED_RE = re.compile(r"^(\d+)\s*[.)]\s+(.*)")
_TABLE_ROW_RE = re.compile(r"^\|.+\|")
_MATH_BLOCK_RE = re.compile(r"^\$\$")
_CODE_FENCE_RE = re.compile(r"^```")


def parse_pages(pages: list[str]) -> list[Block]:
    blocks: list[Block] = []
    global_line = 0
    in_code = False
    in_math = False

    for page_idx, page_md in enumerate(pages):
        for raw_line in page_md.split("\n"):
            stripped = raw_line.strip()

            if in_code:
                if _CODE_FENCE_RE.match(stripped):
                    in_code = False
                blocks.append(Block(
                    kind=BlockKind.CODE_BLOCK, text=stripped, raw=raw_line,
                    page_index=page_idx, line_index=global_line,
                ))
                global_line += 1
                continue

            if in_math:
                blocks.append(Block(
                    kind=BlockKind.MATH_BLOCK, text=stripped, raw=raw_line,
                    page_index=page_idx, line_index=global_line,
                ))
                if _MATH_BLOCK_RE.match(stripped) and global_line > 0:
                    in_math = False
                global_line += 1
                continue

            if _CODE_FENCE_RE.match(stripped):
                in_code = True
                blocks.append(Block(
                    kind=BlockKind.CODE_BLOCK, text=stripped, raw=raw_line,
                    page_index=page_idx, line_index=global_line,
                ))
                global_line += 1
                continue

            if _MATH_BLOCK_RE.match(stripped):
                if stripped == "$$":
                    in_math = not in_math
                blocks.append(Block(
                    kind=BlockKind.MATH_BLOCK, text=stripped, raw=raw_line,
                    page_index=page_idx, line_index=global_line,
                ))
                global_line += 1
                continue

            if not stripped:
                blocks.append(Block(
                    kind=BlockKind.BLANK, text="", raw=raw_line,
                    page_index=page_idx, line_index=global_line,
                ))
                global_line += 1
                continue

            m = _HEADING_RE.match(stripped)
            if m:
                blocks.append(Block(
                    kind=BlockKind.HEADING, text=m.group(2).strip(), raw=raw_line,
                    page_index=page_idx, line_index=global_line,
                ))
                global_line += 1
                continue

            m = _BOLD_LINE_RE.match(stripped)
            if m:
                blocks.append(Block(
                    kind=BlockKind.BOLD_LINE, text=m.group(1).strip(), raw=raw_line,
                    page_index=page_idx, line_index=global_line,
                ))
                global_line += 1
                continue

            if _TABLE_ROW_RE.match(stripped):
                blocks.append(Block(
                    kind=BlockKind.TABLE_ROW, text=stripped, raw=raw_line,
                    page_index=page_idx, line_index=global_line,
                ))
                global_line += 1
                continue

            m = _NUMBERED_RE.match(stripped)
            if m:
                blocks.append(Block(
                    kind=BlockKind.NUMBERED_ITEM, text=m.group(2).strip(),
                    raw=raw_line, page_index=page_idx, line_index=global_line,
                    leading_number=int(m.group(1)),
                ))
                global_line += 1
                continue

            blocks.append(Block(
                kind=BlockKind.PARAGRAPH, text=stripped, raw=raw_line,
                page_index=page_idx, line_index=global_line,
            ))
            global_line += 1

    return blocks
