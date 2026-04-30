"""Tesseract OCR adapter — offline fallback only."""

from __future__ import annotations

import logging
import os
import shutil

from .base import (
    OcrPage,
    OcrResult,
    assert_path_exists,
    is_image,
    is_pdf,
    load_image_gray,
    pdf_to_image_paths,
    preprocess_image,
)
from PIL import Image

logger = logging.getLogger(__name__)


class TesseractProvider:
    """Local Tesseract OCR — last-resort offline fallback.

    Confidence is always 0.5 (Tesseract CLI does not return word-level
    confidence in a reliable machine-readable form via pytesseract image_to_string).
    """

    name = "tesseract"
    confidence_threshold = 0.0  # always accept whatever Tesseract returns

    def _ocr_array(self, image) -> str:
        if shutil.which("tesseract") is None:
            raise RuntimeError("Tesseract binary not found on PATH")
        try:
            import pytesseract
        except ImportError as exc:
            raise RuntimeError("pytesseract not installed") from exc
        pil_image = Image.fromarray(image)
        return pytesseract.image_to_string(pil_image, config="--psm 6").strip()

    def _ocr_image(self, path: str) -> str:
        gray = load_image_gray(path)
        preprocessed = preprocess_image(gray)
        return self._ocr_array(preprocessed)

    def extract(self, path: str) -> OcrResult:
        assert_path_exists(path)

        if is_pdf(path):
            tmp_paths = pdf_to_image_paths(path)
            page_texts: list[str] = []
            for tmp_path in tmp_paths:
                try:
                    page_texts.append(self._ocr_image(tmp_path))
                except Exception as exc:
                    logger.warning("Tesseract: page OCR failed — %s", exc)
                    page_texts.append("")
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
            combined = "\n\n".join(page_texts)
            confidence = 0.5 if combined.strip() else 0.0
            ocr_pages = tuple(
                OcrPage(index=i, markdown=t, confidence=0.5 if t.strip() else 0.0)
                for i, t in enumerate(page_texts)
            )
            return OcrResult(text=combined, confidence=confidence, provider=self.name,
                             page_data=ocr_pages)

        if is_image(path):
            text = self._ocr_image(path)
            confidence = 0.5 if text else 0.0
            return OcrResult(text=text, confidence=confidence, provider=self.name,
                             page_data=(OcrPage(index=0, markdown=text, confidence=confidence),))

        raise ValueError(f"Unsupported file type: {path}")
