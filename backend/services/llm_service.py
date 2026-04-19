"""Generate model answers using Groq's OpenAI-compatible LLM API."""

import hashlib
import json
import logging

from openai import OpenAI

from services.groq_request_coordinator import GroqRequestCoordinator

logger = logging.getLogger(__name__)

_DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
_LEGACY_GEMINI_MODEL_PREFIXES = ("gemini-", "models/gemini-")

_SYSTEM_PROMPT = (
    "You are an expert academic evaluator. "
    "Given a question from a student exam, provide a comprehensive model answer "
    "that covers all key concepts, technical terms, and reasoning. "
    "Keep the answer concise (3-5 sentences) and factually accurate. "
    "Do NOT include the question in your response."
)


class LlmService:
    """
    Generates model answers via Groq.
    Degrades gracefully — returns empty string on failure so callers can skip.
    """

    def __init__(
        self,
        api_key: str,
        model: str = _DEFAULT_GROQ_MODEL,
        base_url: str = "https://api.groq.com/openai/v1",
        min_interval_seconds: float = 2,
        daily_request_limit: int = 14000,
        max_retries: int = 5,
        backoff_base_seconds: float = 2,
        backoff_max_seconds: float = 60,
        cache_path: str = "uploads/groq-cache.json",
        time_fn=None,
        monotonic_fn=None,
        sleep_fn=None,
        jitter_fn=None,
        coordinator: GroqRequestCoordinator | None = None,
    ):
        self._api_key = api_key
        self._model = self._resolve_model(model)
        self._base_url = base_url
        self._client = None
        self._owns_coordinator = coordinator is None
        self._coordinator = coordinator

        if api_key:
            try:
                self._client = OpenAI(api_key=api_key, base_url=base_url)
                if self._coordinator is None:
                    self._coordinator = GroqRequestCoordinator(
                        cache_path=cache_path,
                        min_interval_seconds=min_interval_seconds,
                        daily_request_limit=daily_request_limit,
                        max_retries=max_retries,
                        backoff_base_seconds=backoff_base_seconds,
                        backoff_max_seconds=backoff_max_seconds,
                        time_fn=time_fn,
                        monotonic_fn=monotonic_fn,
                        sleep_fn=sleep_fn,
                        jitter_fn=jitter_fn,
                    )
            except Exception as e:
                logger.warning("Failed to initialize Groq client: %s", e)
                if self._owns_coordinator and self._coordinator is not None:
                    self._coordinator.close()
                    self._coordinator = None

    @property
    def is_configured(self) -> bool:
        """Check if the LLM service has a valid API key."""
        return bool(self._api_key and self._client)

    def generate_model_answer(self, question: str) -> str:
        """
        Generate a concise model answer for a single question.

        Returns empty string if the question is empty, the client isn't
        configured, or the API call fails.
        """
        if not question or not question.strip():
            return ""

        if not self.is_configured:
            logger.warning("LLM not configured — skipping answer generation")
            return ""

        cache_key = self._build_cache_key(question)
        if not self._coordinator:
            return ""

        return self._coordinator.submit(
            cache_key=cache_key,
            request_fn=lambda: self._request_model_answer(question),
        )

    def generate_batch_answers(self, questions: list[str]) -> list[str]:
        """Generate model answers for multiple questions using serialized calls."""
        if not questions:
            return []

        return [self.generate_model_answer(question) for question in questions]

    def close(self) -> None:
        """Release background resources owned by the service."""
        if self._owns_coordinator and self._coordinator is not None:
            self._coordinator.close()
            self._coordinator = None

    @staticmethod
    def _normalize_question(question: str) -> str:
        return " ".join(question.split())

    @staticmethod
    def _resolve_model(model: str) -> str:
        normalized_model = (model or "").strip()
        if not normalized_model:
            return _DEFAULT_GROQ_MODEL

        if normalized_model.lower().startswith(_LEGACY_GEMINI_MODEL_PREFIXES):
            logger.warning(
                "Configured LLM model '%s' is a legacy Gemini value; falling back to Groq default '%s'",
                normalized_model,
                _DEFAULT_GROQ_MODEL,
            )
            return _DEFAULT_GROQ_MODEL

        return normalized_model

    def _build_cache_key(self, question: str) -> str:
        normalized_question = self._normalize_question(question)
        identity = json.dumps(
            {
                "model": self._model,
                "system_prompt": _SYSTEM_PROMPT,
                "question": normalized_question,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()

    def _request_model_answer(self, question: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Question: {self._normalize_question(question)}"},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        return (response.choices[0].message.content or "").strip()
