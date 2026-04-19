---
type: community
cohesion: 0.20
members: 16
---

# Result Storage Tests

**Cohesion:** 0.20 - loosely connected
**Members:** 16 nodes

## Members
- [[.test_evicts_oldest_results_when_capacity_is_exceeded()]] - code - backend/tests/test_result_storage_service.py
- [[.test_filter_by_both()]] - code - backend/tests/test_result_storage_service.py
- [[.test_filter_by_question_id()]] - code - backend/tests/test_result_storage_service.py
- [[.test_filter_by_student_id()]] - code - backend/tests/test_result_storage_service.py
- [[.test_filter_no_match_returns_empty()]] - code - backend/tests/test_result_storage_service.py
- [[.test_get_all_returns_copies()]] - code - backend/tests/test_result_storage_service.py
- [[.test_multiple_stores_accumulate()]] - code - backend/tests/test_result_storage_service.py
- [[.test_starts_empty()]] - code - backend/tests/test_result_storage_service.py
- [[.test_store_adds_result()]] - code - backend/tests/test_result_storage_service.py
- [[.test_stored_result_has_id()]] - code - backend/tests/test_result_storage_service.py
- [[TestFiltering]] - code - backend/tests/test_result_storage_service.py
- [[TestStore]] - code - backend/tests/test_result_storage_service.py
- [[Tests for ResultStorageService — in-memory assessment result store.]] - rationale - backend/tests/test_result_storage_service.py
- [[sample_result()]] - code - backend/tests/test_result_storage_service.py
- [[store()]] - code - backend/tests/test_result_storage_service.py
- [[test_result_storage_service.py]] - code - backend/tests/test_result_storage_service.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Result_Storage_Tests
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_App Bootstrap & Services]]

## Top bridge nodes
- [[TestStore]] - degree 8, connects to 1 community
- [[TestFiltering]] - degree 6, connects to 1 community
- [[Tests for ResultStorageService — in-memory assessment result store.]] - degree 2, connects to 1 community