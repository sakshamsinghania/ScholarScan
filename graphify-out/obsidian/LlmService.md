---
source_file: "backend/services/llm_service.py"
type: "code"
community: "App Bootstrap & Services"
location: "L22"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/App_Bootstrap_&_Services
---

# LlmService

## Connections
- [[.__init__()_9]] - `method` [EXTRACTED]
- [[._build_cache_key()]] - `method` [EXTRACTED]
- [[._request_model_answer()]] - `method` [EXTRACTED]
- [[.close()_1]] - `method` [EXTRACTED]
- [[.generate_batch_answers()]] - `method` [EXTRACTED]
- [[.generate_model_answer()]] - `method` [EXTRACTED]
- [[Application factory. Creates a Flask app with all blueprints registered.      Ar]] - `uses` [INFERRED]
- [[Best-effort check for production runtime.]] - `uses` [INFERRED]
- [[Build a Google GenAI client error with optional retry-after header.]] - `uses` [INFERRED]
- [[Create a mock Google GenAI client.]] - `uses` [INFERRED]
- [[Create the shared LLM service with free-tier safeguard settings.]] - `uses` [INFERRED]
- [[Deterministic clock for rate-limit and backoff tests.]] - `uses` [INFERRED]
- [[EvaluationService]] - `uses` [INFERRED]
- [[Extract questions from a separate question paper.]] - `uses` [INFERRED]
- [[Extract text from file based on type.]] - `uses` [INFERRED]
- [[FakeClock]] - `uses` [INFERRED]
- [[Fallback result when assessment fails for a question.]] - `uses` [INFERRED]
- [[Flask application factory — creates and configures the app.]] - `uses` [INFERRED]
- [[GeminiRequestCoordinator]] - `uses` [INFERRED]
- [[Generates model answers via Google Gemini.     Degrades gracefully — returns emp]] - `rationale_for` [EXTRACTED]
- [[Mock AssessmentService that returns predictable results.]] - `uses` [INFERRED]
- [[Multi-question assessment orchestrator.      Pipeline     1. Extract text from]] - `uses` [INFERRED]
- [[Orchestrate multi-question assessment PDF → Questions → LLM → Scoring.]] - `uses` [INFERRED]
- [[Read allowed frontend origins from env, with sensible local defaults.]] - `uses` [INFERRED]
- [[Record coarse capability flags for health reporting.]] - `uses` [INFERRED]
- [[Return the backend port, with a collision-resistant local default.]] - `uses` [INFERRED]
- [[Run the full multi-question pipeline.          Args             answer_file_pat]] - `uses` [INFERRED]
- [[TestAggregation]] - `uses` [INFERRED]
- [[TestEvaluateImage]] - `uses` [INFERRED]
- [[TestEvaluatePdf]] - `uses` [INFERRED]
- [[TestEvaluateWithQuestionPaper]] - `uses` [INFERRED]
- [[TestGenerateBatchAnswers]] - `uses` [INFERRED]
- [[TestGenerateModelAnswer]] - `uses` [INFERRED]
- [[TestIsConfigured]] - `uses` [INFERRED]
- [[Tests for EvaluationService — multi-question assessment orchestration.]] - `uses` [INFERRED]
- [[Tests for LlmService — LLM model answer generation via Google Gemini.]] - `uses` [INFERRED]
- [[Wire up mock services for testing — no ML models loaded.]] - `uses` [INFERRED]
- [[Wire up real core modules — loads ML models.]] - `uses` [INFERRED]
- [[llm_service.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/App_Bootstrap_&_Services