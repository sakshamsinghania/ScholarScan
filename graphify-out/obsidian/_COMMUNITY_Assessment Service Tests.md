---
type: community
cohesion: 0.12
members: 17
---

# Assessment Service Tests

**Cohesion:** 0.12 - loosely connected
**Members:** 17 nodes

## Members
- [[.test_assessed_at_is_iso_format()]] - code - backend/tests/test_assessment_service.py
- [[.test_calls_compute_similarity()]] - code - backend/tests/test_assessment_service.py
- [[.test_calls_extract_text_with_image_path()]] - code - backend/tests/test_assessment_service.py
- [[.test_calls_preprocess_for_both_modes()]] - code - backend/tests/test_assessment_service.py
- [[.test_calls_score_answer()]] - code - backend/tests/test_assessment_service.py
- [[.test_handles_custom_question_and_student_id()]] - code - backend/tests/test_assessment_service.py
- [[.test_raises_on_empty_ocr_text()]] - code - backend/tests/test_assessment_service.py
- [[.test_raises_on_whitespace_only_ocr()]] - code - backend/tests/test_assessment_service.py
- [[.test_response_contains_required_fields()]] - code - backend/tests/test_assessment_service.py
- [[.test_returns_response_dict()]] - code - backend/tests/test_assessment_service.py
- [[.test_stores_result()]] - code - backend/tests/test_assessment_service.py
- [[.test_wraps_ocr_exception()]] - code - backend/tests/test_assessment_service.py
- [[TestAssess]] - code - backend/tests/test_assessment_service.py
- [[TestAssessErrors]] - code - backend/tests/test_assessment_service.py
- [[mock_dependencies()]] - code - backend/tests/test_assessment_service.py
- [[service()_2]] - code - backend/tests/test_assessment_service.py
- [[test_assessment_service.py]] - code - backend/tests/test_assessment_service.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Assessment_Service_Tests
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_App Bootstrap & Services]]

## Top bridge nodes
- [[TestAssess]] - degree 12, connects to 1 community
- [[TestAssessErrors]] - degree 6, connects to 1 community
- [[test_assessment_service.py]] - degree 5, connects to 1 community
- [[mock_dependencies()]] - degree 2, connects to 1 community