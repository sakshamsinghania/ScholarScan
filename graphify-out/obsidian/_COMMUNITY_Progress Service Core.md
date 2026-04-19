---
type: community
cohesion: 0.11
members: 20
---

# Progress Service Core

**Cohesion:** 0.11 - loosely connected
**Members:** 20 nodes

## Members
- [[.__init__()_7]] - code - backend/services/progress_service.py
- [[._evict_expired_locked()]] - code - backend/services/progress_service.py
- [[.create_task()]] - code - backend/services/progress_service.py
- [[.get_current()]] - code - backend/services/progress_service.py
- [[.get_result()]] - code - backend/services/progress_service.py
- [[.store_result()]] - code - backend/services/progress_service.py
- [[.stream()]] - code - backend/services/progress_service.py
- [[.update()]] - code - backend/services/progress_service.py
- [[Generator that yields progress events until terminal stage.          Reads from]] - rationale - backend/services/progress_service.py
- [[Internal mutable state for a single task.]] - rationale - backend/services/progress_service.py
- [[Record a stage transition. Pushes event to the queue         so any SSE stream c]] - rationale - backend/services/progress_service.py
- [[Register a new task for progress tracking.]] - rationale - backend/services/progress_service.py
- [[Remove expired task state while holding the service lock.]] - rationale - backend/services/progress_service.py
- [[Retrieve the final result for a task.]] - rationale - backend/services/progress_service.py
- [[Snapshot of current progress for a task.]] - rationale - backend/services/progress_service.py
- [[Store the final assessment result for a completed task.]] - rationale - backend/services/progress_service.py
- [[Thread-safe pipeline progress tracking for real-time SSE updates.]] - rationale - backend/services/progress_service.py
- [[_TaskState]] - code - backend/services/progress_service.py
- [[_default_message()]] - code - backend/services/progress_service.py
- [[progress_service.py]] - code - backend/services/progress_service.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Progress_Service_Core
SORT file.name ASC
```

## Connections to other communities
- 8 edges to [[_COMMUNITY_App Bootstrap & Services]]

## Top bridge nodes
- [[._evict_expired_locked()]] - degree 8, connects to 1 community
- [[progress_service.py]] - degree 4, connects to 1 community
- [[.create_task()]] - degree 4, connects to 1 community
- [[.update()]] - degree 4, connects to 1 community
- [[.get_current()]] - degree 3, connects to 1 community