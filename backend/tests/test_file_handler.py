"""Tests for FileHandler — validates image and PDF uploads."""

import os
import tempfile
import pytest
from io import BytesIO
from PIL import Image

# We need to add backend to the path for imports
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from file_handling.file_handler import FileHandler


@pytest.fixture
def handler(tmp_path):
    """Create a handler with a temp upload directory."""
    return FileHandler(
        upload_folder=str(tmp_path),
        allowed_extensions={"jpg", "jpeg", "png"},
        max_file_size=5 * 1024 * 1024,
    )


@pytest.fixture
def valid_image_bytes():
    """Create a minimal valid JPEG image in memory."""
    buf = BytesIO()
    img = Image.new("RGB", (100, 100), color="white")
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.read()


class TestValidateImage:
    def test_rejects_none_file(self, handler):
        with pytest.raises(ValueError, match="No file provided"):
            handler.validate(filename=None, file_bytes=b"")

    def test_rejects_empty_filename(self, handler):
        with pytest.raises(ValueError, match="No file provided"):
            handler.validate(filename="", file_bytes=b"some data")

    def test_rejects_disallowed_extension(self, handler):
        with pytest.raises(ValueError, match="File type not allowed"):
            handler.validate(filename="paper.pdf", file_bytes=b"some data")

    def test_rejects_oversized_file(self, handler):
        huge = b"\x00" * (6 * 1024 * 1024)
        with pytest.raises(ValueError, match="File too large"):
            handler.validate(filename="big.jpg", file_bytes=huge)

    def test_rejects_corrupt_image(self, handler):
        with pytest.raises(ValueError, match="not a valid image"):
            handler.validate(filename="fake.jpg", file_bytes=b"not an image")

    def test_accepts_valid_jpeg(self, handler, valid_image_bytes):
        # Should not raise
        handler.validate(filename="answer.jpg", file_bytes=valid_image_bytes)

    def test_accepts_valid_png(self, handler):
        buf = BytesIO()
        img = Image.new("RGB", (50, 50), color="blue")
        img.save(buf, format="PNG")
        buf.seek(0)
        handler.validate(filename="answer.png", file_bytes=buf.read())


class TestSaveAndCleanup:
    def test_save_creates_file(self, handler, valid_image_bytes, tmp_path):
        path = handler.save_temp(filename="test.jpg", file_bytes=valid_image_bytes)
        assert os.path.exists(path)
        assert path.startswith(str(tmp_path))

    def test_save_uses_uuid_filename(self, handler, valid_image_bytes):
        path = handler.save_temp(filename="test.jpg", file_bytes=valid_image_bytes)
        basename = os.path.basename(path)
        # UUID is 36 chars + .jpg = 40 chars
        assert len(basename) > 10
        assert basename.endswith(".jpg")

    def test_cleanup_removes_file(self, handler, valid_image_bytes):
        path = handler.save_temp(filename="test.jpg", file_bytes=valid_image_bytes)
        assert os.path.exists(path)
        handler.cleanup(path)
        assert not os.path.exists(path)

    def test_cleanup_ignores_missing_file(self, handler):
        # Should not raise
        handler.cleanup("/nonexistent/path/to/file.jpg")
