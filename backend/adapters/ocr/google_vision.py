"""Google Cloud Vision OCR adapter."""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Optional

from .base import (
    OcrPage,
    OcrResult,
    assert_path_exists,
    is_image,
    is_pdf,
    load_image_gray,
    numpy_to_png_bytes,
    pdf_to_image_paths,
    preprocess_image,
)

logger = logging.getLogger(__name__)

_VISION_REST_URL = "https://vision.googleapis.com/v1/images:annotate"


class GoogleVisionProvider:
    """Wraps Google Cloud Vision DOCUMENT_TEXT_DETECTION.

    Supports two auth modes:
    - api_key: uses Vision REST API with a simple API key
    - credentials_path / ADC: uses google-cloud-vision SDK with service account

    Returns confidence averaged from per-word confidence scores when available;
    falls back to a fixed heuristic (0.8) when annotation lacks word scores.
    """

    name = "vision"
    confidence_threshold = 0.60

    def __init__(self, credentials_path: Optional[str] = None,
                 api_key: Optional[str] = None) -> None:
        self._credentials_path = credentials_path
        self._api_key = api_key
        self._client = None
        if not api_key:
            self._client = self._build_client()

    def _build_client(self):
        try:
            from google.cloud import vision
            from google.oauth2 import service_account

            if self._credentials_path:
                creds = service_account.Credentials.from_service_account_file(
                    self._credentials_path,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                return vision.ImageAnnotatorClient(credentials=creds)
            return vision.ImageAnnotatorClient()
        except Exception as exc:
            logger.warning("GoogleVisionProvider: client init failed — %s", exc)
            return None

    def _ocr_bytes_rest(self, image_bytes: bytes) -> tuple[str, float]:
        """Call Vision REST API with API key and return (text, confidence)."""
        import urllib.request

        b64 = base64.b64encode(image_bytes).decode("ascii")
        payload = json.dumps({
            "requests": [{
                "image": {"content": b64},
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
            }]
        }).encode("utf-8")

        url = f"{_VISION_REST_URL}?key={self._api_key}"
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        response = data.get("responses", [{}])[0]
        if "error" in response:
            raise RuntimeError(f"Vision API error: {response['error'].get('message', response['error'])}")

        annotation = response.get("fullTextAnnotation", {})
        if not annotation:
            return "", 0.0

        text = annotation.get("text", "").strip()

        confidences = [
            w.get("confidence", 0)
            for page in annotation.get("pages", [])
            for block in page.get("blocks", [])
            for para in block.get("paragraphs", [])
            for w in para.get("words", [])
            if w.get("confidence", 0) > 0
        ]
        confidence = sum(confidences) / len(confidences) if confidences else (0.8 if text else 0.0)
        return text, confidence

    def _ocr_bytes(self, image_bytes: bytes) -> tuple[str, float]:
        """Call Vision API and return (text, confidence)."""
        if self._api_key:
            return self._ocr_bytes_rest(image_bytes)

        if self._client is None:
            raise RuntimeError("Google Vision client not available")

        from google.cloud import vision

        vision_image = vision.Image(content=image_bytes)
        response = self._client.document_text_detection(image=vision_image)

        if response.error.message:
            raise RuntimeError(f"Vision API error: {response.error.message}")

        annotation = response.full_text_annotation
        if not annotation:
            return "", 0.0

        text = annotation.text.strip()

        # Average per-word confidence when available
        confidences = [
            w.confidence
            for page in annotation.pages
            for block in page.blocks
            for para in block.paragraphs
            for w in para.words
            if hasattr(w, "confidence") and w.confidence > 0
        ]
        confidence = sum(confidences) / len(confidences) if confidences else (0.8 if text else 0.0)
        return text, confidence

    def _ocr_image(self, path: str) -> tuple[str, float]:
        gray = load_image_gray(path)
        preprocessed = preprocess_image(gray)
        image_bytes = numpy_to_png_bytes(preprocessed)
        return self._ocr_bytes(image_bytes)

    def extract(self, path: str) -> OcrResult:
        assert_path_exists(path)

        if is_pdf(path):
            tmp_paths = pdf_to_image_paths(path)
            page_texts: list[str] = []
            all_confidences: list[float] = []
            for tmp_path in tmp_paths:
                try:
                    text, conf = self._ocr_image(tmp_path)
                    page_texts.append(text)
                    all_confidences.append(conf)
                except Exception as exc:
                    logger.warning("GoogleVision: page OCR failed — %s", exc)
                    page_texts.append("")
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
            combined = "\n\n".join(page_texts)
            avg_conf = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
            ocr_pages = tuple(
                OcrPage(index=i, markdown=t, confidence=all_confidences[i] if i < len(all_confidences) else None)
                for i, t in enumerate(page_texts)
            )
            return OcrResult(text=combined, confidence=avg_conf, provider=self.name,
                             page_data=ocr_pages)

        if is_image(path):
            text, conf = self._ocr_image(path)
            return OcrResult(text=text, confidence=conf, provider=self.name,
                             page_data=(OcrPage(index=0, markdown=text, confidence=conf),))

        raise ValueError(f"Unsupported file type: {path}")
