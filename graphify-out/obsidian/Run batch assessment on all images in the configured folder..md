---
source_file: "backend/core/main.py"
type: "rationale"
community: "Scoring & Batch Pipeline"
location: "L286"
tags:
  - graphify/rationale
  - graphify/INFERRED
  - community/Scoring_&_Batch_Pipeline
---

# Run batch assessment on all images in the configured folder.

## Connections
- [[AssessmentResult]] - `uses` [INFERRED]
- [[SBERTSimilarity]] - `uses` [INFERRED]
- [[main()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/INFERRED #community/Scoring_&_Batch_Pipeline