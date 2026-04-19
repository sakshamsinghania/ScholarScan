---
type: community
cohesion: 0.06
members: 45
---

# Structure Extraction

**Cohesion:** 0.06 - loosely connected
**Members:** 45 nodes

## Members
- [[Break answer text into individual pointsbullets.      Detection priority]] - rationale - backend/core/structure_extractor.py
- [[Capitalize the first letter of text without clobbering tech terms.      Standa]] - rationale - backend/core/structure_extractor.py
- [[Deduplicate, strip, remove empties, and normalize dash formatting.]] - rationale - backend/core/structure_extractor.py
- [[Ensure pipelineflow notation (a + b - c - d) is not broken.      This is a pr]] - rationale - backend/core/structure_extractor.py
- [[Ensure proper spacing around punctuation.]] - rationale - backend/core/structure_extractor.py
- [[Extract structured data from cleaned OCR text.      Full pipeline       1. Sema]] - rationale - backend/core/structure_extractor.py
- [[Extract student name and roll number from text.      Handles OCR variants like ']] - rationale - backend/core/structure_extractor.py
- [[Flatten structured extraction output into similarity-ready answer text.      Thi]] - rationale - backend/core/structure_extractor.py
- [[Merge OCR-split compound terms into their correct form.]] - rationale - backend/core/structure_extractor.py
- [[Normalize answer markers like 'ans', 'an's', 'ans.' into 'Ans -'.]] - rationale - backend/core/structure_extractor.py
- [[Normalize technical terms to their canonical casing.]] - rationale - backend/core/structure_extractor.py
- [[Normalize well-known file and resource names to canonical casing.]] - rationale - backend/core/structure_extractor.py
- [[Remove irrelevant metadata tokens that add no semantic value.]] - rationale - backend/core/structure_extractor.py
- [[Remove the student info header from the text, returning the body.      Tries to]] - rationale - backend/core/structure_extractor.py
- [[Replace known OCR-garbled words with their correct forms.]] - rationale - backend/core/structure_extractor.py
- [[Run the full semantic cleaning pipeline on pre-cleaned OCR text.      Pipeline o]] - rationale - backend/core/structure_extractor.py
- [[Separate question text from answer text within a question block.      Args]] - rationale - backend/core/structure_extractor.py
- [[Split long preamble paragraphs into individual sentences.      Only applies to p]] - rationale - backend/core/structure_extractor.py
- [[Split text at inline bullet positions (' - ') into points.      Preserves preamb]] - rationale - backend/core/structure_extractor.py
- [[Split text at match positions into a list of points.      Args         text Fu]] - rationale - backend/core/structure_extractor.py
- [[Split text at named inline item positions.      Each match captures  - name.ext]] - rationale - backend/core/structure_extractor.py
- [[Split the text body into question blocks.      Each block contains the question]] - rationale - backend/core/structure_extractor.py
- [[_clean_points()]] - code - backend/core/structure_extractor.py
- [[_normalize_filenames()]] - code - backend/core/structure_extractor.py
- [[_normalize_punctuation()]] - code - backend/core/structure_extractor.py
- [[_preserve_flow_content()]] - code - backend/core/structure_extractor.py
- [[_safe_capitalize()]] - code - backend/core/structure_extractor.py
- [[_split_by_matches()]] - code - backend/core/structure_extractor.py
- [[_split_inline_bullets()]] - code - backend/core/structure_extractor.py
- [[_split_named_inline_items()]] - code - backend/core/structure_extractor.py
- [[_split_preamble_sentences()]] - code - backend/core/structure_extractor.py
- [[_strip_header()]] - code - backend/core/structure_extractor.py
- [[clean_noise()]] - code - backend/core/structure_extractor.py
- [[extract_answer_block()]] - code - backend/core/structure_extractor.py
- [[extract_answer_points()]] - code - backend/core/structure_extractor.py
- [[extract_structure()]] - code - backend/core/structure_extractor.py
- [[extract_student_info()]] - code - backend/core/structure_extractor.py
- [[fix_common_ocr_errors()]] - code - backend/core/structure_extractor.py
- [[merge_broken_phrases()]] - code - backend/core/structure_extractor.py
- [[normalize_answer_keywords()]] - code - backend/core/structure_extractor.py
- [[normalize_technical_terms()]] - code - backend/core/structure_extractor.py
- [[semantic_clean()]] - code - backend/core/structure_extractor.py
- [[split_questions()]] - code - backend/core/structure_extractor.py
- [[structure_extractor.py]] - code - backend/core/structure_extractor.py
- [[structure_to_text()]] - code - backend/core/structure_extractor.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Structure_Extraction
SORT file.name ASC
```
