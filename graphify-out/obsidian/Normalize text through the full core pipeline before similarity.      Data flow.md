---
source_file: "backend/core/main.py"
type: "rationale"
community: "Scoring & Batch Pipeline"
location: "L93"
tags:
  - graphify/rationale
  - graphify/INFERRED
  - community/Scoring_&_Batch_Pipeline
---

# Normalize text through the full core pipeline before similarity.      Data flow:

## Connections
- [[AssessmentResult]] - `uses` [INFERRED]
- [[SBERTSimilarity]] - `uses` [INFERRED]
- [[_prepare_similarity_inputs()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/INFERRED #community/Scoring_&_Batch_Pipeline