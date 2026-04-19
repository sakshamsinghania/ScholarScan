---
source_file: "backend/core/scoring.py"
type: "code"
community: "Scoring & Batch Pipeline"
location: "L23"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Scoring_&_Batch_Pipeline
---

# AssessmentResult

## Connections
- [[.summary()]] - `method` [EXTRACTED]
- [[BatchConfig]] - `uses` [INFERRED]
- [[Configuration for batch assessment processing.      Attributes         model_an]] - `uses` [INFERRED]
- [[Extract (student_id, question_id) from filenames like        student_01_Q1.jpg]] - `uses` [INFERRED]
- [[Immutable result for one student's answer assessment.]] - `rationale_for` [EXTRACTED]
- [[Normalize text through the full core pipeline before similarity.      Data flow]] - `uses` [INFERRED]
- [[Print class-level summary statistics after all papers are graded.]] - `uses` [INFERRED]
- [[Run batch assessment on all images in the configured folder.]] - `uses` [INFERRED]
- [[Run the full assessment pipeline for one student answer image.      Args]] - `uses` [INFERRED]
- [[Write all assessment results to a CSV file.      Columns       student_id, ques]] - `uses` [INFERRED]
- [[score_answer()]] - `calls` [EXTRACTED]
- [[scoring.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/Scoring_&_Batch_Pipeline