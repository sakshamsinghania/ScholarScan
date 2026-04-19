---
type: community
cohesion: 0.10
members: 21
---

# PDF Service Tests

**Cohesion:** 0.10 - loosely connected
**Members:** 21 nodes

## Members
- [[.test_extracts_text_from_digital_pdf()]] - code - backend/tests/test_pdf_service.py
- [[.test_page_with_text_not_scanned()]] - code - backend/tests/test_pdf_service.py
- [[.test_page_without_text_is_scanned()]] - code - backend/tests/test_pdf_service.py
- [[.test_raises_on_nonexistent_file()]] - code - backend/tests/test_pdf_service.py
- [[.test_returns_string()]] - code - backend/tests/test_pdf_service.py
- [[.test_text_contains_both_pages()]] - code - backend/tests/test_pdf_service.py
- [[Create a PDF with no text content (simulates a scanned PDF).]] - rationale - backend/tests/test_pdf_service.py
- [[Create a minimal digital PDF with extractable text using pdfplumber-compatible f]] - rationale - backend/tests/test_pdf_service.py
- [[Mock OCR function that returns predictable text.]] - rationale - backend/tests/test_pdf_service.py
- [[TestExtractText]] - code - backend/tests/test_pdf_service.py
- [[TestIsScannedPage]] - code - backend/tests/test_pdf_service.py
- [[TestOcrFallback]] - code - backend/tests/test_pdf_service.py
- [[Tests for PdfService — text extraction from digital and scanned PDFs.]] - rationale - backend/tests/test_pdf_service.py
- [[digital_pdf_path()]] - code - backend/tests/test_pdf_service.py
- [[empty_pdf_path()]] - code - backend/tests/test_pdf_service.py
- [[mock_ocr_fn()_1]] - code - backend/tests/test_pdf_service.py
- [[service()_3]] - code - backend/tests/test_pdf_service.py
- [[test_falls_back_to_ocr_for_scanned_page()]] - code - backend/tests/test_pdf_service.py
- [[test_ocr_fallback_returns_text()]] - code - backend/tests/test_pdf_service.py
- [[test_pdf_service.py]] - code - backend/tests/test_pdf_service.py
- [[test_raises_when_no_text_can_be_extracted()]] - code - backend/tests/test_pdf_service.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/PDF_Service_Tests
SORT file.name ASC
```

## Connections to other communities
- 7 edges to [[_COMMUNITY_App Bootstrap & Services]]

## Top bridge nodes
- [[TestExtractText]] - degree 6, connects to 1 community
- [[TestIsScannedPage]] - degree 4, connects to 1 community
- [[Tests for PdfService — text extraction from digital and scanned PDFs.]] - degree 2, connects to 1 community
- [[Mock OCR function that returns predictable text.]] - degree 2, connects to 1 community
- [[Create a minimal digital PDF with extractable text using pdfplumber-compatible f]] - degree 2, connects to 1 community