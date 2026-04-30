"""Tests for OCR service provider wiring."""

from unittest.mock import patch

from services.ocr_service import OcrService


class TestOcrService:
    def test_vision_provider_receives_api_key(self):
        with patch("adapters.ocr.mistral_ocr.MistralOcrProvider"), patch(
            "adapters.ocr.google_vision.GoogleVisionProvider"
        ) as vision_provider_cls, patch(
            "adapters.ocr.tesseract.TesseractProvider"
        ):
            OcrService(
                {
                    "OCR_CASCADE": "vision",
                    "GOOGLE_VISION_API_KEY": "test-vision-key",
                }
            )

        vision_provider_cls.assert_called_once_with(
            credentials_path=None,
            api_key="test-vision-key",
        )
