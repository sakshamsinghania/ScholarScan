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
    """Create a test Flask app with mock services."""
    app = create_app(testing=True)
    app.config["TESTING"] = True
    yield app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def valid_image_file():
    """Create a valid JPEG image as a BytesIO for upload."""
    buf = BytesIO()
    img = Image.new("RGB", (100, 100), color="white")
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf
