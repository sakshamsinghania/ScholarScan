"""Queue, throttle, retry, and cache Groq API requests."""

from __future__ import annotations

import json
import logging
import os
import queue
import random
import tempfile
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Callable

from openai import APIStatusError, RateLimitError

logger = logging.getLogger(__name__)

_SECONDS_PER_DAY = 24 * 60 * 60


@dataclass(slots=True)
class _QueuedRequest:
    """Internal representation of one queued Groq request."""

    cache_key: str
    request_fn: Callable[[], str]
    future: Future


class GroqRequestCoordinator:
    """Serialize Groq requests with disk-backed cache and quota tracking."""

    def __init__(
        self,
        cache_path: str,
        min_interval_seconds: float = 2,
        daily_request_limit: int = 14000,
        max_retries: int = 5,
        backoff_base_seconds: float = 2,
        backoff_max_seconds: float = 60,
        time_fn: Callable[[], float] | None = None,
        monotonic_fn: Callable[[], float] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
        jitter_fn: Callable[[float, float], float] | None = None,
    ) -> None:
        self._cache_path = Path(cache_path)
        self._min_interval_seconds = min_interval_seconds
        self._daily_request_limit = daily_request_limit
        self._max_retries = max_retries
        self._backoff_base_seconds = backoff_base_seconds
        self._backoff_max_seconds = backoff_max_seconds
        self._time_fn = time_fn or time.time
        self._monotonic_fn = monotonic_fn or time.monotonic
        self._sleep_fn = sleep_fn or time.sleep
        self._jitter_fn = jitter_fn or random.uniform

        self._lock = threading.Lock()
        self._queue: queue.Queue[_QueuedRequest | None] = queue.Queue()
        self._stop_event = threading.Event()
        self._inflight: dict[str, Future] = {}
        self._last_request_started_at: float | None = None
        self._state = {
            "cache": {},
            "request_timestamps": [],
        }

        self._load_state()

        self._worker = threading.Thread(
            target=self._run_worker,
            name="groq-request-coordinator",
            daemon=True,
        )
        self._worker.start()

    def get_cached_response(self, cache_key: str) -> str | None:
        """Return a cached response immediately, if available."""
        with self._lock:
            return self._get_cached_response_locked(cache_key, touch=True)

    def submit(self, cache_key: str, request_fn: Callable[[], str]) -> str:
        """Queue a Groq request or join an identical in-flight request."""
        cached = self.get_cached_response(cache_key)
        if cached is not None:
            return cached

        with self._lock:
            future = self._inflight.get(cache_key)
            if future is None:
                future = Future()
                self._inflight[cache_key] = future
                self._queue.put(_QueuedRequest(cache_key=cache_key, request_fn=request_fn, future=future))

        return future.result()

    def close(self) -> None:
        """Stop the worker thread."""
        self._stop_event.set()
        self._queue.put(None)
        if self._worker.is_alive():
            self._worker.join(timeout=1)

    def _run_worker(self) -> None:
        while not self._stop_event.is_set():
            item = self._queue.get()
            if item is None:
                self._queue.task_done()
                return

            try:
                result = self._process_request(item)
                item.future.set_result(result)
            except Exception:
                logger.exception("Groq request coordinator failed unexpectedly")
                item.future.set_result("")
            finally:
                with self._lock:
                    self._inflight.pop(item.cache_key, None)
                self._queue.task_done()

    def _process_request(self, item: _QueuedRequest) -> str:
        with self._lock:
            cached = self._get_cached_response_locked(item.cache_key, touch=True)
        if cached is not None:
            return cached

        if not self._reserve_request_slot():
            return ""

        for attempt in range(self._max_retries):
            try:
                response_text = item.request_fn() or ""
            except RateLimitError as exc:
                if attempt >= self._max_retries - 1:
                    logger.error("Groq request exhausted retries after repeated 429 responses")
                    return ""

                delay = self._compute_retry_delay(exc, attempt)
                logger.warning(
                    "Groq rate limited; retrying in %.2f seconds (attempt %d/%d)",
                    delay,
                    attempt + 1,
                    self._max_retries,
                )
                self._sleep_fn(delay)
                continue
            except APIStatusError as exc:
                logger.error("Groq API error %s: %s", exc.status_code, exc)
                return ""
            except Exception as exc:
                logger.error("Groq request failed: %s", exc)
                return ""

            if response_text:
                with self._lock:
                    self._state["cache"][item.cache_key] = {
                        "response": response_text,
                        "created_at": self._time_fn(),
                        "last_hit_at": self._time_fn(),
                    }
                    self._persist_state_locked()

            return response_text

        return ""

    def _reserve_request_slot(self) -> bool:
        while True:
            sleep_for = 0.0

            with self._lock:
                self._prune_request_timestamps_locked()
                if len(self._state["request_timestamps"]) >= self._daily_request_limit:
                    logger.warning("Groq daily request limit reached; rejecting uncached request")
                    return False

                now = self._monotonic_fn()
                if self._last_request_started_at is not None:
                    elapsed = now - self._last_request_started_at
                    if elapsed < self._min_interval_seconds:
                        sleep_for = self._min_interval_seconds - elapsed
                    else:
                        self._last_request_started_at = now
                        self._state["request_timestamps"].append(self._time_fn())
                        self._persist_state_locked()
                        return True
                else:
                    self._last_request_started_at = now
                    self._state["request_timestamps"].append(self._time_fn())
                    self._persist_state_locked()
                    return True

            self._sleep_fn(sleep_for)

    def _compute_retry_delay(self, exc: RateLimitError, attempt: int) -> float:
        retry_after = self._parse_retry_after(exc)
        backoff = min(
            self._backoff_base_seconds * (2**attempt),
            self._backoff_max_seconds,
        )
        jitter = self._jitter_fn(0.0, backoff * 0.2) if backoff > 0 else 0.0
        backoff_with_jitter = min(backoff + jitter, self._backoff_max_seconds)
        if retry_after is None:
            return backoff_with_jitter
        return max(retry_after, backoff_with_jitter)

    def _parse_retry_after(self, exc: RateLimitError) -> float | None:
        response = getattr(exc, "response", None)
        headers = getattr(response, "headers", None)
        if not headers:
            return None

        value = headers.get("Retry-After")
        if value in (None, ""):
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            try:
                parsed = parsedate_to_datetime(value)
            except (TypeError, ValueError, IndexError, OverflowError):
                return None

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)

            remaining = parsed.timestamp() - self._time_fn()
            return max(0.0, remaining)

    def _get_cached_response_locked(self, cache_key: str, touch: bool) -> str | None:
        entry = self._state["cache"].get(cache_key)
        if not entry:
            return None

        if touch:
            entry["last_hit_at"] = self._time_fn()
            self._persist_state_locked()

        response = entry.get("response")
        return response if isinstance(response, str) else None

    def _prune_request_timestamps_locked(self) -> None:
        cutoff = self._time_fn() - _SECONDS_PER_DAY
        self._state["request_timestamps"] = [
            ts for ts in self._state["request_timestamps"] if ts >= cutoff
        ]

    def _load_state(self) -> None:
        if not self._cache_path.exists():
            return

        try:
            payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load Groq cache state from %s: %s", self._cache_path, exc)
            return

        cache = payload.get("cache", {})
        request_timestamps = payload.get("request_timestamps", [])
        if isinstance(cache, dict):
            self._state["cache"] = cache
        if isinstance(request_timestamps, list):
            self._state["request_timestamps"] = [ts for ts in request_timestamps if isinstance(ts, (int, float))]

    def _persist_state_locked(self) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._state, indent=2, sort_keys=True)

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self._cache_path.parent,
            delete=False,
        ) as handle:
            handle.write(payload)
            temp_path = handle.name

        os.replace(temp_path, self._cache_path)
