"""Assessment result storage.

DB-backed when DATABASE_URL is set (Phase 2). Falls back to thread-safe
in-memory FIFO when no DB is configured (local dev, tests).
"""

import threading
import uuid
from copy import deepcopy

from db.session import get_session, is_db_available


class ResultStorageService:
    """Store and query assessment results. Swaps DB/RAM internals transparently."""

    def __init__(self, max_entries: int = 500):
        # RAM fallback state
        self._results: list[dict] = []
        self._lock = threading.Lock()
        self._max_entries = max_entries

    # ------------------------------------------------------------------
    # Public API (unchanged from Phase 1)
    # ------------------------------------------------------------------

    def store(self, result: dict, owner_id: str | None = None) -> str:
        """Persist result. Returns generated id."""
        if is_db_available():
            return self._store_db(result, owner_id)
        return self._store_ram(result, owner_id)

    def get_all(self, owner_id: str | None = None) -> list[dict]:
        if is_db_available():
            return self._get_all_db(owner_id)
        return self._get_all_ram(owner_id)

    def get_filtered(
        self,
        student_id: str | None = None,
        question_id: str | None = None,
        owner_id: str | None = None,
    ) -> list[dict]:
        if is_db_available():
            return self._get_filtered_db(student_id, question_id, owner_id)
        return self._get_filtered_ram(student_id, question_id, owner_id)

    # ------------------------------------------------------------------
    # DB-backed path
    # ------------------------------------------------------------------

    def _store_db(self, result: dict, owner_id: str | None) -> str:
        from repositories import assessment_repository
        with get_session() as session:
            return assessment_repository.store(session, result, owner_id)

    def _get_all_db(self, owner_id: str | None) -> list[dict]:
        from repositories import assessment_repository
        with get_session() as session:
            return assessment_repository.get_all(session, owner_id)

    def _get_filtered_db(
        self,
        student_id: str | None,
        question_id: str | None,
        owner_id: str | None,
    ) -> list[dict]:
        from repositories import assessment_repository
        with get_session() as session:
            return assessment_repository.get_filtered(session, student_id, question_id, owner_id)

    # ------------------------------------------------------------------
    # In-memory fallback (original Phase 0/1 behaviour)
    # ------------------------------------------------------------------

    def _store_ram(self, result: dict, owner_id: str | None) -> str:
        entry = deepcopy(result)
        entry["id"] = str(uuid.uuid4())
        if owner_id is not None:
            entry["owner_id"] = owner_id
        with self._lock:
            if self._max_entries > 0:
                overflow = len(self._results) - self._max_entries + 1
                if overflow > 0:
                    del self._results[:overflow]
            self._results.append(entry)
        return entry["id"]

    def _get_all_ram(self, owner_id: str | None) -> list[dict]:
        with self._lock:
            results = list(self._results)
        if owner_id is not None:
            results = [r for r in results if r.get("owner_id") == owner_id]
        return deepcopy(results)

    def _get_filtered_ram(
        self,
        student_id: str | None,
        question_id: str | None,
        owner_id: str | None,
    ) -> list[dict]:
        with self._lock:
            results = list(self._results)
        if owner_id is not None:
            results = [r for r in results if r.get("owner_id") == owner_id]
        if student_id is not None:
            results = [r for r in results if r.get("student_id") == student_id]
        if question_id is not None:
            results = [r for r in results if r.get("question_id") == question_id]
        return deepcopy(results)
