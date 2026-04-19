---
type: community
cohesion: 0.13
members: 15
---

# Assess Route Tests

**Cohesion:** 0.13 - loosely connected
**Members:** 15 nodes

## Members
- [[.test_image_without_model_answer_returns_202()]] - code - backend/tests/test_assess_route.py
- [[.test_invalid_file_type_returns_400()]] - code - backend/tests/test_assess_route.py
- [[.test_manual_mode_rejects_question_paper()]] - code - backend/tests/test_assess_route.py
- [[.test_missing_file_returns_400()]] - code - backend/tests/test_assess_route.py
- [[.test_non_positive_max_marks_returns_400()]] - code - backend/tests/test_assess_route.py
- [[.test_response_has_all_fields()]] - code - backend/tests/test_assess_route.py
- [[.test_scores_are_numeric()]] - code - backend/tests/test_assess_route.py
- [[.test_valid_request_returns_200()]] - code - backend/tests/test_assess_route.py
- [[Backward-compatible image + model_answer → single-question result.]] - rationale - backend/tests/test_assess_route.py
- [[New answer_file without model_answer → async pipeline with task_id.]] - rationale - backend/tests/test_assess_route.py
- [[TestAssessRouteLegacy]] - code - backend/tests/test_assess_route.py
- [[TestAssessRouteMultiQuestion]] - code - backend/tests/test_assess_route.py
- [[TestAssessRouteValidation]] - code - backend/tests/test_assess_route.py
- [[Tests for POST apiassess route — backward compat + multi-question.]] - rationale - backend/tests/test_assess_route.py
- [[test_assess_route.py]] - code - backend/tests/test_assess_route.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Assess_Route_Tests
SORT file.name ASC
```
