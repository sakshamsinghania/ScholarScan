"""CRUD for LlmCache rows with TTL eviction."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from db.models import LlmCache

logger = logging.getLogger(__name__)

_DEFAULT_TTL_DAYS = 30
_MAX_ROWS = 50_000


def get(session: Session, cache_key: str) -> str | None:
    """Return cached response and bump hit_count + last_hit_at. None on miss."""
    row = session.get(LlmCache, cache_key)
    if row is None:
        return None
    row.hit_count += 1
    row.last_hit_at = datetime.now(timezone.utc)
    return row.response


def put(session: Session, cache_key: str, response: str, model: str | None = None, prompt_hash: str | None = None) -> None:
    """Upsert a cache entry."""
    row = session.get(LlmCache, cache_key)
    if row is None:
        row = LlmCache(
            cache_key=cache_key,
            model=model,
            prompt_hash=prompt_hash,
            response=response,
        )
        session.add(row)
    else:
        row.response = response
        row.last_hit_at = datetime.now(timezone.utc)
        row.hit_count += 1


def evict_expired(session: Session, ttl_days: int = _DEFAULT_TTL_DAYS) -> int:
    """Delete entries not hit within ttl_days. Returns deleted count."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)
    deleted = (
        session.query(LlmCache)
        .filter(LlmCache.last_hit_at < cutoff)
        .delete(synchronize_session=False)
    )
    logger.info("LLM cache eviction: removed %d expired entries", deleted)
    return deleted
