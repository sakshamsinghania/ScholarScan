---
type: community
cohesion: 0.22
members: 9
---

# Results Route Tests

**Cohesion:** 0.22 - loosely connected
**Members:** 9 nodes

## Members
- [[.test_empty_results_returns_200()]] - code - backend/tests/test_results_route.py
- [[.test_filter_by_student_id()_1]] - code - backend/tests/test_results_route.py
- [[.test_filter_no_match_returns_empty()_1]] - code - backend/tests/test_results_route.py
- [[.test_mixed_result_shapes_are_returned_as_history_summaries()]] - code - backend/tests/test_results_route.py
- [[.test_response_has_count()]] - code - backend/tests/test_results_route.py
- [[.test_returns_stored_results_after_assessment()]] - code - backend/tests/test_results_route.py
- [[TestResultsRoute]] - code - backend/tests/test_results_route.py
- [[Tests for GET apiresults route.]] - rationale - backend/tests/test_results_route.py
- [[test_results_route.py]] - code - backend/tests/test_results_route.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Results_Route_Tests
SORT file.name ASC
```
