"""Extract text from PDF files with OCR fallback for scanned pages."""

import logging
import os
import tempfile
from typing import Callable, Optional

import pdfplumber

from adapters.ocr.base import OcrPage, OcrResult

logger = logging.getLogger(__name__)


class PdfService:
    """
    Extracts text from PDFs using pdfplumber for digital content.
    Falls back to OCR (via injected extract_text_fn) for scanned pages
    that have no extractable text.

    When an ocr_extract_result_fn is provided, PDFs can be routed through
    Mistral OCR natively (bypassing pdfplumber for scanned PDFs).
    """

    def __init__(
        self,
        extract_text_fn: Callable[[str], str],
        ocr_extract_result_fn: Optional[Callable[[str], OcrResult]] = None,
    ):
        self._extract_text_fn = extract_text_fn
        self._ocr_extract_result_fn = ocr_extract_result_fn

    def extract_text(
        self,
        pdf_path: str,
        on_progress: Callable[[int, int, str], None] | None = None,
    ) -> str:
        """
        Extract all text from a PDF file.

        For each page:
        - If digital text exists → use pdfplumber extraction
        - If no text (scanned/handwritten) → convert to image → OCR

        Raises FileNotFoundError if the file doesn't exist.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        page_texts: list[str] = []

        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                if self.is_scanned_page(page):
                    ocr_text = self._ocr_page(pdf_path, i)
                    page_texts.append(ocr_text)
                    extraction_mode = "ocr"
                else:
                    text = page.extract_text() or ""
                    page_texts.append(text)
                    extraction_mode = "digital"

                if on_progress:
                    on_progress(i + 1, total_pages, extraction_mode)

        combined_text = "\n\n".join(page_texts).strip()
        if not combined_text:
            raise ValueError(
                "No text could be extracted from the PDF. "
                "Check Google Vision connectivity or the local Tesseract installation."
            )

        return combined_text

    def is_scanned_page(self, page) -> bool:
        """
        Detect if a pdfplumber page has no extractable text.
        A page is considered scanned if extract_text() returns
        None or whitespace-only content.
        """
        text = page.extract_text()
        return not text or not text.strip()

    def _ocr_page(self, pdf_path: str, page_index: int) -> str:
        """Convert a single PDF page to an image and run OCR on it."""
        try:
            from pdf2image import convert_from_path

            images = convert_from_path(
                pdf_path,
                first_page=page_index + 1,
                last_page=page_index + 1,
                dpi=300,
            )

            if not images:
                return ""

            # Save image to temp file for OCR function
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                images[0].save(tmp, format="PNG")
                tmp_path = tmp.name

            try:
                return self._extract_text_fn(tmp_path)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        except ImportError:
            return ""
        except Exception as exc:
            logger.warning(
                "OCR failed for page %d of %s: %s",
                page_index + 1,
                pdf_path,
                exc,
            )
            return ""

    def extract_result(
        self,
        pdf_path: str,
        on_progress: Callable[[int, int, str], None] | None = None,
    ) -> OcrResult:
        """Extract text from PDF and return a page-aware OcrResult.

        If an OCR provider that supports native PDF ingestion is available
        (e.g. Mistral), route through it first. Fall back to pdfplumber+OCR.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        if self._ocr_extract_result_fn:
            try:
                result = self._ocr_extract_result_fn(pdf_path)
                if result.text.strip():
                    return result
            except Exception as exc:
                logger.warning("PDF native OCR failed, falling back to pdfplumber: %s", exc)

        page_texts: list[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                if self.is_scanned_page(page):
                    ocr_text = self._ocr_page(pdf_path, i)
                    page_texts.append(ocr_text)
                    extraction_mode = "ocr"
                else:
                    text = page.extract_text() or ""
                    page_texts.append(text)
                    extraction_mode = "digital"

                if on_progress:
                    on_progress(i + 1, total_pages, extraction_mode)

        combined = "\n\n".join(page_texts).strip()
        if not combined:
            raise ValueError(
                "No text could be extracted from the PDF. "
                "Check OCR connectivity or the local Tesseract installation."
            )

        ocr_pages = tuple(
            OcrPage(index=i, markdown=t) for i, t in enumerate(page_texts)
        )
        return OcrResult(
            text=combined,
            confidence=0.7,
            provider="pdfplumber",
            page_data=ocr_pages,
        )
