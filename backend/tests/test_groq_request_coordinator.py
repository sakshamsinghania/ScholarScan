"""Tests for GroqRequestCoordinator retry, quota, and throttle behavior."""

import os
import sys
import threading
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.groq_request_coordinator as groq_request_coordinator_module
from services.groq_request_coordinator import GroqRequestCoordinator


class FakeClock:
    """Deterministic time source for retry and quota tests."""

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


@pytest.fixture(autouse=True)
def patch_openai_exceptions(monkeypatch):
    monkeypatch.setattr(groq_request_coordinator_module, "RateLimitError", FakeRateLimitError)
    monkeypatch.setattr(groq_request_coordinator_module, "APIStatusError", FakeAPIStatusError)


@pytest.fixture
def fake_clock():
    return FakeClock()


def test_retrying_after_429_does_not_consume_an_extra_daily_slot(fake_clock, tmp_path):
    coordinator = GroqRequestCoordinator(
        cache_path=str(tmp_path / "coordinator-cache.json"),
        daily_request_limit=1,
        max_retries=2,
        time_fn=fake_clock.time,
        monotonic_fn=fake_clock.monotonic,
        sleep_fn=fake_clock.sleep,
        jitter_fn=lambda _low, _high: 0.0,
    )

    attempts = iter([FakeRateLimitError("rate limited"), "Recovered answer"])

    def request_fn():
        value = next(attempts)
        if isinstance(value, Exception):
            raise value
        return value

    try:
        result = coordinator.submit("quota-key", request_fn)
    finally:
        coordinator.close()

    assert result == "Recovered answer"
    assert len(coordinator._state["request_timestamps"]) == 1
    assert fake_clock.sleep_calls == [2]


def test_retry_after_http_date_is_honored(fake_clock, tmp_path):
    coordinator = GroqRequestCoordinator(
        cache_path=str(tmp_path / "retry-after-cache.json"),
        max_retries=2,
        time_fn=fake_clock.time,
        monotonic_fn=fake_clock.monotonic,
        sleep_fn=fake_clock.sleep,
        jitter_fn=lambda _low, _high: 0.0,
    )

    attempts = iter([
        FakeRateLimitError("rate limited", retry_after="Thu, 01 Jan 1970 00:02:00 GMT"),
        "Recovered answer",
    ])

    def request_fn():
        value = next(attempts)
        if isinstance(value, Exception):
            raise value
        return value

    try:
        result = coordinator.submit("http-date-key", request_fn)
    finally:
        coordinator.close()

    assert result == "Recovered answer"
    assert fake_clock.sleep_calls == [120]


def test_backoff_includes_jitter(fake_clock, tmp_path):
    coordinator = GroqRequestCoordinator(
        cache_path=str(tmp_path / "jitter-cache.json"),
        time_fn=fake_clock.time,
        monotonic_fn=fake_clock.monotonic,
        sleep_fn=fake_clock.sleep,
        backoff_base_seconds=10,
        jitter_fn=lambda _low, _high: 2.0,
    )

    try:
        delay = coordinator._compute_retry_delay(FakeRateLimitError("rate limited"), attempt=0)
    finally:
        coordinator.close()

    assert delay == 12.0


def test_cached_reads_are_not_blocked_while_throttle_waits(tmp_path):
    sleep_started = threading.Event()
    release_sleep = threading.Event()

    class BlockingClock:
        def __init__(self):
            self.current = 0.0

        def time(self) -> float:
            return self.current

        def monotonic(self) -> float:
            return self.current

        def sleep(self, seconds: float) -> None:
            sleep_started.set()
            release_sleep.wait(timeout=2)
            self.current += seconds

    clock = BlockingClock()
    coordinator = GroqRequestCoordinator(
        cache_path=str(tmp_path / "lock-cache.json"),
        min_interval_seconds=15,
        time_fn=clock.time,
        monotonic_fn=clock.monotonic,
        sleep_fn=clock.sleep,
        jitter_fn=lambda _low, _high: 0.0,
    )

    with coordinator._lock:
        coordinator._state["cache"]["cached-key"] = {
            "response": "cached-value",
            "created_at": 0,
            "last_hit_at": 0,
        }
        coordinator._last_request_started_at = 0.0

    worker = threading.Thread(target=coordinator._reserve_request_slot)
    worker.start()
    assert sleep_started.wait(timeout=1), "expected throttle sleep to begin"

    cached_response: list[str | None] = []

    def reader():
        cached_response.append(coordinator.get_cached_response("cached-key"))

    reader_thread = threading.Thread(target=reader)
    reader_thread.start()
    reader_thread.join(timeout=0.2)

    release_sleep.set()
    worker.join(timeout=1)
    reader_thread.join(timeout=1)
    coordinator.close()

    assert not reader_thread.is_alive()
    assert cached_response == ["cached-value"]
