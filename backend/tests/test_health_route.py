"""Tests for GET /api/health route."""


class TestHealthRoute:
    def test_health_returns_200(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        response = client.get("/api/health")
        data = response.get_json()
        assert "status" in data
        assert "sbert_loaded" in data
        assert "spacy_model_loaded" in data
        assert "timestamp" in data

    def test_health_status_field(self, client):
        response = client.get("/api/health")
        data = response.get_json()
        assert data["status"] in ("healthy", "degraded")

    def test_health_allows_vite_dev_origin(self, client):
        response = client.get(
            "/api/health",
            headers={"Origin": "http://localhost:5173"},
        )

        assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"

    def test_health_allows_dynamic_localhost_dev_origin(self, client):
        response = client.get(
            "/api/health",
            headers={"Origin": "http://localhost:5174"},
        )

        assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5174"

    def test_health_reports_capabilities(self, client):
        response = client.get("/api/health")
        data = response.get_json()

        assert "capabilities" in data
        assert set(data["capabilities"]) >= {"ocr", "semantic_similarity", "llm", "pdf"}
