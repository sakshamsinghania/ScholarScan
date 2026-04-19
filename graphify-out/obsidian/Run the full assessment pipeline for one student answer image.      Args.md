---
source_file: "backend/core/main.py"
type: "rationale"
community: "Scoring & Batch Pipeline"
location: "L148"
tags:
  - graphify/rationale
  - graphify/INFERRED
  - community/Scoring_&_Batch_Pipeline
---

# Run the full assessment pipeline for one student answer image.      Args:

## Connections
- [[AssessmentResult]] - `uses` [INFERRED]
- [[SBERTSimilarity]] - `uses` [INFERRED]
- [[process_single()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/INFERRED #community/Scoring_&_Batch_Pipeline