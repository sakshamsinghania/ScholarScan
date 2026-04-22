"""File upload validation, temp storage, and cleanup — supports images and PDFs."""

import os
import uuid
from io import BytesIO

from PIL import Image


class FileHandler:
    """Handles file validation, temporary storage, and cleanup for images and PDFs."""

    _IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "bmp", "tiff"}
    _PDF_EXTENSIONS = {"pdf"}

    def __init__(
        self,
        upload_folder: str,
        allowed_extensions: set[str],
        max_file_size: int,
    ):
        self._upload_folder = upload_folder
        self._allowed_extensions = allowed_extensions
        self._max_file_size = max_file_size
        os.makedirs(self._upload_folder, exist_ok=True)

    def validate(self, filename: str | None, file_bytes: bytes) -> None:
        """Validate an uploaded file. Raises ValueError on failure."""
        if not filename:
            raise ValueError("No file provided")

        ext = self._get_extension(filename)
        if ext not in self._allowed_extensions:
            raise ValueError(
                f"File type not allowed: .{ext}. "
                f"Allowed: {', '.join(sorted(self._allowed_extensions))}"
            )

        if len(file_bytes) > self._max_file_size:
            raise ValueError(
                f"File too large: {len(file_bytes)} bytes. "
                f"Max: {self._max_file_size} bytes"
            )

        # Only verify PIL for images, not PDFs
        if ext in self._IMAGE_EXTENSIONS:
            try:
                img = Image.open(BytesIO(file_bytes))
                img.verify()
            except Exception:
                raise ValueError("Uploaded file is not a valid image")
        elif ext in self._PDF_EXTENSIONS:
            # Basic PDF header check
            if not file_bytes[:5] == b"%PDF-":
                raise ValueError("Uploaded file is not a valid PDF")

    def save_temp(self, filename: str, file_bytes: bytes) -> str:
        """Save file bytes to a temp path with a UUID name. Returns the path."""
        ext = self._get_extension(filename)
        unique_name = f"{uuid.uuid4()}.{ext}"
        path = os.path.join(self._upload_folder, unique_name)

        with open(path, "wb") as f:
            f.write(file_bytes)

        return path

    def cleanup(self, path: str) -> None:
        """Remove a temp file. Silently ignores missing files."""
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    def get_file_type(self, filename: str) -> str:
        """Determine file type from extension. Returns 'image' or 'pdf'."""
        ext = self._get_extension(filename)
        if ext in self._PDF_EXTENSIONS:
            return "pdf"
        return "image"

    @staticmethod
    def _get_extension(filename: str) -> str:
        return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
