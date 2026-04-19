---
type: community
cohesion: 0.23
members: 12
---

# Health Model

**Cohesion:** 0.23 - loosely connected
**Members:** 12 nodes

## Members
- [[BaseModel]] - code
- [[Capability-level availability flags.]] - rationale - backend/models/health.py
- [[CapabilityStatus]] - code - backend/models/health.py
- [[GET apihealth — System health check.]] - rationale - backend/routes/health.py
- [[HealthStatus]] - code - backend/models/health.py
- [[JSON response shape for GET apihealth.]] - rationale - backend/models/health.py
- [[Return system component status.]] - rationale - backend/routes/health.py
- [[SupportedModes]] - code - backend/models/health.py
- [[User-visible grading modes derived from component readiness.]] - rationale - backend/models/health.py
- [[health.py]] - code - backend/models/health.py
- [[health.py_1]] - code - backend/routes/health.py
- [[health_check()]] - code - backend/routes/health.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Health_Model
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_API Routes & Models]]

## Top bridge nodes
- [[BaseModel]] - degree 4, connects to 1 community