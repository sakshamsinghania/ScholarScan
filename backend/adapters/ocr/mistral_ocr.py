"""Mistral OCR adapter (mistral-ocr-latest / MISTRAL_OCR_MODEL)."""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Optional

from .base import OcrPage, OcrResult, assert_path_exists, is_image, is_pdf

logger = logging.getLogger(__name__)

_MIME_BY_SUFFIX = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


class MistralOcrProvider:
    """Mistral OCR primary provider using MISTRAL_OCR_MODEL.

    Default model: mistral-ocr-latest (override via MISTRAL_OCR_MODEL env var).
    Confidence derived from average_page_confidence_score when available;
    falls back to heuristic 0.92 when text found.
    """

    name = "mistral"
    confidence_threshold = 0.70

    def __init__(self, api_key: str, model_name: Optional[str] = None) -> None:
        self._api_key = api_key
        self._model_name = model_name or os.getenv("MISTRAL_OCR_MODEL", "mistral-ocr-latest")
        self._client = self._build_client()

    def _build_client(self):
        try:
            from mistralai.client import Mistral
            return Mistral(api_key=self._api_key)
        except Exception as exc:
            logger.warning("MistralOcr: client init failed — %s", exc)
            return None

    def _encode(self, path: str) -> tuple[str, str]:
        suffix = Path(path).suffix.lower()
        mime = _MIME_BY_SUFFIX.get(suffix)
        if mime is None:
            raise ValueError(f"Unsupported file type: {path}")
        with open(path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode("ascii")
        return mime, b64

    def _build_document(self, path: str) -> dict:
        mime, b64 = self._encode(path)
        data_uri = f"data:{mime};base64,{b64}"
        if is_pdf(path):
            return {"type": "document_url", "document_url": data_uri}
        return {"type": "image_url", "image_url": data_uri}

    @staticmethod
    def _page_confidence(page) -> Optional[float]:
        scores = getattr(page, "confidence_scores", None)
        if scores is None:
            return None
        avg = getattr(scores, "average_page_confidence_score", None)
        return float(avg) if avg is not None else None

    def extract(self, path: str) -> OcrResult:
        assert_path_exists(path)
        if not (is_pdf(path) or is_image(path)):
            raise ValueError(f"Unsupported file type: {path}")
        if self._client is None:
            raise RuntimeError("Mistral OCR client not available")

        document = self._build_document(path)
        try:
            response = self._client.ocr.process(
                model=self._model_name,
                document=document,
                confidence_scores_granularity="page",
            )
        except Exception as exc:
            raise RuntimeError(f"Mistral OCR request failed: {exc}") from exc

        pages = getattr(response, "pages", []) or []
        page_texts = [(getattr(p, "markdown", "") or "").strip() for p in pages]
        combined = "\n\n".join(t for t in page_texts if t).strip()

        page_scores = [self._page_confidence(p) for p in pages]
        real_scores = [s for s in page_scores if s is not None]
        if real_scores:
            confidence = sum(real_scores) / len(real_scores)
        else:
            confidence = 0.92 if combined else 0.0

        ocr_pages = tuple(
            OcrPage(index=i, markdown=page_texts[i], confidence=page_scores[i])
            for i in range(len(pages))
        )

        return OcrResult(
            text=combined,
            confidence=confidence,
            provider=self.name,
            page_data=ocr_pages,
            metadata={"model": self._model_name},
        )
