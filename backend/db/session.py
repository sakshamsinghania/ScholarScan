"""MongoDB client + database accessor.

Activated when MONGODB_URI is set. When unset, get_session() yields None
and callers fall back to in-memory storage.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database

logger = logging.getLogger(__name__)

_client: MongoClient | None = None
_database: Database | None = None


def init_db(uri: str, db_name: str) -> bool:
    """Connect to MongoDB. Returns True on success."""
    global _client, _database
    if not uri:
        return False
    try:
        _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        _database = _client[db_name]
        _client.admin.command("ping")
        logger.info("MongoDB connected: %s / %s", uri.split("@")[-1], db_name)
        return True
    except Exception as exc:
        logger.warning("MongoDB unavailable (%s) — falling back to in-memory storage", exc)
        _client = None
        _database = None
        return False


def reset_db() -> None:
    """Close the active client."""
    global _client, _database
    if _client is not None:
        _client.close()
    _client = None
    _database = None


def is_db_available() -> bool:
    return _database is not None


@contextmanager
def get_session() -> Generator[Database | None, None, None]:
    """Context manager that yields the MongoDB database or None (RAM fallback)."""
    yield _database


def create_all_tables() -> None:
    """Create MongoDB indexes (idempotent)."""
    if _database is None:
        return
    _database["assessments"].create_index("owner_id")
    _database["assessments"].create_index("student_id")
    _database["assessments"].create_index([("created_at", DESCENDING)])
    _database["users"].create_index("email", unique=True)
    _database["llm_cache"].create_index([("last_hit_at", ASCENDING)])
    _database["progress_events"].create_index("task_id")
    logger.info("MongoDB indexes created")
