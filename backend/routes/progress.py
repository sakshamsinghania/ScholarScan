"""GET /api/progress/stream/<task_id> — SSE pipeline progress stream."""

import json

from flask import Blueprint, Response, current_app, jsonify

progress_bp = Blueprint("progress", __name__)


@progress_bp.route("/api/progress/stream/<task_id>")
def stream_progress(task_id: str):
    """
    Stream pipeline progress as Server-Sent Events.

    Each event is formatted as: ``data: {json}\n\n``
    The stream ends when the pipeline reaches a terminal stage (completed/error).
    """
    progress_service = current_app.config["PROGRESS_SERVICE"]

    # Check task exists before starting stream
    if progress_service.get_current(task_id) is None:
        return jsonify({"error": "Task not found", "code": 404}), 404

    def generate():
        for event in progress_service.stream(task_id, timeout=120):
            yield f"data: {json.dumps(event)}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
