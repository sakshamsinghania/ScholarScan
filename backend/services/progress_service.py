"""Thread-safe pipeline progress tracking for real-time SSE updates."""

import queue
import threading
import time
from typing import Generator

# Ordered pipeline stages: (key, display_label)
PIPELINE_STAGES = [
    ("upload_received", "Upload received"),
    ("file_type_detection", "Detecting file type"),
    ("text_extraction", "Extracting text from document"),
    ("nlp_preprocessing", "Preprocessing text with NLP"),
    ("question_detection", "Detecting questions"),
    ("llm_generation", "Generating model answers with AI"),
    ("answer_mapping", "Mapping answers to questions"),
    ("similarity", "Computing semantic similarity"),
    ("scoring", "Calculating scores & feedback"),
    ("completed", "Assessment complete"),
]

_STAGE_INDEX = {key: i for i, (key, _) in enumerate(PIPELINE_STAGES)}
_TERMINAL_STAGE = "completed"
_ERROR_STATUS = "error"


class _TaskState:
    """Internal mutable state for a single task."""

    __slots__ = (
        "task_id",
        "owner_id",
        "stage",
        "status",
        "message",
        "completed_stages",
        "update_queue",
        "result",
        "updated_at",
    )

    def __init__(self, task_id: str, owner_id: str | None = None):
        self.task_id = task_id
        self.owner_id = owner_id
        self.stage: str | None = None
        self.status: str = "pending"
        self.message: str = ""
        self.completed_stages: list[str] = []
        self.update_queue: queue.Queue[dict] = queue.Queue()
        self.result: dict | None = None
        self.updated_at = time.monotonic()


class ProgressService:
    """
    Track per-task pipeline progress with thread-safe access.

    Uses a Queue per task so SSE consumers never miss events,
    even under high-frequency updates from producer threads.
    """

    def __init__(self, task_ttl_seconds: float = 60 * 60):
        self._tasks: dict[str, _TaskState] = {}
        self._lock = threading.Lock()
        self._task_ttl_seconds = task_ttl_seconds

    def create_task(self, task_id: str, owner_id: str | None = None) -> None:
        """Register a new task for progress tracking."""
        with self._lock:
            self._evict_expired_locked()
            self._tasks[task_id] = _TaskState(task_id, owner_id=owner_id)

    def update(self, task_id: str, stage: str, status: str, message: str = "") -> None:
        """
        Record a stage transition. Pushes event to the queue
        so any SSE stream consumer receives it.
        """
        with self._lock:
            self._evict_expired_locked()
            state = self._tasks.get(task_id)
            if not state:
                return

            # Mark previous stage as completed if transitioning
            if state.stage and state.stage != stage and state.status != "error":
                if state.stage not in state.completed_stages:
                    state.completed_stages.append(state.stage)

            state.stage = stage
            state.status = status
            state.message = message or self._default_message(stage)
            state.updated_at = time.monotonic()

            # If this stage itself is completed, add to completed list
            if status == "completed" and stage not in state.completed_stages:
                state.completed_stages.append(stage)

            step = _STAGE_INDEX.get(stage, 0) + 1

            # Push snapshot to queue for SSE consumers
            event = {
                "task_id": state.task_id,
                "stage": stage,
                "status": status,
                "message": state.message,
                "step": step,
                "total_steps": len(PIPELINE_STAGES),
                "completed_stages": list(state.completed_stages),
            }
            state.update_queue.put(event)

    def get_current(self, task_id: str) -> dict | None:
        """Snapshot of current progress for a task."""
        with self._lock:
            self._evict_expired_locked()
            state = self._tasks.get(task_id)
            if not state:
                return None

            step = _STAGE_INDEX.get(state.stage, 0) + 1 if state.stage else 0

            return {
                "task_id": state.task_id,
                "stage": state.stage,
                "status": state.status,
                "message": state.message,
                "step": step,
                "total_steps": len(PIPELINE_STAGES),
                "completed_stages": list(state.completed_stages),
            }

    def stream(self, task_id: str, timeout: float = 30) -> Generator[dict, None, None]:
        """
        Generator that yields progress events until terminal stage.

        Reads from the task's Queue so no events are lost.
        """
        with self._lock:
            self._evict_expired_locked()
            state = self._tasks.get(task_id)
            if not state:
                return
            q = state.update_queue

        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                event = q.get(timeout=min(remaining, 1.0))
                yield event
                if event.get("stage") == _TERMINAL_STAGE or event.get("status") == _ERROR_STATUS:
                    return
            except queue.Empty:
                continue

    def store_result(self, task_id: str, result: dict) -> None:
        """Store the final assessment result for a completed task."""
        with self._lock:
            self._evict_expired_locked()
            state = self._tasks.get(task_id)
            if state:
                state.result = result
                state.updated_at = time.monotonic()

    def get_result(self, task_id: str) -> dict | None:
        """Retrieve the final result for a task."""
        with self._lock:
            self._evict_expired_locked()
            state = self._tasks.get(task_id)
            if state and state.result is not None:
                return state.result
            return None

    def cleanup(self, task_id: str) -> None:
        """Remove a task from tracking. Silently ignores missing tasks."""
        with self._lock:
            self._tasks.pop(task_id, None)

    def is_owner(self, task_id: str, owner_id: str | None) -> bool:
        """Check if owner_id matches the task owner. None owner = no check."""
        if owner_id is None:
            return True
        with self._lock:
            state = self._tasks.get(task_id)
            if not state:
                return False
            if state.owner_id is None:
                return True
            return state.owner_id == owner_id

    def _evict_expired_locked(self) -> None:
        """Remove expired task state while holding the service lock."""
        if self._task_ttl_seconds <= 0:
            return

        now = time.monotonic()
        expired = [
            task_id
            for task_id, state in self._tasks.items()
            if now - state.updated_at > self._task_ttl_seconds
        ]
        for task_id in expired:
            self._tasks.pop(task_id, None)

    @staticmethod
    def _default_message(stage: str) -> str:
        """Look up default display message for a stage."""
        for key, label in PIPELINE_STAGES:
            if key == stage:
                return label
        return stage
