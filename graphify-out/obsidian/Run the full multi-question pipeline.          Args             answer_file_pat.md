---
source_file: "backend/services/evaluation_service.py"
type: "rationale"
community: "App Bootstrap & Services"
location: "L55"
tags:
  - graphify/rationale
  - graphify/INFERRED
  - community/App_Bootstrap_&_Services
---

# Run the full multi-question pipeline.          Args:             answer_file_pat

## Connections
- [[.evaluate()]] - `rationale_for` [EXTRACTED]
- [[AssessmentService]] - `uses` [INFERRED]
- [[LlmService]] - `uses` [INFERRED]
- [[PdfService]] - `uses` [INFERRED]
- [[QuestionService]] - `uses` [INFERRED]
- [[ResultStorageService]] - `uses` [INFERRED]

#graphify/rationale #graphify/INFERRED #community/App_Bootstrap_&_Services