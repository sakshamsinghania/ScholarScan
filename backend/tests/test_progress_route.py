"""Tests for SSE progress streaming route and task result route."""

import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app


@pytest.fixture
def client():
    app = create_app(testing=True)
    app.config["AUTH_REQUIRED"] = False
    with app.test_client() as c:
        yield c, app


class TestProgressStreamRoute:
    def test_stream_returns_event_stream_content_type(self, client):
        c, app = client
        # Create a task in the progress service
        progress = app.config["PROGRESS_SERVICE"]
        progress.create_task("test-task-1")
        progress.update("test-task-1", "completed", "completed", "Done!")

        response = c.get("/api/progress/stream/test-task-1")
        assert response.content_type.startswith("text/event-stream")

    def test_stream_yields_sse_formatted_events(self, client):
        c, app = client
        progress = app.config["PROGRESS_SERVICE"]
        progress.create_task("test-task-2")
        progress.update("test-task-2", "upload_received", "completed")
        progress.update("test-task-2", "completed", "completed", "Done!")

        response = c.get("/api/progress/stream/test-task-2")
        data = response.get_data(as_text=True)

        # SSE format: each event is "data: {...}\n\n"
        lines = [l for l in data.strip().split("\n") if l.startswith("data:")]
        assert len(lines) >= 2

        # Parse first event
        first_event = json.loads(lines[0].removeprefix("data: "))
        assert first_event["stage"] == "upload_received"

    def test_stream_404_for_unknown_task(self, client):
        c, _ = client
        response = c.get("/api/progress/stream/nonexistent")
        assert response.status_code == 404

    def test_stream_includes_step_and_total(self, client):
        c, app = client
        progress = app.config["PROGRESS_SERVICE"]
        progress.create_task("test-task-3")
        progress.update("test-task-3", "text_extraction", "running", "Extracting...")
        progress.update("test-task-3", "completed", "completed")

        response = c.get("/api/progress/stream/test-task-3")
        data = response.get_data(as_text=True)
        lines = [l for l in data.strip().split("\n") if l.startswith("data:")]
        event = json.loads(lines[0].removeprefix("data: "))
        assert "step" in event
        assert "total_steps" in event


class TestTaskResultRoute:
    def test_result_ready(self, client):
        c, app = client
        progress = app.config["PROGRESS_SERVICE"]
        progress.create_task("result-task-1")
        progress.store_result("result-task-1", {"total_score": 14, "max_total_score": 20})

        response = c.get("/api/task/result-task-1/result")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total_score"] == 14

    def test_result_still_processing(self, client):
        c, app = client
        progress = app.config["PROGRESS_SERVICE"]
        progress.create_task("result-task-2")

        response = c.get("/api/task/result-task-2/result")
        assert response.status_code == 202
        data = response.get_json()
        assert data["status"] == "processing"

    def test_result_not_found(self, client):
        c, _ = client
        response = c.get("/api/task/nonexistent/result")
        assert response.status_code == 404
