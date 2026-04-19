"""Tests for POST /api/assess route — backward compat + multi-question."""

from io import BytesIO


class TestAssessRouteValidation:
    def test_missing_file_returns_400(self, client):
        response = client.post(
            "/api/assess",
            data={"model_answer": "Photosynthesis is..."},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert data["code"] == 400

    def test_invalid_file_type_returns_400(self, client):
        response = client.post(
            "/api/assess",
            data={
                "image": (BytesIO(b"fake txt content"), "doc.txt"),
                "model_answer": "answer text",
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 400

    def test_manual_mode_rejects_question_paper(self, client, valid_image_file):
        question_file = BytesIO(b"%PDF-1.4\n%mock pdf")

        response = client.post(
            "/api/assess",
            data={
                "image": (valid_image_file, "test.jpg"),
                "model_answer": "Teacher provided answer",
                "question_file": (question_file, "questions.pdf"),
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 400
        assert "question paper" in response.get_json()["error"].lower()

    def test_non_positive_max_marks_returns_400(self, client, valid_image_file):
        response = client.post(
            "/api/assess",
            data={
                "image": (valid_image_file, "test.jpg"),
                "model_answer": "Teacher provided answer",
                "max_marks": "0",
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 400
        assert "max_marks" in response.get_json()["error"]


class TestAssessRouteLegacy:
    """Backward-compatible: image + model_answer → single-question result."""

    def test_valid_request_returns_200(self, client, valid_image_file):
        response = client.post(
            "/api/assess",
            data={
                "image": (valid_image_file, "test.jpg"),
                "model_answer": "Photosynthesis is the process...",
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 200

    def test_response_has_all_fields(self, client, valid_image_file):
        response = client.post(
            "/api/assess",
            data={
                "image": (valid_image_file, "test.jpg"),
                "model_answer": "Photosynthesis is the process...",
            },
            content_type="multipart/form-data",
        )
        data = response.get_json()
        required_fields = {
            "extracted_text",
            "cleaned_text",
            "tfidf_score",
            "sbert_score",
            "similarity_score",
            "marks",
            "max_marks",
            "grade",
            "feedback",
            "assessed_at",
        }
        assert required_fields.issubset(data.keys())

    def test_scores_are_numeric(self, client, valid_image_file):
        response = client.post(
            "/api/assess",
            data={
                "image": (valid_image_file, "test.jpg"),
                "model_answer": "Photosynthesis is the process...",
            },
            content_type="multipart/form-data",
        )
        data = response.get_json()
        assert isinstance(data["similarity_score"], (int, float))
        assert isinstance(data["marks"], (int, float))


class TestAssessRouteMultiQuestion:
    """New: answer_file without model_answer → async pipeline with task_id."""

    def test_image_without_model_answer_returns_202(self, client, valid_image_file):
        response = client.post(
            "/api/assess",
            data={
                "answer_file": (valid_image_file, "test.jpg"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 202
        data = response.get_json()
        assert "task_id" in data
        assert data["status"] == "processing"
