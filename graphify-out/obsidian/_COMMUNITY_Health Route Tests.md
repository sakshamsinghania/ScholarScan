---
type: community
cohesion: 0.22
members: 9
---

# Health Route Tests

**Cohesion:** 0.22 - loosely connected
**Members:** 9 nodes

## Members
- [[.test_health_allows_dynamic_localhost_dev_origin()]] - code - backend/tests/test_health_route.py
- [[.test_health_allows_vite_dev_origin()]] - code - backend/tests/test_health_route.py
- [[.test_health_reports_capabilities()]] - code - backend/tests/test_health_route.py
- [[.test_health_returns_200()]] - code - backend/tests/test_health_route.py
- [[.test_health_returns_json()]] - code - backend/tests/test_health_route.py
- [[.test_health_status_field()]] - code - backend/tests/test_health_route.py
- [[TestHealthRoute]] - code - backend/tests/test_health_route.py
- [[Tests for GET apihealth route.]] - rationale - backend/tests/test_health_route.py
- [[test_health_route.py]] - code - backend/tests/test_health_route.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Health_Route_Tests
SORT file.name ASC
```
