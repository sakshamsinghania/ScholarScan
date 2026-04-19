---
source_file: "backend/services/evaluation_service.py"
type: "rationale"
community: "App Bootstrap & Services"
location: "L1"
tags:
  - graphify/rationale
  - graphify/INFERRED
  - community/App_Bootstrap_&_Services
---

# Orchestrate multi-question assessment: PDF → Questions → LLM → Scoring.

## Connections
- [[AssessmentService]] - `uses` [INFERRED]
- [[LlmService]] - `uses` [INFERRED]
- [[PdfService]] - `uses` [INFERRED]
- [[QuestionService]] - `uses` [INFERRED]
- [[ResultStorageService]] - `uses` [INFERRED]
- [[evaluation_service.py]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/INFERRED #community/App_Bootstrap_&_Services