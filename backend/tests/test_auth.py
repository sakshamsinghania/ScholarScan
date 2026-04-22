"""Tests for auth routes — register, login, refresh."""

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


class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "new@example.com", "password": "password123", "role": "teacher",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "new@example.com"
        assert data["user"]["role"] == "teacher"

    def test_register_missing_fields(self, client):
        resp = client.post("/api/auth/register", json={"email": "x@x.com"})
        assert resp.status_code == 400

    def test_register_short_password(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "x@x.com", "password": "short",
        })
        assert resp.status_code == 400

    def test_register_duplicate_email(self, client):
        client.post("/api/auth/register", json={
            "email": "dup@example.com", "password": "password123",
        })
        resp = client.post("/api/auth/register", json={
            "email": "dup@example.com", "password": "password456",
        })
        assert resp.status_code == 409

    def test_register_invalid_role(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "x@x.com", "password": "password123", "role": "student",
        })
        assert resp.status_code == 400


class TestLogin:
    def test_login_success(self, client):
        register_user(client, "login@example.com", "password123")
        resp = client.post("/api/auth/login", json={
            "email": "login@example.com", "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "access_token" in data
        assert data["user"]["email"] == "login@example.com"

    def test_login_wrong_password(self, client):
        register_user(client, "wrong@example.com", "password123")
        resp = client.post("/api/auth/login", json={
            "email": "wrong@example.com", "password": "wrongpass123",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "noone@example.com", "password": "password123",
        })
        assert resp.status_code == 401


class TestRefresh:
    def test_refresh_success(self, client):
        data = register_user(client, "refresh@example.com", "password123")
        resp = client.post("/api/auth/refresh", headers=auth_headers(data["refresh_token"]))
        assert resp.status_code == 200
        assert "access_token" in resp.get_json()

    def test_refresh_with_access_token_fails(self, client):
        data = register_user(client, "ref2@example.com", "password123")
        resp = client.post("/api/auth/refresh", headers=auth_headers(data["access_token"]))
        assert resp.status_code == 422 or resp.status_code == 401


class TestProtectedRoutes:
    def test_unauthenticated_assess_returns_401(self, client):
        resp = client.post("/api/assess")
        assert resp.status_code == 401

    def test_unauthenticated_results_returns_401(self, client):
        resp = client.get("/api/results")
        assert resp.status_code == 401

    def test_health_remains_public(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
