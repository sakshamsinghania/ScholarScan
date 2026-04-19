"""Tests for GET /api/results route."""


class TestResultsRoute:
    def test_empty_results_returns_200(self, client):
        response = client.get("/api/results")
        assert response.status_code == 200
        data = response.get_json()
        assert data["results"] == []

    def test_returns_stored_results_after_assessment(self, client, valid_image_file):
        # First, create an assessment
        client.post(
            "/api/assess",
            data={
                "image": (valid_image_file, "test.jpg"),
                "model_answer": "Photosynthesis is the process...",
            },
            content_type="multipart/form-data",
        )

        # Then check results
        response = client.get("/api/results")
        data = response.get_json()
        assert len(data["results"]) == 1

    def test_filter_by_student_id(self, client, valid_image_file):
        # Create assessment with student_id
        client.post(
            "/api/assess",
            data={
                "image": (valid_image_file, "test.jpg"),
                "model_answer": "answer",
                "student_id": "alice",
            },
            content_type="multipart/form-data",
        )

        response = client.get("/api/results?student_id=alice")
        data = response.get_json()
        assert len(data["results"]) >= 1

    def test_filter_no_match_returns_empty(self, client):
        response = client.get("/api/results?student_id=nonexistent")
        data = response.get_json()
        assert data["results"] == []

    def test_response_has_count(self, client):
        response = client.get("/api/results")
        data = response.get_json()
        assert "count" in data
        assert data["count"] == 0

    def test_mixed_result_shapes_are_returned_as_history_summaries(self, client, app):
        app.config["RESULT_STORE"].store(
            {
                "student_id": "alice",
                "question_id": "Q1",
                "similarity_score": 0.82,
                "marks": 8,
                "max_marks": 10,
                "grade": "A",
                "assessed_at": "2026-04-16T10:00:00+00:00",
                "extracted_text": "full answer text",
            }
        )
        app.config["RESULT_STORE"].store(
            {
                "student_id": "alice",
                "total_score": 17,
                "max_total_score": 20,
                "total_questions": 2,
                "assessed_at": "2026-04-16T11:00:00+00:00",
                "results": [{"question_id": "Q1"}],
            }
        )

        response = client.get("/api/results")
        data = response.get_json()

        assert response.status_code == 200
        assert [item["result_type"] for item in data["results"]] == [
            "single_question",
            "multi_question",
        ]
        assert "extracted_text" not in data["results"][0]
        assert "results" not in data["results"][1]
