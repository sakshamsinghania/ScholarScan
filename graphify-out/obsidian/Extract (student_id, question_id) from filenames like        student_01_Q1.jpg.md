---
source_file: "backend/core/main.py"
type: "rationale"
community: "Scoring & Batch Pipeline"
location: "L116"
tags:
  - graphify/rationale
  - graphify/INFERRED
  - community/Scoring_&_Batch_Pipeline
---

# Extract (student_id, question_id) from filenames like:        student_01_Q1.jpg

## Connections
- [[AssessmentResult]] - `uses` [INFERRED]
- [[SBERTSimilarity]] - `uses` [INFERRED]
- [[_parse_filename()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/INFERRED #community/Scoring_&_Batch_Pipeline