---
source_file: "backend/services/assessment_service.py"
type: "code"
community: "App Bootstrap & Services"
location: "L9"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/App_Bootstrap_&_Services
---

# AssessmentService

## Connections
- [[.__init__()_10]] - `method` [EXTRACTED]
- [[._run_ocr()]] - `method` [EXTRACTED]
- [[.assess()]] - `method` [EXTRACTED]
- [[Application factory. Creates a Flask app with all blueprints registered.      Ar]] - `uses` [INFERRED]
- [[Best-effort check for production runtime.]] - `uses` [INFERRED]
- [[Business layer that coordinates core modules to assess a student answer.      Us]] - `rationale_for` [EXTRACTED]
- [[Create mock callables that mimic core module functions.]] - `uses` [INFERRED]
- [[Create the shared LLM service with free-tier safeguard settings.]] - `uses` [INFERRED]
- [[EvaluationService]] - `uses` [INFERRED]
- [[Extract questions from a separate question paper.]] - `uses` [INFERRED]
- [[Extract text from file based on type.]] - `uses` [INFERRED]
- [[Fallback result when assessment fails for a question.]] - `uses` [INFERRED]
- [[Flask application factory — creates and configures the app.]] - `uses` [INFERRED]
- [[Multi-question assessment orchestrator.      Pipeline     1. Extract text from]] - `uses` [INFERRED]
- [[Orchestrate multi-question assessment PDF → Questions → LLM → Scoring.]] - `uses` [INFERRED]
- [[Read allowed frontend origins from env, with sensible local defaults.]] - `uses` [INFERRED]
- [[Record coarse capability flags for health reporting.]] - `uses` [INFERRED]
- [[ResultStorageService]] - `uses` [INFERRED]
- [[Return the backend port, with a collision-resistant local default.]] - `uses` [INFERRED]
- [[Run the full multi-question pipeline.          Args             answer_file_pat]] - `uses` [INFERRED]
- [[TestAssess]] - `uses` [INFERRED]
- [[TestAssessErrors]] - `uses` [INFERRED]
- [[Tests for AssessmentService — orchestrates core assessment pipeline.]] - `uses` [INFERRED]
- [[Wire up mock services for testing — no ML models loaded.]] - `uses` [INFERRED]
- [[Wire up real core modules — loads ML models.]] - `uses` [INFERRED]
- [[assessment_service.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/App_Bootstrap_&_Services