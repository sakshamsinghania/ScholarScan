"""CRUD for assessments collection."""

from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from pymongo.database import Database


def store(db: Database, result: dict, owner_id: str | None = None) -> str:
    """Persist a result dict. Returns the generated assessment id."""
    assessment_id = str(uuid.uuid4())
    result_copy = deepcopy(result)
    result_copy["id"] = assessment_id
    if owner_id is not None:
        result_copy["owner_id"] = owner_id

    now = datetime.now(timezone.utc)
    doc = {
        "_id": assessment_id,
        "owner_id": owner_id,
        "student_id": result.get("student_id"),
        "status": "completed",
        "created_at": now,
        "completed_at": now,
        "result_json": result_copy,
    }
    db["assessments"].insert_one(doc)
    return assessment_id


def get_all(db: Database, owner_id: str | None = None) -> list[dict]:
    """Return all stored results, optionally filtered by owner."""
    query: dict[str, Any] = {}
    if owner_id is not None:
        query["owner_id"] = owner_id
    rows = db["assessments"].find(query).sort("created_at", -1)
    return [deepcopy(r["result_json"]) for r in rows if r.get("result_json") is not None]


def get_filtered(
    db: Database,
    student_id: str | None = None,
    question_id: str | None = None,
    owner_id: str | None = None,
) -> list[dict]:
    """Return results matching given filters."""
    query: dict[str, Any] = {}
    if owner_id is not None:
        query["owner_id"] = owner_id
    if student_id is not None:
        query["student_id"] = student_id

    rows = db["assessments"].find(query).sort("created_at", -1)
    results = [deepcopy(r["result_json"]) for r in rows if r.get("result_json") is not None]

    if question_id is not None:
        results = [r for r in results if r.get("question_id") == question_id]

    return results
