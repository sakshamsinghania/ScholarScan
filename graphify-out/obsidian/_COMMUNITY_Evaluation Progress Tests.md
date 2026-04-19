---
type: community
cohesion: 0.48
members: 7
---

# Evaluation Progress Tests

**Cohesion:** 0.48 - moderately connected
**Members:** 7 nodes

## Members
- [[.test_callback_invoked_during_pipeline()]] - code - backend/tests/test_evaluation_progress.py
- [[.test_callback_none_is_safe()]] - code - backend/tests/test_evaluation_progress.py
- [[.test_callback_receives_messages()]] - code - backend/tests/test_evaluation_progress.py
- [[.test_error_in_pipeline_calls_error_callback()]] - code - backend/tests/test_evaluation_progress.py
- [[TestProgressCallback]] - code - backend/tests/test_evaluation_progress.py
- [[_make_service()]] - code - backend/tests/test_evaluation_progress.py
- [[test_evaluation_progress.py]] - code - backend/tests/test_evaluation_progress.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Evaluation_Progress_Tests
SORT file.name ASC
```

## Connections to other communities
- 4 edges to [[_COMMUNITY_App Bootstrap & Services]]

## Top bridge nodes
- [[TestProgressCallback]] - degree 7, connects to 1 community
- [[_make_service()]] - degree 6, connects to 1 community
- [[test_evaluation_progress.py]] - degree 3, connects to 1 community