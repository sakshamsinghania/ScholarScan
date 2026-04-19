"""Tests for PdfService — text extraction from digital and scanned PDFs."""

import os
import sys
import tempfile
import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.pdf_service import PdfService


@pytest.fixture
def mock_ocr_fn():
    """Mock OCR function that returns predictable text."""
    return MagicMock(return_value="OCR extracted text from scanned page")


@pytest.fixture
def service(mock_ocr_fn):
    return PdfService(extract_text_fn=mock_ocr_fn)


@pytest.fixture
def digital_pdf_path(tmp_path):
    """Create a minimal digital PDF with extractable text using pdfplumber-compatible format."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        path = str(tmp_path / "digital.pdf")
        c = canvas.Canvas(path, pagesize=letter)
        c.drawString(100, 700, "Q1. What is photosynthesis?")
        c.drawString(100, 680, "Plants use sunlight to make food.")
        c.showPage()
        c.drawString(100, 700, "Q2. What is gravity?")
        c.drawString(100, 680, "Force that pulls objects toward earth.")
        c.showPage()
        c.save()
        return path
    except ImportError:
        pytest.skip("reportlab not installed")


@pytest.fixture
def empty_pdf_path(tmp_path):
    """Create a PDF with no text content (simulates a scanned PDF)."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        path = str(tmp_path / "scanned.pdf")
        c = canvas.Canvas(path, pagesize=letter)
        # Draw a rectangle but no text — simulates scanned image
        c.rect(100, 600, 200, 100, fill=1)
        c.showPage()
        c.save()
        return path
    except ImportError:
        pytest.skip("reportlab not installed")


class TestExtractText:
    def test_extracts_text_from_digital_pdf(self, service, digital_pdf_path):
        text = service.extract_text(digital_pdf_path)
        assert "photosynthesis" in text.lower()
        assert "gravity" in text.lower()

    def test_returns_string(self, service, digital_pdf_path):
        result = service.extract_text(digital_pdf_path)
        assert isinstance(result, str)

    def test_text_contains_both_pages(self, service, digital_pdf_path):
        text = service.extract_text(digital_pdf_path)
        assert "Q1" in text
        assert "Q2" in text

    def test_raises_on_nonexistent_file(self, service):
        with pytest.raises(FileNotFoundError):
            service.extract_text("/nonexistent/fake.pdf")

    @patch("services.pdf_service.os.path.exists", return_value=True)
    @patch("services.pdf_service.pdfplumber.open")
    def test_reports_per_page_progress(self, mock_open, _mock_exists, service):
        progress_updates = []
        page_one = MagicMock()
        page_one.extract_text.return_value = "Page 1 text"
        page_two = MagicMock()
        page_two.extract_text.return_value = "Page 2 text"
        pdf = MagicMock()
        pdf.pages = [page_one, page_two]
        mock_open.return_value.__enter__.return_value = pdf

        text = service.extract_text(
            "/fake/document.pdf",
            on_progress=lambda current, total, mode: progress_updates.append((current, total, mode)),
        )

        assert "page 1 text" in text.lower()
        assert progress_updates == [
            (1, 2, "digital"),
            (2, 2, "digital"),
        ]


class TestOcrFallback:
    @patch("services.pdf_service.PdfService._ocr_page")
    def test_falls_back_to_ocr_for_scanned_page(self, mock_ocr_page, service, empty_pdf_path):
        mock_ocr_page.return_value = "OCR text from scanned page"
        text = service.extract_text(empty_pdf_path)
        mock_ocr_page.assert_called_once()

    @patch("services.pdf_service.PdfService._ocr_page")
    def test_ocr_fallback_returns_text(self, mock_ocr_page, service, empty_pdf_path):
        mock_ocr_page.return_value = "Scanned content here"
        text = service.extract_text(empty_pdf_path)
        assert "Scanned content here" in text

    @patch("services.pdf_service.PdfService._ocr_page")
    def test_raises_when_no_text_can_be_extracted(self, mock_ocr_page, service, empty_pdf_path):
        mock_ocr_page.return_value = ""

        with pytest.raises(ValueError, match="No text could be extracted from the PDF"):
            service.extract_text(empty_pdf_path)


class TestIsScannedPage:
    def test_page_with_text_not_scanned(self, service, digital_pdf_path):
        import pdfplumber

        with pdfplumber.open(digital_pdf_path) as pdf:
            assert not service.is_scanned_page(pdf.pages[0])

    def test_page_without_text_is_scanned(self, service, empty_pdf_path):
        import pdfplumber

        with pdfplumber.open(empty_pdf_path) as pdf:
            assert service.is_scanned_page(pdf.pages[0])
