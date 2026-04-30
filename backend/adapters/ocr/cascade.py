"""CascadeProvider — wraps OcrService cascade logic as a single pseudo-provider.

Used by the benchmark harness so the cascade pipeline can be benchmarked as one
provider entry alongside individual providers (mistral, vision, tesseract).
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from .base import OcrProvider, OcrResult

logger = logging.getLogger(__name__)

_OFFLINE_FLAG = "Partial"


class CascadeProvider:
    """Pseudo-provider that runs the ScholarScan cascade pipeline.

    Delegates to OcrService which handles retry/timeout/fallback internally.
    Latency is total wall-clock (sum of all provider attempts inside the cascade).
    """

    name = "cascade"
    confidence_threshold = 0.0  # always accept cascade best result
    offline = _OFFLINE_FLAG

    def __init__(self, config: Optional[dict] = None) -> None:
        from services.ocr_service import OcrService

        self._service = OcrService(config or {})

    def extract(self, path: str) -> OcrResult:
        return self._service.extract_result(path)
