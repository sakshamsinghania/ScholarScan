# =============================================================================
# ocr_google_vision.py — Handwritten Text Extraction (Google Cloud Vision API)
# =============================================================================
# Dependencies:
#   google-cloud-vision, opencv-python-headless, Pillow, pdf2image
#   System: poppler-utils (for PDF page rendering)
#
# Install:
#   pip install google-cloud-vision opencv-python-headless Pillow pdf2image
# =============================================================================

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

__all__ = ["extract_text"]

logger = logging.getLogger(__name__)

_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"})
_PDF_EXTENSION = ".pdf"


# --------------------------------------------------------------------------- #
#  Google Vision client setup                                                  #
# --------------------------------------------------------------------------- #

def _get_vision_client(credentials_path: str | None = None):
    """Build and return a Google Vision ImageAnnotatorClient.

    Args:
        credentials_path: Path to the service account JSON key file.
                          If None, falls back to GOOGLE_APPLICATION_CREDENTIALS
                          environment variable.
    """
    from google.cloud import vision
    from google.oauth2 import service_account

    if credentials_path:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return vision.ImageAnnotatorClient(credentials=credentials)

    # Fallback: use GOOGLE_APPLICATION_CREDENTIALS env var
    return vision.ImageAnnotatorClient()


# --------------------------------------------------------------------------- #
#  Image loading & preprocessing                                               #
# --------------------------------------------------------------------------- #

def _load_image(image_path: str) -> np.ndarray:
    """Load image from disk and convert to grayscale NumPy array.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file cannot be decoded as an image.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(
            f"Could not decode image at: {image_path}. "
            "Ensure it is a valid image file (JPG, PNG, etc.)."
        )
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def _deskew(image: np.ndarray) -> np.ndarray:
    """Detect and correct tilt in a binarized image."""
    ys, xs = np.where(image == 0)
    coords = np.column_stack((xs, ys))
    if coords.size == 0:
        return image

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    h, w = image.shape
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        image,
        rotation_matrix,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def _preprocess_image(image: np.ndarray) -> np.ndarray:
    """Full image preprocessing pipeline before sending to Vision API.

    Steps:
      1. Gaussian blur      → removes high-frequency noise
      2. Adaptive threshold → converts to clean black/white
      3. Deskew             → straightens tilted text
      4. Morphological open → removes small specks / pen artifacts

    Note: Vision API works well on the original image too,
    but preprocessing still improves accuracy on low-quality handwritten sheets.
    """
    blurred = cv2.GaussianBlur(image, (3, 3), 0)
    binary = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=11,
        C=2,
    )
    deskewed = _deskew(binary)
    kernel = np.ones((1, 1), np.uint8)
    cleaned = cv2.morphologyEx(deskewed, cv2.MORPH_OPEN, kernel)
    return cleaned


def _numpy_to_png_bytes(image: np.ndarray) -> bytes:
    """Encode a NumPy image array to PNG bytes for the Vision API."""
    success, buffer = cv2.imencode(".png", image)
    if not success:
        raise ValueError("Failed to encode preprocessed image to PNG bytes.")
    return buffer.tobytes()


# --------------------------------------------------------------------------- #
#  Google Vision OCR execution                                                 #
# --------------------------------------------------------------------------- #

def _run_vision_ocr(image: np.ndarray, client) -> str:
    """Send a preprocessed image to Cloud Vision and return extracted text.

    Uses DOCUMENT_TEXT_DETECTION — better than TEXT_DETECTION for dense,
    multi-line handwritten content like answer sheets.
    """
    from google.cloud import vision

    image_bytes = _numpy_to_png_bytes(image)
    vision_image = vision.Image(content=image_bytes)

    response = client.document_text_detection(image=vision_image)

    if response.error.message:
        raise RuntimeError(
            f"Google Vision API error: {response.error.message}\n"
            "Check API enablement and service account permissions."
        )

    # full_text_annotation gives the complete extracted string directly
    annotation = response.full_text_annotation
    return annotation.text.strip() if annotation else ""


def _run_tesseract_ocr(image: np.ndarray) -> str:
    """Fallback OCR using the local Tesseract binary."""
    if shutil.which("tesseract") is None:
        raise RuntimeError("Local Tesseract OCR is not installed")

    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("pytesseract is not installed") from exc

    pil_image = Image.fromarray(image)
    return pytesseract.image_to_string(pil_image, config="--psm 6").strip()


def _extract_with_fallback(image: np.ndarray, client) -> str:
    """Prefer Google Vision and fall back to local Tesseract when unavailable."""
    vision_error: Exception | None = None

    if client is not None:
        try:
            text = _run_vision_ocr(image, client)
            if text:
                return text
            logger.warning(
                "Google Vision returned no text; falling back to local Tesseract OCR."
            )
        except Exception as exc:
            vision_error = exc
            logger.warning(
                "Google Vision OCR failed; falling back to local Tesseract OCR. Error: %s",
                exc,
            )

    text = _run_tesseract_ocr(image)
    if text:
        return text

    if vision_error is not None:
        raise RuntimeError(
            "Both Google Vision OCR and local Tesseract OCR failed to extract text."
        ) from vision_error

    return ""


def _ocr_single_image(image_path: str, client) -> str:
    """Run the full OCR pipeline on a single image file."""
    raw = _load_image(image_path)
    clean = _preprocess_image(raw)
    return _extract_with_fallback(clean, client)


# --------------------------------------------------------------------------- #
#  PDF page extraction via pdf2image                                           #
# --------------------------------------------------------------------------- #

def _ocr_pdf(pdf_path: str, client) -> str:
    """Extract text from a PDF by converting each page to an image and running OCR.

    Uses pdf2image (poppler) to render pages at 300 DPI.
    Falls back to empty string per page on errors.
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        raise ImportError(
            "pdf2image is required for PDF OCR. "
            "Install it with: pip install pdf2image"
        )

    logger.info("Converting PDF to images for OCR: %s", pdf_path)
    images = convert_from_path(pdf_path, dpi=300)

    page_texts: list[str] = []
    for i, pil_image in enumerate(images):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            pil_image.save(tmp, format="PNG")
            tmp_path = tmp.name

        try:
            text = _ocr_single_image(tmp_path, client)
            page_texts.append(text)
            logger.debug("Page %d: extracted %d chars", i + 1, len(text))
        except Exception:
            logger.warning("OCR failed for page %d of %s", i + 1, pdf_path)
            page_texts.append("")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    return "\n\n".join(page_texts)


