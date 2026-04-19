"""Tests for OCR preprocessing helpers."""

import os
import sys
from unittest.mock import patch

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.ocr_google_vision import _deskew


def test_deskew_uses_text_pixels_in_xy_order():
    image = np.array(
        [
            [255, 0],
            [0, 255],
        ],
        dtype=np.uint8,
    )

    captured_coords = []

    def fake_min_area_rect(coords):
        captured_coords.append(coords.copy())
        return ((0, 0), (1, 1), -10)

    with patch("core.ocr_google_vision.cv2.minAreaRect", side_effect=fake_min_area_rect), patch(
        "core.ocr_google_vision.cv2.getRotationMatrix2D",
        return_value=np.eye(2, 3),
    ), patch(
        "core.ocr_google_vision.cv2.warpAffine",
        return_value=image,
    ):
        _deskew(image)

    assert len(captured_coords) == 1
    np.testing.assert_array_equal(captured_coords[0], np.array([[1, 0], [0, 1]]))
