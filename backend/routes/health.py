"""GET /api/health — System health check."""

from datetime import datetime, timezone

import spacy.util
from flask import Blueprint, current_app, jsonify
from models.health import HealthStatus

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health", methods=["GET"])
def health_check():
    """Return system component status."""
    ocr_available = current_app.config.get("OCR_AVAILABLE", False)
    tesseract_available = current_app.config.get("TESSERACT_AVAILABLE", False)
    vision_credentials_configured = current_app.config.get(
        "VISION_CREDENTIALS_CONFIGURED", False
    )
    sbert_loaded = current_app.config.get("SBERT_LOADED", False)
    llm_configured = current_app.config.get("LLM_CONFIGURED", False)
    spacy_loaded = spacy.util.is_package("en_core_web_sm")
    pdf_support = current_app.config.get("PDF_SUPPORT", True)

    capabilities = {
        "ocr": ocr_available,
        "semantic_similarity": sbert_loaded,
        "llm": llm_configured,
        "pdf": pdf_support,
    }
    supported_modes = {
        "manual_assessment": ocr_available and spacy_loaded,
        "auto_reference_generation": llm_configured,
        "multi_question_assessment": ocr_available and llm_configured and pdf_support,
    }
    all_healthy = all(capabilities.values()) and spacy_loaded
    payload = HealthStatus.model_validate(
        {
            "status": "healthy" if all_healthy else "degraded",
            "ocr_available": ocr_available,
            "tesseract_available": tesseract_available,
            "vision_credentials_configured": vision_credentials_configured,
            "sbert_loaded": sbert_loaded,
            "spacy_model_loaded": spacy_loaded,
            "llm_configured": llm_configured,
            "pdf_support": pdf_support,
            "capabilities": capabilities,
            "supported_modes": supported_modes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    return jsonify(payload.model_dump(mode="json"))
