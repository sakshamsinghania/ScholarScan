---
source_file: "backend/core/main.py"
type: "rationale"
community: "Scoring & Batch Pipeline"
location: "L40"
tags:
  - graphify/rationale
  - graphify/INFERRED
  - community/Scoring_&_Batch_Pipeline
---

# Configuration for batch assessment processing.      Attributes:         model_an

## Connections
- [[AssessmentResult]] - `uses` [INFERRED]
- [[BatchConfig]] - `rationale_for` [EXTRACTED]
- [[SBERTSimilarity]] - `uses` [INFERRED]

#graphify/rationale #graphify/INFERRED #community/Scoring_&_Batch_Pipeline