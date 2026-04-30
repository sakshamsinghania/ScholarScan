"""CRUD for llm_cache collection with TTL eviction."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from pymongo.database import Database

logger = logging.getLogger(__name__)

_DEFAULT_TTL_DAYS = 30


def get(db: Database, cache_key: str) -> str | None:
    """Return cached response and bump hit_count + last_hit_at. None on miss."""
    row = db["llm_cache"].find_one_and_update(
        {"_id": cache_key},
        {
            "$inc": {"hit_count": 1},
            "$set": {"last_hit_at": datetime.now(timezone.utc)},
        },
    )
    return row["response"] if row else None


def put(
    db: Database,
    cache_key: str,
    response: str,
    model: str | None = None,
    prompt_hash: str | None = None,
) -> None:
    """Upsert a cache entry."""
    now = datetime.now(timezone.utc)
    db["llm_cache"].update_one(
        {"_id": cache_key},
        {
            "$set": {
                "response": response,
                "model": model,
                "prompt_hash": prompt_hash,
                "last_hit_at": now,
            },
            "$setOnInsert": {"created_at": now, "hit_count": 0},
        },
        upsert=True,
    )


def evict_expired(db: Database, ttl_days: int = _DEFAULT_TTL_DAYS) -> int:
    """Delete entries not hit within ttl_days. Returns deleted count."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)
    result = db["llm_cache"].delete_many({"last_hit_at": {"$lt": cutoff}})
    logger.info("LLM cache eviction: removed %d expired entries", result.deleted_count)
    return result.deleted_count
