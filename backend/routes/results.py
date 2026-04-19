"""GET /api/results — Retrieve stored assessment results."""

from flask import Blueprint, current_app, jsonify, request
from models.assessment import MultiHistoryEntry, SingleHistoryEntry

results_bp = Blueprint("results", __name__)


def _to_history_entry(result: dict) -> dict:
    """Map raw stored result payloads into history-safe summaries."""
    if "results" in result and "total_questions" in result:
        max_total = result.get("max_total_score") or 0
        summary = MultiHistoryEntry.model_validate(
            {
                "id": result["id"],
                "result_type": "multi_question",
                "student_id": result.get("student_id", "anonymous"),
                "assessed_at": result.get("assessed_at"),
                "total_questions": result.get("total_questions", 0),
                "total_score": result.get("total_score", 0),
                "max_total_score": max_total,
                "average_score_ratio": (
                    result.get("total_score", 0) / max_total if max_total else 0
                ),
            }
        )
        return summary.model_dump(mode="json")

    summary = SingleHistoryEntry.model_validate(
        {
            "id": result["id"],
            "result_type": "single_question",
            "student_id": result.get("student_id", "anonymous"),
            "assessed_at": result.get("assessed_at"),
            "question_id": result.get("question_id", "Q1"),
            "score_ratio": result.get("similarity_score", 0),
            "marks": result.get("marks", 0),
            "max_marks": result.get("max_marks", 1),
            "grade": result.get("grade", "N/A"),
        }
    )
    return summary.model_dump(mode="json")


@results_bp.route("/api/results", methods=["GET"])
def get_results():
    """Return all stored assessment results, with optional filtering."""
    store = current_app.config["RESULT_STORE"]

    student_id = request.args.get("student_id")
    question_id = request.args.get("question_id")

    if student_id or question_id:
        results = store.get_filtered(
            student_id=student_id, question_id=question_id
        )
    else:
        results = store.get_all()

    history = [_to_history_entry(result) for result in results]
    return jsonify({"results": history, "count": len(history)})
