"""Celery application instance for ScholarScan.

Initialised bare here. Call init_celery(flask_app) in the Flask factory
so tasks inherit Flask's app context automatically.
"""

from __future__ import annotations

import os

from celery import Celery

celery = Celery(
    "scholarscan",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("DATABASE_URL") or os.getenv("REDIS_URL", "redis://localhost:6379/1"),
    include=["workers.tasks"],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Retry transient errors automatically (up to 3 times)
    task_max_retries=3,
    task_default_retry_delay=10,
)


def init_celery(app) -> None:
    """Bind Celery to a Flask app so every task runs inside an app context."""

    class _ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = _ContextTask
    celery.conf.update(
        broker_url=app.config.get("REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0")),
    )
