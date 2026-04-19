---
source_file: "backend/core/main.py"
type: "rationale"
community: "Scoring & Batch Pipeline"
location: "L212"
tags:
  - graphify/rationale
  - graphify/INFERRED
  - community/Scoring_&_Batch_Pipeline
---

# Write all assessment results to a CSV file.      Columns:       student_id, ques

## Connections
- [[AssessmentResult]] - `uses` [INFERRED]
- [[SBERTSimilarity]] - `uses` [INFERRED]
- [[_export_csv()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/INFERRED #community/Scoring_&_Batch_Pipeline