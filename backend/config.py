"""Application configuration loaded from environment variables."""

import os
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
