"""In-memory storage for assessment results. Swappable to a database later."""

import threading
import uuid
from copy import deepcopy


class ResultStorageService:
    """Thread-safe in-memory storage for assessment results."""

    def __init__(self, max_entries: int = 500):
        self._results: list[dict] = []
        self._lock = threading.Lock()
        self._max_entries = max_entries

    def store(self, result: dict) -> str:
        """Store a result dict, adding a unique ID. Returns the generated ID."""
        entry = deepcopy(result)
        entry["id"] = str(uuid.uuid4())
        with self._lock:
            if self._max_entries > 0:
                overflow = len(self._results) - self._max_entries + 1
                if overflow > 0:
                    del self._results[:overflow]
            self._results.append(entry)
        return entry["id"]

    def get_all(self) -> list[dict]:
        """Return a copy of all stored results."""
        with self._lock:
            return deepcopy(self._results)

    def get_filtered(
        self,
        student_id: str | None = None,
        question_id: str | None = None,
    ) -> list[dict]:
        """Return results matching the given filters."""
        with self._lock:
            results = list(self._results)

        if student_id is not None:
            results = [r for r in results if r.get("student_id") == student_id]

        if question_id is not None:
            results = [r for r in results if r.get("question_id") == question_id]

        return deepcopy(results)
