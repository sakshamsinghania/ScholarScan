---
source_file: "backend/tests/test_evaluation_service.py"
type: "rationale"
community: "Question Detection & Tests"
location: "L18"
tags:
  - graphify/rationale
  - graphify/INFERRED
  - community/Question_Detection_&_Tests
---

# Mock AssessmentService that returns predictable results.

## Connections
- [[DetectedQuestion]] - `uses` [INFERRED]
- [[EvaluationService]] - `uses` [INFERRED]
- [[LlmService]] - `uses` [INFERRED]
- [[mock_assessment_service()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/INFERRED #community/Question_Detection_&_Tests