"""SQLAlchemy engine + session factory.

Activated when DATABASE_URL is set. When unset, get_session() returns None
and callers fall back to in-memory storage.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)

_engine = None
_SessionFactory: sessionmaker | None = None


class Base(DeclarativeBase):
    pass


def init_db(database_url: str) -> bool:
    """Initialise engine + session factory. Returns True on success."""
    global _engine, _SessionFactory
    if not database_url:
        return False
    try:
        _engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)
        # Smoke-test the connection
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connected: %s", database_url.split("@")[-1])
        return True
    except Exception as exc:
        logger.warning("Database unavailable (%s) — falling back to in-memory storage", exc)
        _engine = None
        _SessionFactory = None
        return False


def reset_db() -> None:
    """Dispose the active engine/session factory."""
    global _engine, _SessionFactory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionFactory = None


def is_db_available() -> bool:
    return _SessionFactory is not None


@contextmanager
def get_session() -> Generator[Session | None, None, None]:
    """Context manager that yields a DB session or None (RAM fallback)."""
    if _SessionFactory is None:
        yield None
        return

    session: Session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_all_tables() -> None:
    """Create all ORM-mapped tables (idempotent — use alembic for prod migrations)."""
    if _engine is None:
        return
    from db.models import Base as ModelBase  # noqa: F401 — registers models
    ModelBase.metadata.create_all(_engine)
