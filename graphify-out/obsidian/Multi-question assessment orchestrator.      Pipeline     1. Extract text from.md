---
source_file: "backend/services/evaluation_service.py"
type: "rationale"
community: "App Bootstrap & Services"
location: "L17"
tags:
  - graphify/rationale
  - graphify/INFERRED
  - community/App_Bootstrap_&_Services
---

# Multi-question assessment orchestrator.      Pipeline:     1. Extract text from

## Connections
- [[AssessmentService]] - `uses` [INFERRED]
- [[EvaluationService]] - `rationale_for` [EXTRACTED]
- [[LlmService]] - `uses` [INFERRED]
- [[PdfService]] - `uses` [INFERRED]
- [[QuestionService]] - `uses` [INFERRED]
- [[ResultStorageService]] - `uses` [INFERRED]

#graphify/rationale #graphify/INFERRED #community/App_Bootstrap_&_Services