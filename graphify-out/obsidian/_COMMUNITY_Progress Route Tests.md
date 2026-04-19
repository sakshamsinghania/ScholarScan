---
type: community
cohesion: 0.17
members: 12
---

# Progress Route Tests

**Cohesion:** 0.17 - loosely connected
**Members:** 12 nodes

## Members
- [[.test_result_not_found()_1]] - code - backend/tests/test_progress_route.py
- [[.test_result_ready()]] - code - backend/tests/test_progress_route.py
- [[.test_result_still_processing()]] - code - backend/tests/test_progress_route.py
- [[.test_stream_404_for_unknown_task()]] - code - backend/tests/test_progress_route.py
- [[.test_stream_includes_step_and_total()]] - code - backend/tests/test_progress_route.py
- [[.test_stream_returns_event_stream_content_type()]] - code - backend/tests/test_progress_route.py
- [[.test_stream_yields_sse_formatted_events()]] - code - backend/tests/test_progress_route.py
- [[TestProgressStreamRoute]] - code - backend/tests/test_progress_route.py
- [[TestTaskResultRoute]] - code - backend/tests/test_progress_route.py
- [[Tests for SSE progress streaming route and task result route.]] - rationale - backend/tests/test_progress_route.py
- [[client()_1]] - code - backend/tests/test_progress_route.py
- [[test_progress_route.py]] - code - backend/tests/test_progress_route.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Progress_Route_Tests
SORT file.name ASC
```
