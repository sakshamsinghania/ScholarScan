"""Tests for LlmService — LLM model answer generation via Groq."""

import os
import sys
import threading
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.groq_request_coordinator as groq_request_coordinator_module
from services.llm_service import LlmService


class FakeClock:
    """Deterministic clock for rate-limit and backoff tests."""

    def __init__(self):
        self.current = 0.0
        self.sleep_calls: list[float] = []

    def time(self) -> float:
        return self.current

    def monotonic(self) -> float:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.sleep_calls.append(seconds)
        self.current += seconds


class FakeRateLimitError(Exception):
    """Minimal stand-in for openai.RateLimitError."""

    def __init__(self, message: str = "request failed", retry_after: str | None = None):
        super().__init__(message)
        self.response = MagicMock()
        self.response.headers = {}
        if retry_after is not None:
            self.response.headers["Retry-After"] = retry_after


class FakeAPIStatusError(Exception):
    """Minimal stand-in for openai.APIStatusError."""

    def __init__(self, status_code: int, message: str = "request failed"):
        super().__init__(message)
        self.status_code = status_code
        self.response = MagicMock()
        self.response.headers = {}


def make_openai_response(content: str) -> MagicMock:
    """Create a minimal chat.completions response payload."""
    response = MagicMock()
    choice = MagicMock()
    choice.message.content = content
    response.choices = [choice]
    return response


