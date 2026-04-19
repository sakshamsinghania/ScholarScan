"""Tests for backend runtime configuration helpers."""

from flask import Flask
from unittest.mock import patch

import app as backend_app
from config import Config


class TestRuntimePort:
    def test_runtime_port_defaults_to_5050(self, monkeypatch):
        monkeypatch.delenv("PORT", raising=False)

        assert backend_app.get_runtime_port() == 5050

    def test_runtime_port_uses_env_value(self, monkeypatch):
        monkeypatch.setenv("PORT", "5099")

        assert backend_app.get_runtime_port() == 5099

    def test_runtime_port_falls_back_when_env_is_invalid(self, monkeypatch):
        monkeypatch.setenv("PORT", "not-a-number")

        assert backend_app.get_runtime_port() == 5050


class TestLlmConfiguration:
    def test_config_defaults_cover_free_tier_rate_limits(self):
        assert Config.LLM_MIN_INTERVAL_SECONDS == 2
        assert Config.LLM_DAILY_REQUEST_LIMIT == 14000
        assert Config.LLM_MAX_RETRIES == 5
        assert Config.LLM_BACKOFF_BASE_SECONDS == 2
        assert Config.LLM_BACKOFF_MAX_SECONDS == 60

    def test_build_llm_service_passes_rate_limit_settings(self):
        app = Flask(__name__)
        app.config.update(
            GROQ_API_KEY="test-key",
            GROQ_BASE_URL="https://api.groq.com/openai/v1",
            LLM_MODEL="llama-3.3-70b-versatile",
            LLM_MIN_INTERVAL_SECONDS=2,
            LLM_DAILY_REQUEST_LIMIT=14000,
            LLM_MAX_RETRIES=5,
            LLM_BACKOFF_BASE_SECONDS=2,
            LLM_BACKOFF_MAX_SECONDS=60,
            LLM_CACHE_PATH="uploads/test-groq-cache.json",
        )

        with patch("services.llm_service.LlmService") as llm_service_cls:
            backend_app._build_llm_service(app)

        llm_service_cls.assert_called_once_with(
            api_key="test-key",
            model="llama-3.3-70b-versatile",
            base_url="https://api.groq.com/openai/v1",
            min_interval_seconds=2,
            daily_request_limit=14000,
            max_retries=5,
            backoff_base_seconds=2,
            backoff_max_seconds=60,
            cache_path="uploads/test-groq-cache.json",
        )
