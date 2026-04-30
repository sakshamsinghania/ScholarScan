"""SQLAlchemy ORM models for ScholarScan."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, TypeDecorator

from db.session import Base


# ---------------------------------------------------------------------------
# Portable UUID + JSON types (work with both Postgres and SQLite for tests)
# ---------------------------------------------------------------------------

class PortableUUID(TypeDecorator):
    """Store UUIDs as TEXT on SQLite, native UUID on Postgres."""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        return value


class PortableJSON(TypeDecorator):
    """Use JSONB on Postgres, plain JSON elsewhere."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if dialect.name == "postgresql":
            return value
        import json
        return json.dumps(value) if value is not None else None

    def process_result_value(self, value, dialect):
        if dialect.name == "postgresql" or value is None:
            return value
        import json
        return json.loads(value)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Assessment(Base):
    """One grading job (manual or document). Maps to a stored result."""

    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(PortableUUID, primary_key=True, default=_new_uuid)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    student_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Full serialised result (AssessmentResponse or MultiAssessmentResponse JSON).
    result_json: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)

    question_results: Mapped[list[QuestionResult]] = relationship(
        "QuestionResult", back_populates="assessment", cascade="all, delete-orphan"
    )


class UserAccount(Base):
    """Persisted user credentials for login/register."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(PortableUUID, primary_key=True, default=_new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="teacher")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )


class QuestionResult(Base):
    """Per-question scoring breakdown for document assessments."""

    __tablename__ = "question_results"

    id: Mapped[str] = mapped_column(PortableUUID, primary_key=True, default=_new_uuid)
    assessment_id: Mapped[str] = mapped_column(
        PortableUUID, ForeignKey("assessments.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    question_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    student_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    tfidf_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sbert_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    combined_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    suggested_marks: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_marks: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_marks: Mapped[float | None] = mapped_column(Float, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(8), nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="completed")

    assessment: Mapped[Assessment] = relationship("Assessment", back_populates="question_results")


class LlmCache(Base):
    """Disk-backed LLM response cache migrated to DB (Phase 2)."""

    __tablename__ = "llm_cache"

    cache_key: Mapped[str] = mapped_column(String(512), primary_key=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    last_hit_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    hit_count: Mapped[int] = mapped_column(Integer, default=0)


class ProgressEvent(Base):
    """Persisted SSE progress events — used for replay on SSE reconnect."""

    __tablename__ = "progress_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(36), index=True)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    stage: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
