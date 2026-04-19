---
source_file: "backend/services/result_storage_service.py"
type: "code"
community: "App Bootstrap & Services"
location: "L8"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/App_Bootstrap_&_Services
---

# ResultStorageService

## Connections
- [[.__init__()_11]] - `method` [EXTRACTED]
- [[.get_all()]] - `method` [EXTRACTED]
- [[.get_filtered()]] - `method` [EXTRACTED]
- [[.store()]] - `method` [EXTRACTED]
- [[Application factory. Creates a Flask app with all blueprints registered.      Ar]] - `uses` [INFERRED]
- [[AssessmentService]] - `uses` [INFERRED]
- [[Best-effort check for production runtime.]] - `uses` [INFERRED]
- [[Business layer that coordinates core modules to assess a student answer.      Us]] - `uses` [INFERRED]
- [[Create mock callables that mimic core module functions.]] - `uses` [INFERRED]
- [[Create the shared LLM service with free-tier safeguard settings.]] - `uses` [INFERRED]
- [[EvaluationService]] - `uses` [INFERRED]
- [[Extract questions from a separate question paper.]] - `uses` [INFERRED]
- [[Extract text from file based on type.]] - `uses` [INFERRED]
- [[Extract text from image with error wrapping.]] - `uses` [INFERRED]
- [[Fallback result when assessment fails for a question.]] - `uses` [INFERRED]
- [[Flask application factory — creates and configures the app.]] - `uses` [INFERRED]
- [[Map core AssessmentResult to API response dict.]] - `uses` [INFERRED]
- [[Multi-question assessment orchestrator.      Pipeline     1. Extract text from]] - `uses` [INFERRED]
- [[Orchestrate multi-question assessment PDF → Questions → LLM → Scoring.]] - `uses` [INFERRED]
- [[Orchestrates the core assessment pipeline OCR → NLP → Similarity → Scoring.]] - `uses` [INFERRED]
- [[Read allowed frontend origins from env, with sensible local defaults.]] - `uses` [INFERRED]
- [[Record coarse capability flags for health reporting.]] - `uses` [INFERRED]
- [[Return the backend port, with a collision-resistant local default.]] - `uses` [INFERRED]
- [[Run the full assessment pipeline for a single student answer.          Args]] - `uses` [INFERRED]
- [[Run the full multi-question pipeline.          Args             answer_file_pat]] - `uses` [INFERRED]
- [[TestAssess]] - `uses` [INFERRED]
- [[TestAssessErrors]] - `uses` [INFERRED]
- [[TestFiltering]] - `uses` [INFERRED]
- [[TestStore]] - `uses` [INFERRED]
- [[Tests for AssessmentService — orchestrates core assessment pipeline.]] - `uses` [INFERRED]
- [[Tests for ResultStorageService — in-memory assessment result store.]] - `uses` [INFERRED]
- [[Thread-safe in-memory storage for assessment results.]] - `rationale_for` [EXTRACTED]
- [[Wire up mock services for testing — no ML models loaded.]] - `uses` [INFERRED]
- [[Wire up real core modules — loads ML models.]] - `uses` [INFERRED]
- [[result_storage_service.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/App_Bootstrap_&_Services