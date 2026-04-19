---
type: community
cohesion: 0.50
members: 4
---

# Progress Routes

**Cohesion:** 0.50 - moderately connected
**Members:** 4 nodes

## Members
- [[GET apiprogressstreamtask_id — SSE pipeline progress stream.]] - rationale - backend/routes/progress.py
- [[Stream pipeline progress as Server-Sent Events.      Each event is formatted as]] - rationale - backend/routes/progress.py
- [[progress.py]] - code - backend/routes/progress.py
- [[stream_progress()]] - code - backend/routes/progress.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Progress_Routes
SORT file.name ASC
```
