"""GET /api/task/<task_id>/result — Fetch final result for a completed task."""

from flask import Blueprint, current_app, jsonify
from app import auth_required_conditional, get_current_user_id

task_result_bp = Blueprint("task_result", __name__)


@task_result_bp.route("/api/task/<task_id>/result")
@auth_required_conditional
def get_task_result(task_id: str):
    """
    Retrieve the assessment result for a completed task.

    Returns:
        200 + result dict — if task is done and result stored.
        202 — if task exists but is still processing.
        403 — if task belongs to another user.
        404 — if task_id is unknown.
    """
    progress_service = current_app.config["PROGRESS_SERVICE"]

    current = progress_service.get_current(task_id)
    if current is None:
        return jsonify({"error": "Task not found", "code": 404}), 404

    owner_id = get_current_user_id()
    if not progress_service.is_owner(task_id, owner_id):
        return jsonify({"error": "Forbidden", "code": 403}), 403

    result = progress_service.get_result(task_id)
    if result is not None:
        return jsonify(result)

    return jsonify({"status": "processing", "task_id": task_id}), 202
