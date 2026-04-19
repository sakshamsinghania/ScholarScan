---
type: community
cohesion: 0.22
members: 9
---

# App Runtime Tests

**Cohesion:** 0.22 - loosely connected
**Members:** 9 nodes

## Members
- [[.test_build_llm_service_passes_rate_limit_settings()]] - code - backend/tests/test_app_runtime.py
- [[.test_config_defaults_cover_free_tier_rate_limits()]] - code - backend/tests/test_app_runtime.py
- [[.test_runtime_port_defaults_to_5050()]] - code - backend/tests/test_app_runtime.py
- [[.test_runtime_port_falls_back_when_env_is_invalid()]] - code - backend/tests/test_app_runtime.py
- [[.test_runtime_port_uses_env_value()]] - code - backend/tests/test_app_runtime.py
- [[TestLlmConfiguration]] - code - backend/tests/test_app_runtime.py
- [[TestRuntimePort]] - code - backend/tests/test_app_runtime.py
- [[Tests for backend runtime configuration helpers.]] - rationale - backend/tests/test_app_runtime.py
- [[test_app_runtime.py]] - code - backend/tests/test_app_runtime.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/App_Runtime_Tests
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_App Bootstrap & Services]]

## Top bridge nodes
- [[TestRuntimePort]] - degree 5, connects to 1 community
- [[TestLlmConfiguration]] - degree 4, connects to 1 community
- [[Tests for backend runtime configuration helpers.]] - degree 2, connects to 1 community