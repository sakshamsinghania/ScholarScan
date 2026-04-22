"""Application configuration loaded from environment variables."""

import os
import secrets
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Flask application configuration."""

    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
    RESULT_STORE_MAX_ENTRIES = int(os.getenv("RESULT_STORE_MAX_ENTRIES", "500"))
    TASK_TTL_SECONDS = int(os.getenv("TASK_TTL_SECONDS", str(60 * 60)))
    SBERT_MODEL_NAME = os.getenv("SBERT_MODEL_NAME", "all-MiniLM-L6-v2")
    ALLOWED_EXTENSIONS = set(
        os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png,pdf").split(",")
    )
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    LLM_MIN_INTERVAL_SECONDS = float(os.getenv("LLM_MIN_INTERVAL_SECONDS", "2"))
    LLM_DAILY_REQUEST_LIMIT = int(os.getenv("LLM_DAILY_REQUEST_LIMIT", "14000"))
    LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "5"))
    LLM_BACKOFF_BASE_SECONDS = float(os.getenv("LLM_BACKOFF_BASE_SECONDS", "2"))
    LLM_BACKOFF_MAX_SECONDS = float(os.getenv("LLM_BACKOFF_MAX_SECONDS", "60"))
    LLM_CACHE_PATH = os.getenv(
        "LLM_CACHE_PATH",
        os.path.join(UPLOAD_FOLDER, "groq-cache.json"),
    )

    # --- Auth ---
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "3600"))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", str(86400 * 30)))
    )
    AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "true").lower() == "true"

    # --- Rate limiting ---
    RATE_LIMIT_ASSESS = os.getenv("RATE_LIMIT_ASSESS", "30/hour")
    RATE_LIMIT_LOGIN = os.getenv("RATE_LIMIT_LOGIN", "10/minute")
    RATE_LIMIT_GLOBAL = os.getenv("RATE_LIMIT_GLOBAL", "300/hour")

    # --- Persistence (Phase 2) ---
    # Set DATABASE_URL to enable Postgres-backed storage (Postgres or SQLite).
    # Unset → RAM-only fallback (safe for local dev and tests).
    DATABASE_URL = os.getenv("DATABASE_URL", "")

    # --- Job queue (Phase 3) ---
    # Set USE_CELERY=true to route async jobs through Celery/Redis.
    # Unset / false → existing threading fallback (safe for local dev and tests).
    USE_CELERY = os.getenv("USE_CELERY", "false").lower() == "true"
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
