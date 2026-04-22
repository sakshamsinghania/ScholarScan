"""CRUD for Assessment + QuestionResult rows."""

from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from db.models import Assessment, QuestionResult


def store(
    session: Session,
    result: dict,
    owner_id: str | None = None,
) -> str:
    """Persist a result dict. Returns the generated assessment id."""
    assessment_id = str(uuid.uuid4())
    result_copy = deepcopy(result)
    result_copy["id"] = assessment_id
    if owner_id is not None:
        result_copy["owner_id"] = owner_id

    assessment = Assessment(
        id=assessment_id,
        owner_id=owner_id,
        student_id=result.get("student_id"),
        status="completed",
        completed_at=datetime.now(timezone.utc),
        result_json=result_copy,
    )

    # Persist per-question breakdown when present (MultiAssessmentResponse shape)
    questions: list[dict] = result.get("questions") or []
    for q in questions:
        qr = QuestionResult(
            assessment_id=assessment_id,
            question_id=q.get("question_id"),
            question_text=q.get("question_text"),
            student_answer=q.get("student_answer"),
            model_answer=q.get("model_answer"),
            tfidf_score=q.get("tfidf_score"),
            sbert_score=q.get("sbert_score"),
            combined_score=q.get("combined_score"),
            suggested_marks=q.get("marks") or q.get("suggested_marks"),
            final_marks=q.get("marks") or q.get("final_marks"),
            max_marks=q.get("max_marks"),
            grade=q.get("grade"),
            feedback=q.get("feedback"),
            status="completed",
        )
        assessment.question_results.append(qr)

    session.add(assessment)
    return assessment_id


def get_all(session: Session, owner_id: str | None = None) -> list[dict]:
    """Return all stored results, optionally filtered by owner."""
    query = session.query(Assessment)
    if owner_id is not None:
        query = query.filter(Assessment.owner_id == owner_id)
    rows = query.order_by(Assessment.created_at.desc()).all()
    return [deepcopy(r.result_json) for r in rows if r.result_json is not None]


def get_filtered(
    session: Session,
    student_id: str | None = None,
    question_id: str | None = None,
    owner_id: str | None = None,
) -> list[dict]:
    """Return results matching given filters."""
    query = session.query(Assessment)
    if owner_id is not None:
        query = query.filter(Assessment.owner_id == owner_id)
    if student_id is not None:
        query = query.filter(Assessment.student_id == student_id)

    rows = query.order_by(Assessment.created_at.desc()).all()
    results: list[dict[str, Any]] = [deepcopy(r.result_json) for r in rows if r.result_json is not None]

    if question_id is not None:
        results = [r for r in results if r.get("question_id") == question_id]

    return results
