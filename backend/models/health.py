"""Pydantic schema for health check response."""

from pydantic import BaseModel


class CapabilityStatus(BaseModel):
    """Capability-level availability flags."""

    ocr: bool
    semantic_similarity: bool
    llm: bool
    pdf: bool


class SupportedModes(BaseModel):
    """User-visible grading modes derived from component readiness."""

    manual_assessment: bool
    auto_reference_generation: bool
    multi_question_assessment: bool


class HealthStatus(BaseModel):
    """JSON response shape for GET /api/health."""

    status: str
    ocr_available: bool
    tesseract_available: bool
    vision_credentials_configured: bool
    sbert_loaded: bool
    spacy_model_loaded: bool
    llm_configured: bool
    pdf_support: bool
    capabilities: CapabilityStatus
    supported_modes: SupportedModes
    timestamp: str
