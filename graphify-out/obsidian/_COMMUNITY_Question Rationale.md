---
type: community
cohesion: 1.00
members: 1
---

# Question Rationale

**Cohesion:** 1.00 - tightly connected
**Members:** 1 nodes

## Members
- [[Normalize question IDs to Q1, Q2, ... format.]] - rationale - backend/services/question_service.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Question_Rationale
SORT file.name ASC
```
