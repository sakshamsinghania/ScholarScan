"""Flask application factory — creates and configures the app."""

import logging
import os
import re
import shutil
from functools import wraps

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, verify_jwt_in_request, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from services.result_storage_service import ResultStorageService
from services.progress_service import ProgressService
from services.user_service import UserService

DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)
LOCAL_DEV_ORIGIN_PATTERN = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$")
DEFAULT_BACKEND_PORT = 5050

# Module-level limiter with deferred app init — importable by route modules
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")


def _is_production() -> bool:
    """Best-effort check for production runtime."""
    env = os.getenv("FLASK_ENV", "").lower()
    return env == "production"


def get_runtime_port() -> int:
    """Return the backend port, with a collision-resistant local default."""
    configured = os.getenv("PORT", "").strip()
    if not configured:
        return DEFAULT_BACKEND_PORT

    try:
        port = int(configured)
    except ValueError:
        return DEFAULT_BACKEND_PORT

    return port if 0 < port < 65536 else DEFAULT_BACKEND_PORT


def _get_cors_origins() -> list[str | re.Pattern[str]]:
    """Read allowed frontend origins from env, with sensible local defaults."""
    configured = os.getenv("CORS_ORIGIN")
    origins = (
        [origin.strip() for origin in configured.split(",") if origin.strip()]
        if configured
        else list(DEFAULT_CORS_ORIGINS)
    )

    if _is_production() and "*" in origins:
        logging.getLogger(__name__).warning(
            "CORS_ORIGIN contains '*' in production — this is insecure"
        )
        origins = [o for o in origins if o != "*"]

    if not _is_production():
        origins.append(LOCAL_DEV_ORIGIN_PATTERN)

    return origins


