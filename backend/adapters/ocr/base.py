"""OCR provider Protocol and shared utilities."""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"})
_PDF_EXTENSION = ".pdf"


@dataclass(frozen=True)
class OcrPage:
    index: int
    markdown: str
    confidence: float | None = None


@dataclass
class OcrResult:
    text: str
    confidence: float  # 0.0–1.0; heuristic for providers that lack native scores
    provider: str
    page_data: tuple[OcrPage, ...] = ()
    metadata: dict = field(default_factory=dict)

    @property
    def page_count(self) -> int:
        return max(1, len(self.page_data))


@runtime_checkable
class OcrProvider(Protocol):
    """Minimal interface every OCR adapter must satisfy."""

    name: str
    confidence_threshold: float  # short-circuit cascade when result.confidence >= this

    def extract(self, path: str) -> OcrResult:
        """Extract text from an image or PDF file.

        Args:
            path: Absolute path to image or PDF.

        Returns:
            OcrResult with extracted text and confidence.

        Raises:
            FileNotFoundError: If file does not exist.
            RuntimeError: If extraction fails unrecoverably.
        """
        ...


# ---------------------------------------------------------------------------
# Shared image preprocessing (same pipeline used by original Google Vision code)
# ---------------------------------------------------------------------------

def load_image_gray(image_path: str) -> np.ndarray:
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Cannot decode image: {image_path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def _deskew(image: np.ndarray) -> np.ndarray:
    ys, xs = np.where(image == 0)
    coords = np.column_stack((xs, ys))
    if coords.size == 0:
        return image
    angle = cv2.minAreaRect(coords)[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    h, w = image.shape
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def preprocess_image(image: np.ndarray) -> np.ndarray:
    blurred = cv2.GaussianBlur(image, (3, 3), 0)
    binary = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    deskewed = _deskew(binary)
    kernel = np.ones((1, 1), np.uint8)
    return cv2.morphologyEx(deskewed, cv2.MORPH_OPEN, kernel)


def numpy_to_png_bytes(image: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("Failed to encode image to PNG bytes.")
    return buf.tobytes()


def pdf_to_image_paths(pdf_path: str, dpi: int = 300) -> list[str]:
    """Convert PDF pages to temp PNG files. Caller must delete them."""
    try:
        from pdf2image import convert_from_path
    except ImportError as exc:
        raise ImportError("pdf2image required for PDF OCR") from exc

    images = convert_from_path(pdf_path, dpi=dpi)
    paths: list[str] = []
    for pil_image in images:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        pil_image.save(tmp, format="PNG")
        tmp.close()
        paths.append(tmp.name)
    return paths


def is_image(path: str) -> bool:
    return Path(path).suffix.lower() in _IMAGE_EXTENSIONS


def is_pdf(path: str) -> bool:
    return Path(path).suffix.lower() == _PDF_EXTENSION


def assert_path_exists(path: str) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
