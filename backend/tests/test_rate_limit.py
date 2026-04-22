"""Tests for rate limiting."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app


@pytest.fixture
def app():
    app = create_app(testing=True)
    app.config["TESTING"] = True
    app.config["AUTH_REQUIRED"] = False
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


class TestRateLimit:
    def test_login_rate_limit(self, app):
        """Login endpoint should enforce rate limits."""
        client = app.test_client()
        for _ in range(10):
            client.post("/api/auth/login", json={
                "email": "x@x.com", "password": "wrongpass1",
            })

        resp = client.post("/api/auth/login", json={
            "email": "x@x.com", "password": "wrongpass1",
        })
        assert resp.status_code == 429