# --------------------------------------------------------------------------- #
#  Public API                                                                  #
# --------------------------------------------------------------------------- #

def extract_text(
    image_path: str,
    credentials_path: str | None = None,
    debug: bool = False,
) -> str:
    """Extract text from an image or PDF file using Google Cloud Vision API.

    Args:
        image_path:        Path to an image file (JPG/PNG/etc.) or PDF.
        credentials_path:  Path to the service account JSON key file.
                           If None, uses GOOGLE_APPLICATION_CREDENTIALS env var.
        debug:             If True, logs intermediate step info.

    Returns:
        Extracted text as a plain string.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file type is unsupported or image cannot be decoded.
        RuntimeError: If the Vision API returns an error.
    """
    path = Path(image_path)
    suffix = path.suffix.lower()

    if debug:
        logger.info("OCR starting: %s (type: %s)", image_path, suffix)

    # Build client once and reuse across all pages
    try:
        client = _get_vision_client(credentials_path)
    except Exception as exc:
        logger.warning(
            "Failed to initialize Google Vision client; using local Tesseract OCR only. Error: %s",
            exc,
        )
        client = None

    if suffix == _PDF_EXTENSION:
        text = _ocr_pdf(image_path, client)
    elif suffix in _IMAGE_EXTENSIONS:
        text = _ocr_single_image(image_path, client)
    else:
        raise ValueError(
            f"Unsupported file type: '{suffix}'. "
            f"Supported: {', '.join(sorted(_IMAGE_EXTENSIONS | {_PDF_EXTENSION}))}"
        )

    if debug:
        word_count = len(text.split()) if text else 0
        logger.info("OCR complete: %d words extracted", word_count)

    return text


# --------------------------------------------------------------------------- #
#  CLI entry point                                                             #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) < 2:
        print(f"Usage: python -m core.ocr_google_vision <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "") or None

    result = extract_text(image_path, credentials_path=credentials_path, debug=True)

    print("=" * 50)
    print("EXTRACTED TEXT:")
    print("=" * 50)
    print(result)
