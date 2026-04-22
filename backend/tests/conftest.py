"""Shared test fixtures for route tests."""

import os
import sys
import pytest
from io import BytesIO
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app


@pytest.fixture
def app():
    """Create a test Flask app with mock services and auth disabled."""
    app = create_app(testing=True)
    app.config["TESTING"] = True
    app.config["AUTH_REQUIRED"] = False
    yield app


@pytest.fixture
def app_with_auth():
    """Create a test Flask app with auth enabled."""
    app = create_app(testing=True)
    app.config["TESTING"] = True
    app.config["AUTH_REQUIRED"] = True
    yield app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def auth_client(app_with_auth):
    """Flask test client with auth enabled."""
    return app_with_auth.test_client()


@pytest.fixture
def valid_image_file():
    """Create a valid JPEG image as a BytesIO for upload."""
    buf = BytesIO()
    img = Image.new("RGB", (100, 100), color="white")
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def register_user(client, email="test@example.com", password="testpass123", role="teacher"):
    """Helper: register a user and return response JSON."""
    resp = client.post("/api/auth/register", json={
        "email": email, "password": password, "role": role,
    })
    return resp.get_json()


def auth_headers(token):
    """Helper: return Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}