@pytest.fixture(autouse=True)
def patch_openai_exceptions(monkeypatch):
    monkeypatch.setattr(groq_request_coordinator_module, "RateLimitError", FakeRateLimitError)
    monkeypatch.setattr(groq_request_coordinator_module, "APIStatusError", FakeAPIStatusError)


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI-compatible client."""
    client = MagicMock()
    client.chat.completions.create.return_value = make_openai_response(
        "Photosynthesis is the process by which plants convert light energy."
    )
    return client


@pytest.fixture
def fake_clock():
    return FakeClock()


@pytest.fixture
def service(mock_openai_client, fake_clock, tmp_path):
    with patch("services.llm_service.OpenAI", return_value=mock_openai_client):
        svc = LlmService(
            api_key="test-key",
            model="llama-3.3-70b-versatile",
            base_url="https://api.groq.com/openai/v1",
            min_interval_seconds=2,
            daily_request_limit=14000,
            max_retries=5,
            backoff_base_seconds=2,
            backoff_max_seconds=60,
            cache_path=str(tmp_path / "llm-cache.json"),
            time_fn=fake_clock.time,
            monotonic_fn=fake_clock.monotonic,
            sleep_fn=fake_clock.sleep,
            jitter_fn=lambda _low, _high: 0.0,
        )
    yield svc
    svc.close()


class TestGenerateModelAnswer:
    def test_legacy_gemini_model_name_falls_back_to_default_groq_model(
        self, mock_openai_client, fake_clock, tmp_path
    ):
        with patch("services.llm_service.OpenAI", return_value=mock_openai_client):
            service = LlmService(
                api_key="test-key",
                model="gemini-2.5-flash",
                base_url="https://api.groq.com/openai/v1",
                cache_path=str(tmp_path / "legacy-model-cache.json"),
                time_fn=fake_clock.time,
                monotonic_fn=fake_clock.monotonic,
                sleep_fn=fake_clock.sleep,
                jitter_fn=lambda _low, _high: 0.0,
            )

        try:
            service.generate_model_answer("What is gravity?")

            assert mock_openai_client.chat.completions.create.call_args.kwargs["model"] == (
                "llama-3.3-70b-versatile"
            )
        finally:
            service.close()

    def test_returns_string(self, service):
        result = service.generate_model_answer("What is photosynthesis?")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_calls_groq_api(self, service, mock_openai_client):
        service.generate_model_answer("What is gravity?")
        mock_openai_client.chat.completions.create.assert_called_once()

    def test_returns_empty_on_api_failure(self, service, mock_openai_client):
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
        result = service.generate_model_answer("What is gravity?")
        assert result == ""

    def test_empty_question_returns_empty(self, service):
        result = service.generate_model_answer("")
        assert result == ""

    def test_cache_hit_skips_duplicate_api_call(self, service, mock_openai_client):
        first = service.generate_model_answer("What is gravity?")
        second = service.generate_model_answer("  What is gravity?  ")

        assert first == second
        mock_openai_client.chat.completions.create.assert_called_once()

    def test_duplicate_prompt_does_not_consume_daily_quota_twice(
        self, mock_openai_client, fake_clock, tmp_path
    ):
        with patch("services.llm_service.OpenAI", return_value=mock_openai_client):
            service = LlmService(
                api_key="test-key",
                model="llama-3.3-70b-versatile",
                base_url="https://api.groq.com/openai/v1",
                daily_request_limit=1,
                cache_path=str(tmp_path / "quota-cache.json"),
                time_fn=fake_clock.time,
                monotonic_fn=fake_clock.monotonic,
                sleep_fn=fake_clock.sleep,
                jitter_fn=lambda _low, _high: 0.0,
            )

        try:
            first = service.generate_model_answer("What is DNA?")
            second = service.generate_model_answer("What is DNA?")

            assert first == second
            assert mock_openai_client.chat.completions.create.call_count == 1
        finally:
            service.close()

    def test_queues_requests_in_order(self, mock_openai_client, fake_clock, tmp_path):
        observed_questions: list[str] = []

        def create_side_effect(*, model, messages, temperature, max_tokens):
            observed_questions.append(messages[-1]["content"])
            return make_openai_response(messages[-1]["content"])

        mock_openai_client.chat.completions.create.side_effect = create_side_effect

        with patch("services.llm_service.OpenAI", return_value=mock_openai_client):
            service = LlmService(
                api_key="test-key",
                model="llama-3.3-70b-versatile",
                base_url="https://api.groq.com/openai/v1",
                cache_path=str(tmp_path / "queue-cache.json"),
                time_fn=fake_clock.time,
                monotonic_fn=fake_clock.monotonic,
                sleep_fn=fake_clock.sleep,
                jitter_fn=lambda _low, _high: 0.0,
            )

        try:
            results: list[str | None] = [None, None]

            def worker(index: int, question: str) -> None:
                results[index] = service.generate_model_answer(question)

            threads = [
                threading.Thread(target=worker, args=(0, "What is gravity?")),
                threading.Thread(target=worker, args=(1, "What is DNA?")),
            ]

            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            assert observed_questions == ["Question: What is gravity?", "Question: What is DNA?"]
            assert results == observed_questions
        finally:
            service.close()

    def test_enforces_minimum_spacing_between_outbound_requests(
        self, service, mock_openai_client, fake_clock
    ):
        service.generate_model_answer("What is photosynthesis?")
        service.generate_model_answer("What is gravity?")

        assert mock_openai_client.chat.completions.create.call_count == 2
        assert fake_clock.sleep_calls == [2]

    def test_retries_429_with_exponential_backoff(
        self, service, mock_openai_client, fake_clock
    ):
        mock_openai_client.chat.completions.create.side_effect = [
            FakeRateLimitError("rate limited"),
            make_openai_response("Recovered answer"),
        ]

        result = service.generate_model_answer("What is gravity?")

        assert result == "Recovered answer"
        assert mock_openai_client.chat.completions.create.call_count == 2
        assert fake_clock.sleep_calls == [2]

    def test_honors_retry_after_header_when_backing_off(
        self, service, mock_openai_client, fake_clock
    ):
        mock_openai_client.chat.completions.create.side_effect = [
            FakeRateLimitError("rate limited", retry_after="120"),
            make_openai_response("Recovered answer"),
        ]

        result = service.generate_model_answer("What is gravity?")

        assert result == "Recovered answer"
        assert fake_clock.sleep_calls == [120]

    def test_stops_after_max_retries_on_429(self, mock_openai_client, fake_clock, tmp_path):
        mock_openai_client.chat.completions.create.side_effect = [
            FakeRateLimitError("rate limited"),
            FakeRateLimitError("rate limited"),
            FakeRateLimitError("rate limited"),
        ]

        with patch("services.llm_service.OpenAI", return_value=mock_openai_client):
            service = LlmService(
                api_key="test-key",
                model="llama-3.3-70b-versatile",
                base_url="https://api.groq.com/openai/v1",
                max_retries=3,
                cache_path=str(tmp_path / "retry-cache.json"),
                time_fn=fake_clock.time,
                monotonic_fn=fake_clock.monotonic,
                sleep_fn=fake_clock.sleep,
                jitter_fn=lambda _low, _high: 0.0,
            )

        try:
            result = service.generate_model_answer("What is gravity?")

            assert result == ""
            assert mock_openai_client.chat.completions.create.call_count == 3
            assert fake_clock.sleep_calls == [2, 4]
        finally:
            service.close()

    def test_api_status_errors_do_not_retry(self, service, mock_openai_client):
        mock_openai_client.chat.completions.create.side_effect = FakeAPIStatusError(400, "bad request")

        result = service.generate_model_answer("What is gravity?")

        assert result == ""
        mock_openai_client.chat.completions.create.assert_called_once()

    def test_blocks_uncached_requests_after_daily_limit(
        self, mock_openai_client, fake_clock, tmp_path
    ):
        with patch("services.llm_service.OpenAI", return_value=mock_openai_client):
            service = LlmService(
                api_key="test-key",
                model="llama-3.3-70b-versatile",
                base_url="https://api.groq.com/openai/v1",
                daily_request_limit=1,
                cache_path=str(tmp_path / "daily-limit-cache.json"),
                time_fn=fake_clock.time,
                monotonic_fn=fake_clock.monotonic,
                sleep_fn=fake_clock.sleep,
                jitter_fn=lambda _low, _high: 0.0,
            )

        try:
            first = service.generate_model_answer("What is gravity?")
            second = service.generate_model_answer("What is DNA?")

            assert first != ""
            assert second == ""
            assert mock_openai_client.chat.completions.create.call_count == 1
        finally:
            service.close()

    def test_cache_persists_across_service_restarts(self, mock_openai_client, fake_clock, tmp_path):
        cache_path = tmp_path / "persistent-cache.json"

        with patch("services.llm_service.OpenAI", return_value=mock_openai_client):
            first = LlmService(
                api_key="test-key",
                model="llama-3.3-70b-versatile",
                base_url="https://api.groq.com/openai/v1",
                cache_path=str(cache_path),
                time_fn=fake_clock.time,
                monotonic_fn=fake_clock.monotonic,
                sleep_fn=fake_clock.sleep,
                jitter_fn=lambda _low, _high: 0.0,
            )

        try:
            cached = first.generate_model_answer("What is photosynthesis?")
        finally:
            first.close()

        second_client = MagicMock()
        second_client.chat.completions.create.return_value = make_openai_response("unused")
        with patch("services.llm_service.OpenAI", return_value=second_client):
            second = LlmService(
                api_key="test-key",
                model="llama-3.3-70b-versatile",
                base_url="https://api.groq.com/openai/v1",
                cache_path=str(cache_path),
                time_fn=fake_clock.time,
                monotonic_fn=fake_clock.monotonic,
                sleep_fn=fake_clock.sleep,
                jitter_fn=lambda _low, _high: 0.0,
            )

        try:
            restored = second.generate_model_answer("What is photosynthesis?")

            assert restored == cached
            second_client.chat.completions.create.assert_not_called()
        finally:
            second.close()


class TestGenerateBatchAnswers:
    def test_returns_list(self, service):
        questions = ["What is DNA?", "What is RNA?"]
        results = service.generate_batch_answers(questions)
        assert isinstance(results, list)
        assert len(results) == 2

    def test_empty_list_returns_empty(self, service):
        result = service.generate_batch_answers([])
        assert result == []

    def test_processes_batch_sequentially(self, service, mock_openai_client, fake_clock):
        questions = ["What is DNA?", "What is RNA?"]

        results = service.generate_batch_answers(questions)

        assert len(results) == 2
        assert mock_openai_client.chat.completions.create.call_count == 2
        assert fake_clock.sleep_calls == [2]


class TestIsConfigured:
    def test_configured_with_key(self, service):
        assert service.is_configured is True

    def test_not_configured_without_key(self):
        svc = LlmService(api_key="", model="test")
        try:
            assert svc.is_configured is False
        finally:
            svc.close()
