"""OCR cascade orchestrator.

Provider chain: mistral → vision → tesseract (default).
Controlled by OCR_CASCADE env / config key.

Each provider gets up to OCR_RETRIES_PER_PROVIDER attempts (tenacity exponential backoff).
Per-provider timeout uses concurrent.futures (thread-safe — works in Celery/non-main threads).
Short-circuits when result.confidence >= provider.confidence_threshold.
Total wall-clock cap: OCR_TOTAL_TIMEOUT_SECONDS (default 120s).
"""

from __future__ import annotations

import concurrent.futures
import logging
import time
from typing import Callable, Optional

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    RetryError,
)

from adapters.ocr.base import OcrProvider, OcrResult

logger = logging.getLogger(__name__)

_PROVIDER_TIMEOUT_SECONDS = 60
_TOTAL_TIMEOUT_SECONDS = 120
_RETRIES_PER_PROVIDER = 2
_DEFAULT_CASCADE = "mistral,vision,tesseract"


def _make_retry_extract(provider: OcrProvider, timeout_s: int, retries: int) -> Callable:
    @retry(
        retry=retry_if_exception_type((RuntimeError, OSError, TimeoutError)),
        stop=stop_after_attempt(retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _extract_with_retry(path: str) -> OcrResult:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(provider.extract, path)
            try:
                return future.result(timeout=timeout_s)
            except concurrent.futures.TimeoutError:
                raise TimeoutError(f"OCR provider timed out after {timeout_s}s")

    return _extract_with_retry


class OcrService:
    """Cascade OCR service.

    Usage::

        ocr = OcrService(config)
        text = ocr.extract("/path/to/image.jpg")  # Callable[[str], str]
    """

    def __init__(self, config: dict) -> None:
        self._cascade_names = [
            n.strip()
            for n in config.get("OCR_CASCADE", _DEFAULT_CASCADE).split(",")
            if n.strip()
        ]
        self._provider_timeout = int(config.get("OCR_PROVIDER_TIMEOUT_SECONDS",
                                                 _PROVIDER_TIMEOUT_SECONDS))
        self._total_timeout = int(config.get("OCR_TOTAL_TIMEOUT_SECONDS",
                                             _TOTAL_TIMEOUT_SECONDS))
        self._retries = int(config.get("OCR_RETRIES_PER_PROVIDER", _RETRIES_PER_PROVIDER))

        mistral_key: str = config.get("MISTRAL_API_KEY", "")
        vision_api_key: Optional[str] = config.get("GOOGLE_VISION_API_KEY") or None
        credentials_path: Optional[str] = config.get("GOOGLE_CREDENTIALS_PATH") or None

        self._providers: dict[str, OcrProvider] = {}
        self._init_providers(mistral_key, credentials_path, vision_api_key)

        logger.info(
            "OcrService cascade: %s",
            " → ".join(n for n in self._cascade_names if n in self._providers),
        )

    def _init_providers(
        self,
        mistral_key: str,
        credentials_path: Optional[str],
        vision_api_key: Optional[str],
    ) -> None:
        from adapters.ocr.mistral_ocr import MistralOcrProvider
        from adapters.ocr.google_vision import GoogleVisionProvider
        from adapters.ocr.tesseract import TesseractProvider

        if mistral_key:
            try:
                self._providers["mistral"] = MistralOcrProvider(api_key=mistral_key)
            except Exception as exc:
                logger.warning("OcrService: mistral init failed — %s", exc)
        else:
            logger.info("OcrService: MISTRAL_API_KEY not set — Mistral provider disabled")

        try:
            self._providers["vision"] = GoogleVisionProvider(
                credentials_path=credentials_path,
                api_key=vision_api_key,
            )
        except Exception as exc:
            logger.warning("OcrService: vision init failed — %s", exc)

        try:
            self._providers["tesseract"] = TesseractProvider()
        except Exception as exc:
            logger.warning("OcrService: tesseract init failed — %s", exc)

    def _active_cascade(self) -> list[OcrProvider]:
        return [
            self._providers[name]
            for name in self._cascade_names
            if name in self._providers
        ]

    def extract_result(self, path: str) -> OcrResult:
        """Run cascade, return OcrResult from first provider that succeeds."""
        providers = self._active_cascade()
        if not providers:
            raise RuntimeError("OcrService: no providers available")

        deadline = time.monotonic() + self._total_timeout
        best: Optional[OcrResult] = None
        last_error: Optional[Exception] = None

        for provider in providers:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logger.warning("OcrService: total timeout reached, stopping cascade")
                break

            timeout = min(self._provider_timeout, int(remaining))
            _try_extract = _make_retry_extract(provider, timeout, self._retries)

            try:
                result = _try_extract(path)
                logger.info(
                    "OcrService: %s → %d chars, confidence=%.2f",
                    provider.name, len(result.text), result.confidence,
                )
                if best is None or result.confidence > best.confidence:
                    best = result
                if result.confidence >= provider.confidence_threshold:
                    logger.debug("OcrService: short-circuit on %s (conf=%.2f >= %.2f)",
                                 provider.name, result.confidence,
                                 provider.confidence_threshold)
                    return result
            except (RetryError, Exception) as exc:
                last_error = exc
                logger.warning("OcrService: %s failed after retries — %s",
                               provider.name, exc)

        if best is not None:
            logger.info("OcrService: cascade exhausted, returning best result from %s",
                        best.provider)
            return best

        raise RuntimeError(
            "OcrService: all providers failed"
        ) from last_error

    def extract(self, path: str) -> str:
        """Drop-in replacement for the legacy extract_text(path) -> str signature."""
        return self.extract_result(path).text
