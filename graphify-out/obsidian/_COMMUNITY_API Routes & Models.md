---
type: community
cohesion: 0.11
members: 30
---

# API Routes & Models

**Cohesion:** 0.11 - loosely connected
**Members:** 30 nodes

## Members
- [[Accept an answer file + optional model answer  question paper.      Backward co]] - rationale - backend/routes/assess.py
- [[Accepted async assessment task.]] - rationale - backend/models/assessment.py
- [[AssessmentBaseModel]] - code - backend/models/assessment.py
- [[AssessmentResponse]] - code - backend/models/assessment.py
- [[ErrorResponse]] - code - backend/models/assessment.py
- [[GET apiresults — Retrieve stored assessment results.]] - rationale - backend/routes/results.py
- [[History-safe summary for a single-question assessment.]] - rationale - backend/models/assessment.py
- [[History-safe summary for an aggregate multi-question assessment.]] - rationale - backend/models/assessment.py
- [[JSON response shape for POST apiassess (single-question, backward compat).]] - rationale - backend/models/assessment.py
- [[JSON response shape for multi-question assessment.]] - rationale - backend/models/assessment.py
- [[Map raw stored result payloads into history-safe summaries.]] - rationale - backend/routes/results.py
- [[MultiAssessmentResponse]] - code - backend/models/assessment.py
- [[MultiHistoryEntry]] - code - backend/models/assessment.py
- [[POST apiassess — Submit student answers for assessment.]] - rationale - backend/routes/assess.py
- [[Pydantic schemas for assessment requestresponse validation.]] - rationale - backend/models/assessment.py
- [[QuestionResult]] - code - backend/models/assessment.py
- [[Result for a single question within a multi-question assessment.]] - rationale - backend/models/assessment.py
- [[Return all stored assessment results, with optional filtering.]] - rationale - backend/routes/results.py
- [[Run the evaluation pipeline in a background thread with progress tracking.]] - rationale - backend/routes/assess.py
- [[Shared base model for assessment schemas.]] - rationale - backend/models/assessment.py
- [[SingleHistoryEntry]] - code - backend/models/assessment.py
- [[Standard error envelope.]] - rationale - backend/models/assessment.py
- [[TaskStartResponse]] - code - backend/models/assessment.py
- [[_run_pipeline_async()]] - code - backend/routes/assess.py
- [[_to_history_entry()]] - code - backend/routes/results.py
- [[assess()]] - code - backend/routes/assess.py
- [[assess.py]] - code - backend/routes/assess.py
- [[assessment.py]] - code - backend/models/assessment.py
- [[get_results()]] - code - backend/routes/results.py
- [[results.py]] - code - backend/routes/results.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/API_Routes_&_Models
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Health Model]]

## Top bridge nodes
- [[AssessmentBaseModel]] - degree 10, connects to 1 community