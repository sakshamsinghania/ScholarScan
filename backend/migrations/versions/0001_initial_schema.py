"""Initial schema — assessments, question_results, llm_cache, progress_events.

Revision ID: 0001
Revises:
Create Date: 2026-04-22
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _jsonb_or_text(dialect_name: str):
    """Use JSONB on Postgres, TEXT elsewhere (e.g. SQLite for tests)."""
    if dialect_name == "postgresql":
        return postgresql.JSONB()
    return sa.Text()


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.create_table(
        "assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=True, index=True),
        sa.Column("student_id", sa.String(255), nullable=True, index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="completed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result_json", _jsonb_or_text(dialect), nullable=True),
    )

    op.create_table(
        "question_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "assessment_id",
            sa.String(36),
            sa.ForeignKey("assessments.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("question_id", sa.String(255), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=True),
        sa.Column("student_answer", sa.Text(), nullable=True),
        sa.Column("model_answer", sa.Text(), nullable=True),
        sa.Column("tfidf_score", sa.Float(), nullable=True),
        sa.Column("sbert_score", sa.Float(), nullable=True),
        sa.Column("combined_score", sa.Float(), nullable=True),
        sa.Column("suggested_marks", sa.Float(), nullable=True),
        sa.Column("final_marks", sa.Float(), nullable=True),
        sa.Column("max_marks", sa.Float(), nullable=True),
        sa.Column("grade", sa.String(8), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="completed"),
    )

    op.create_table(
        "llm_cache",
        sa.Column("cache_key", sa.String(512), primary_key=True),
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("prompt_hash", sa.String(64), nullable=True),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "progress_events",
        sa.Column(
            "id",
            sa.BigInteger() if dialect == "postgresql" else sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column("task_id", sa.String(36), nullable=False, index=True),
        sa.Column("owner_id", sa.String(36), nullable=True),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("payload", _jsonb_or_text(dialect), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("progress_events")
    op.drop_table("llm_cache")
    op.drop_table("question_results")
    op.drop_table("assessments")
