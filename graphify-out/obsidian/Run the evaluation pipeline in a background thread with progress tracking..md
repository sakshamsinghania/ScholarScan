---
source_file: "backend/routes/assess.py"
type: "rationale"
community: "API Routes & Models"
location: "L15"
tags:
  - graphify/rationale
  - graphify/INFERRED
  - community/API_Routes_&_Models
---

# Run the evaluation pipeline in a background thread with progress tracking.

## Connections
- [[AssessmentResponse]] - `uses` [INFERRED]
- [[MultiAssessmentResponse]] - `uses` [INFERRED]
- [[TaskStartResponse]] - `uses` [INFERRED]
- [[_run_pipeline_async()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/INFERRED #community/API_Routes_&_Models