"""Tests for IDOR protection — cross-user access blocked."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app
from tests.conftest import register_user, auth_headers


@pytest.fixture
def app():
    app = create_app(testing=True)
    app.config["TESTING"] = True
    app.config["AUTH_REQUIRED"] = True
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


class TestIDOR:
    def test_user_cannot_access_other_users_task(self, client, app):
        user_a = register_user(client, "a@example.com", "password123")
        user_b = register_user(client, "b@example.com", "password123")

        progress_service = app.config["PROGRESS_SERVICE"]
        progress_service.create_task("task-owned-by-a", owner_id=user_a["user"]["id"])

        resp = client.get(
            "/api/task/task-owned-by-a/result",
            headers=auth_headers(user_b["access_token"]),
        )
        assert resp.status_code == 403

    def test_owner_can_access_own_task(self, client, app):
        user_a = register_user(client, "owner@example.com", "password123")

        progress_service = app.config["PROGRESS_SERVICE"]
        progress_service.create_task("task-mine", owner_id=user_a["user"]["id"])

        resp = client.get(
            "/api/task/task-mine/result",
            headers=auth_headers(user_a["access_token"]),
        )
        assert resp.status_code == 202

    def test_user_only_sees_own_results(self, client, app):
        user_a = register_user(client, "res_a@example.com", "password123")
        user_b = register_user(client, "res_b@example.com", "password123")

        store = app.config["RESULT_STORE"]
        store.store({
            "student_id": "s1", "marks": 8, "max_marks": 10,
            "grade": "B", "similarity_score": 0.8, "assessed_at": "2026-01-01T00:00:00",
        }, owner_id=user_a["user"]["id"])
        store.store({
            "student_id": "s2", "marks": 9, "max_marks": 10,
            "grade": "A", "similarity_score": 0.9, "assessed_at": "2026-01-01T00:00:00",
        }, owner_id=user_b["user"]["id"])

        resp = client.get("/api/results", headers=auth_headers(user_a["access_token"]))
        data = resp.get_json()
        assert data["count"] == 1

    def test_progress_stream_blocked_for_non_owner(self, client, app):
        user_a = register_user(client, "stream_a@example.com", "password123")
        user_b = register_user(client, "stream_b@example.com", "password123")

        progress_service = app.config["PROGRESS_SERVICE"]
        progress_service.create_task("stream-task", owner_id=user_a["user"]["id"])

        resp = client.get(
            "/api/progress/stream/stream-task",
            headers=auth_headers(user_b["access_token"]),
        )
        assert resp.status_code == 403
