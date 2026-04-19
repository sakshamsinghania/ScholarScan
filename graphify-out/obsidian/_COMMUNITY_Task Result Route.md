---
type: community
cohesion: 0.50
members: 4
---

# Task Result Route

**Cohesion:** 0.50 - moderately connected
**Members:** 4 nodes

## Members
- [[GET apitasktask_idresult — Fetch final result for a completed task.]] - rationale - backend/routes/task_result.py
- [[Retrieve the assessment result for a completed task.      Returns         200 +]] - rationale - backend/routes/task_result.py
- [[get_task_result()]] - code - backend/routes/task_result.py
- [[task_result.py]] - code - backend/routes/task_result.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Task_Result_Route
SORT file.name ASC
```
