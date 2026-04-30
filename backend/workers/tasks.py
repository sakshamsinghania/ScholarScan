"""Celery tasks for ScholarScan.

evaluate_assessment is the durable replacement for the threading.Thread
path in routes/assess.py. Activated when USE_CELERY=true.
"""

from __future__ import annotations

import json
import logging

from flask import current_app

from models.assessment import MultiAssessmentResponse
from workers.celery_app import celery

logger = logging.getLogger(__name__)


class _TransientError(Exception):
    """Marker for errors that warrant a Celery retry."""


def _publish_progress(redis_client, task_id: str, event: dict) -> None:
    """Publish a progress event to Redis pub/sub channel."""
    try:
        redis_client.publish(f"progress:{task_id}", json.dumps(event))
    except Exception as exc:
        logger.warning("Redis publish failed for task %s: %s", task_id, exc)


def _persist_event(progress_service, task_id: str, stage: str, status: str, message: str = "") -> None:
    """Update in-memory progress state + publish to Redis."""
    progress_service.update(task_id, stage, status, message)


@celery.task(
    bind=True,
    name="workers.tasks.evaluate_assessment",
    max_retries=3,
    autoretry_for=(_TransientError,),
    default_retry_delay=10,
)
def evaluate_assessment(
    self,
    task_id: str,
    answer_file_path: str,
    file_type: str,
    student_id: str,
    max_marks_per_question: int,
    question_file_path: str | None = None,
    question_file_type: str | None = None,
    owner_id: str | None = None,
) -> dict:
    """
    Durable evaluation pipeline — runs inside a Celery worker with Flask app context.

    Publishes progress events to Redis pub/sub so the SSE endpoint can stream
    them to the client. Also stores the final result via ProgressService so
    GET /api/task/<task_id>/result returns the aggregated JSON.
    """
    progress_service = current_app.config["PROGRESS_SERVICE"]
    eval_service = current_app.config["EVALUATION_SERVICE"]
    file_handler = current_app.config["FILE_HANDLER"]

    # Re-register task in progress service in case the worker restarted
    if progress_service.get_current(task_id) is None:
        progress_service.create_task(task_id, owner_id=owner_id)

    redis_client = _get_redis_client()

    def on_progress(stage: str, message: str = "") -> None:
        logger.info("Task %s stage=%s message=%s", task_id, stage, message)
        progress_service.update(task_id, stage, "running", message)
        if redis_client:
            current_state = progress_service.get_current(task_id)
            if current_state:
                _publish_progress(redis_client, task_id, current_state)
        # Persist to DB for replay on reconnect
        _persist_progress_event(task_id, stage, owner_id, progress_service.get_current(task_id))

    try:
        result = eval_service.evaluate(
            on_progress=on_progress,
            answer_file_path=answer_file_path,
            file_type=file_type,
            question_file_path=question_file_path,
            question_file_type=question_file_type,
            student_id=student_id,
            max_marks_per_question=max_marks_per_question,
        )
        validated = MultiAssessmentResponse.model_validate(result).model_dump(mode="json")

        progress_service.store_result(task_id, validated)
        progress_service.update(task_id, "completed", "completed", "Assessment complete!")

        if redis_client:
            final_state = progress_service.get_current(task_id)
            if final_state:
                _publish_progress(redis_client, task_id, final_state)
            # Publish sentinel so SSE subscriber can stop listening
            _publish_progress(redis_client, task_id, {"task_id": task_id, "stage": "completed", "status": "completed", "__done": True})

        logger.info("Celery task %s completed", task_id)
        return validated

    except ValueError as exc:
        logger.warning("Celery task %s validation failed: %s", task_id, exc)
        _fail_task(task_id, str(exc), progress_service, redis_client)
        return {}
    except Exception as exc:
        logger.exception("Celery task %s failed", task_id)
        _fail_task(
            task_id,
            "Assessment could not be completed. Please try again or contact support.",
            progress_service,
            redis_client,
        )
        # Store failed status in DB assessments row
        _mark_assessment_failed(task_id, str(exc), owner_id)
        return {}
    finally:
        file_handler.cleanup(answer_file_path)
        if question_file_path:
            file_handler.cleanup(question_file_path)


def _fail_task(task_id: str, message: str, progress_service, redis_client) -> None:
    progress_service.update(task_id, "error", "error", message)
    if redis_client:
        state = progress_service.get_current(task_id) or {}
        state["__done"] = True
        _publish_progress(redis_client, task_id, state)


def _get_redis_client():
    """Return a Redis client using REDIS_URL, or None if Redis is unavailable."""
    try:
        import redis as redis_lib
        import os
        r = redis_lib.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        r.ping()
        return r
    except Exception:
        return None


def _persist_progress_event(task_id: str, stage: str, owner_id: str | None, payload: dict | None) -> None:
    """Write a progress_events document to DB for SSE replay. No-op if DB unavailable."""
    try:
        from datetime import datetime, timezone
        from db.session import get_session, is_db_available
        if not is_db_available():
            return
        with get_session() as db:
            if db is None:
                return
            db["progress_events"].insert_one({
                "task_id": task_id,
                "owner_id": owner_id,
                "stage": stage,
                "payload": payload,
                "created_at": datetime.now(timezone.utc),
            })
    except Exception as exc:
        logger.debug("Failed to persist progress event: %s", exc)


def _mark_assessment_failed(task_id: str, error_message: str, owner_id: str | None) -> None:
    """Upsert an assessments document with status=failed. No-op if DB unavailable."""
    try:
        from datetime import datetime, timezone
        from db.session import get_session, is_db_available
        if not is_db_available():
            return
        with get_session() as db:
            if db is None:
                return
            now = datetime.now(timezone.utc)
            db["assessments"].update_one(
                {"_id": task_id},
                {"$set": {
                    "status": "failed",
                    "error_message": error_message,
                    "completed_at": now,
                    "owner_id": owner_id,
                }, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
    except Exception as exc:
        logger.debug("Failed to mark assessment failed in DB: %s", exc)
