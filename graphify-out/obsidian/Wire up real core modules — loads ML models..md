---
source_file: "backend/app.py"
type: "rationale"
community: "App Bootstrap & Services"
location: "L132"
tags:
  - graphify/rationale
  - graphify/INFERRED
  - community/App_Bootstrap_&_Services
---

# Wire up real core modules — loads ML models.

## Connections
- [[AssessmentService]] - `uses` [INFERRED]
- [[Config]] - `uses` [INFERRED]
- [[EvaluationService]] - `uses` [INFERRED]
- [[FileHandler]] - `uses` [INFERRED]
- [[LlmService]] - `uses` [INFERRED]
- [[PdfService]] - `uses` [INFERRED]
- [[ProgressService]] - `uses` [INFERRED]
- [[QuestionService]] - `uses` [INFERRED]
- [[ResultStorageService]] - `uses` [INFERRED]
- [[SBERTSimilarity]] - `uses` [INFERRED]
- [[_register_real_services()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/INFERRED #community/App_Bootstrap_&_Services