def auth_required_conditional(fn):
    """Skip JWT verification when AUTH_REQUIRED is false."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        from flask import current_app
        if current_app.config.get("AUTH_REQUIRED", True):
            verify_jwt_in_request()
        return fn(*args, **kwargs)
    return wrapper


def get_current_user_id() -> str | None:
    """Return JWT identity if auth is active, else None."""
    from flask import current_app
    if not current_app.config.get("AUTH_REQUIRED", True):
        return None
    try:
        return get_jwt_identity()
    except Exception:
        return None


def _configure_runtime_capabilities(app: Flask, testing: bool) -> None:
    """Record coarse capability flags for health reporting."""
    tesseract_available = shutil.which("tesseract") is not None
    vision_credentials_configured = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

    app.config["TESSERACT_AVAILABLE"] = tesseract_available
    app.config["VISION_CREDENTIALS_CONFIGURED"] = vision_credentials_configured
    app.config["OCR_AVAILABLE"] = testing or tesseract_available or vision_credentials_configured
    app.config["PDF_SUPPORT"] = True


def _build_llm_service(app: Flask):
    """Create the shared LLM service with Groq free-tier safeguard settings."""
    from services.llm_service import LlmService

    return LlmService(
        api_key=app.config["GROQ_API_KEY"],
        model=app.config["LLM_MODEL"],
        base_url=app.config["GROQ_BASE_URL"],
        min_interval_seconds=app.config["LLM_MIN_INTERVAL_SECONDS"],
        daily_request_limit=app.config["LLM_DAILY_REQUEST_LIMIT"],
        max_retries=app.config["LLM_MAX_RETRIES"],
        backoff_base_seconds=app.config["LLM_BACKOFF_BASE_SECONDS"],
        backoff_max_seconds=app.config["LLM_BACKOFF_MAX_SECONDS"],
        cache_path=app.config["LLM_CACHE_PATH"],
    )


def create_app(testing: bool = False) -> Flask:
    """
    Application factory. Creates a Flask app with all blueprints registered.

    Args:
        testing: If True, uses mock services (no ML model loading).
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={r"/api/*": {"origins": _get_cors_origins()}})
    _configure_runtime_capabilities(app, testing)

    # Auth
    jwt = JWTManager(app)
    user_service = UserService()
    app.config["USER_SERVICE"] = user_service

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Token has expired", "code": 401}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        return jsonify({"error": "Invalid token", "code": 401}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error_string):
        return jsonify({"error": "Authorization required", "code": 401}), 401

    # Rate limiting
    limiter.init_app(app)
    app.config["LIMITER"] = limiter

    # Ensure upload folder exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize shared services
    result_store = ResultStorageService(max_entries=app.config["RESULT_STORE_MAX_ENTRIES"])
    progress_service = ProgressService(task_ttl_seconds=app.config["TASK_TTL_SECONDS"])
    app.config["RESULT_STORE"] = result_store
    app.config["PROGRESS_SERVICE"] = progress_service

    if testing:
        _register_mock_services(app, result_store)
    else:
        _register_real_services(app, result_store)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.health import health_bp
    from routes.assess import assess_bp
    from routes.results import results_bp
    from routes.progress import progress_bp
    from routes.task_result import task_result_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(assess_bp)
    app.register_blueprint(results_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(task_result_bp)

    return app


def _register_real_services(app: Flask, result_store: ResultStorageService) -> None:
    """Wire up real core modules — loads ML models."""
    from core.ocr_google_vision import extract_text
    from core.nlp import preprocess_for_tfidf, preprocess_for_sbert
    from core.similarity import SBERTSimilarity, compute_similarity
    from core.scoring import score_answer

    from file_handling.file_handler import FileHandler
    from services.assessment_service import AssessmentService
    from services.pdf_service import PdfService
    from services.question_service import QuestionService
    from services.llm_service import LlmService
    from services.evaluation_service import EvaluationService

    sbert_model = SBERTSimilarity(model_name=app.config["SBERT_MODEL_NAME"])

    assessment_service = AssessmentService(
        extract_text_fn=extract_text,
        preprocess_for_tfidf_fn=preprocess_for_tfidf,
        preprocess_for_sbert_fn=preprocess_for_sbert,
        compute_similarity_fn=compute_similarity,
        score_answer_fn=score_answer,
        sbert_model=sbert_model,
        result_store=result_store,
    )

    pdf_service = PdfService(extract_text_fn=extract_text)
    question_service = QuestionService()
    llm_service = _build_llm_service(app)
    evaluation_service = EvaluationService(
        pdf_service=pdf_service,
        question_service=question_service,
        llm_service=llm_service,
        assessment_service=assessment_service,
        result_store=result_store,
        extract_text_fn=extract_text,
    )

    app.config["ASSESSMENT_SERVICE"] = assessment_service
    app.config["EVALUATION_SERVICE"] = evaluation_service
    app.config["LLM_SERVICE"] = llm_service

    app.config["FILE_HANDLER"] = FileHandler(
        upload_folder=app.config["UPLOAD_FOLDER"],
        allowed_extensions=app.config["ALLOWED_EXTENSIONS"],
        max_file_size=app.config["MAX_CONTENT_LENGTH"],
    )

    app.config["SBERT_LOADED"] = sbert_model.is_available
    app.config["LLM_CONFIGURED"] = llm_service.is_configured


def _register_mock_services(app: Flask, result_store: ResultStorageService) -> None:
    """Wire up mock services for testing — no ML models loaded."""
    from unittest.mock import MagicMock
    from file_handling.file_handler import FileHandler
    from services.assessment_service import AssessmentService
    from services.pdf_service import PdfService
    from services.question_service import QuestionService
    from services.llm_service import LlmService
    from services.evaluation_service import EvaluationService

    mock_assessment = MagicMock(
        raw_ocr_text="mock ocr text",
        cleaned_text="mock cleaned text",
        tfidf_score=0.5,
        sbert_score=0.7,
        combined_score=0.65,
        keyword_overlap=0.6,
        missing_keywords=["keyword1"],
        marks=7.0,
        max_marks=10,
        grade="B",
        feedback="Good answer.",
    )

    mock_extract = MagicMock(return_value="mock ocr text")

    assessment_service = AssessmentService(
        extract_text_fn=mock_extract,
        preprocess_for_tfidf_fn=MagicMock(return_value="mock tfidf text"),
        preprocess_for_sbert_fn=MagicMock(return_value="mock sbert text"),
        compute_similarity_fn=MagicMock(
            return_value={
                "tfidf_score": 0.5,
                "sbert_score": 0.7,
                "combined_score": 0.65,
                "keyword_overlap": 0.6,
                "missing_keywords": ["keyword1"],
            }
        ),
        score_answer_fn=MagicMock(return_value=mock_assessment),
        sbert_model=MagicMock(),
        result_store=result_store,
    )

    pdf_service = PdfService(extract_text_fn=mock_extract)
    question_service = QuestionService()
    llm_service = LlmService(api_key="", model="test")

    evaluation_service = EvaluationService(
        pdf_service=pdf_service,
        question_service=question_service,
        llm_service=llm_service,
        assessment_service=assessment_service,
        result_store=result_store,
        extract_text_fn=mock_extract,
    )

    app.config["ASSESSMENT_SERVICE"] = assessment_service
    app.config["EVALUATION_SERVICE"] = evaluation_service
    app.config["LLM_SERVICE"] = llm_service

    app.config["FILE_HANDLER"] = FileHandler(
        upload_folder=app.config["UPLOAD_FOLDER"],
        allowed_extensions=app.config["ALLOWED_EXTENSIONS"],
        max_file_size=app.config["MAX_CONTENT_LENGTH"],
    )

    app.config["SBERT_LOADED"] = False
    app.config["LLM_CONFIGURED"] = False


if __name__ == "__main__":
    app = create_app()
    app.run(debug=app.config["DEBUG"], port=get_runtime_port())
