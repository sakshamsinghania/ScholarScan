---
type: community
cohesion: 0.04
members: 57
---

# Question Detection & Tests

**Cohesion:** 0.04 - loosely connected
**Members:** 57 nodes

## Members
- [[._build_question_list()]] - code - backend/services/question_service.py
- [[._build_segments()]] - code - backend/services/question_service.py
- [[.detect_questions()]] - code - backend/services/question_service.py
- [[.extract_questions_only()]] - code - backend/services/question_service.py
- [[.test_answer_text_extracted()]] - code - backend/tests/test_question_service.py
- [[.test_calls_pdf_extraction()]] - code - backend/tests/test_evaluation_service.py
- [[.test_detects_dot_numbered()]] - code - backend/tests/test_question_service.py
- [[.test_detects_parenthesized_numbers()]] - code - backend/tests/test_question_service.py
- [[.test_detects_q_numbered_pattern()]] - code - backend/tests/test_question_service.py
- [[.test_detects_question_word_pattern()]] - code - backend/tests/test_question_service.py
- [[.test_empty_text_returns_empty()]] - code - backend/tests/test_question_service.py
- [[.test_extracts_only_questions()]] - code - backend/tests/test_question_service.py
- [[.test_generates_llm_answers()]] - code - backend/tests/test_evaluation_service.py
- [[.test_max_total_score_sums_max_marks()]] - code - backend/tests/test_evaluation_service.py
- [[.test_raises_when_llm_is_unavailable_for_multi_question_grading()]] - code - backend/tests/test_evaluation_service.py
- [[.test_raises_when_text_extraction_is_empty()]] - code - backend/tests/test_evaluation_service.py
- [[.test_rejects_student_answer_as_reference_fallback()]] - code - backend/tests/test_evaluation_service.py
- [[.test_result_count_matches_questions()]] - code - backend/tests/test_evaluation_service.py
- [[.test_returns_detected_question_objects()]] - code - backend/tests/test_question_service.py
- [[.test_returns_list_of_dicts()]] - code - backend/tests/test_question_service.py
- [[.test_returns_multi_result()]] - code - backend/tests/test_evaluation_service.py
- [[.test_reuses_cached_model_answer_for_repeated_question_text()]] - code - backend/tests/test_evaluation_service.py
- [[.test_single_block_fallback()]] - code - backend/tests/test_question_service.py
- [[.test_student_id_in_result()]] - code - backend/tests/test_evaluation_service.py
- [[.test_total_score_sums_marks()]] - code - backend/tests/test_evaluation_service.py
- [[.test_uses_ocr_for_image()]] - code - backend/tests/test_evaluation_service.py
- [[.test_uses_question_paper()]] - code - backend/tests/test_evaluation_service.py
- [[.test_whitespace_only_returns_empty()]] - code - backend/tests/test_question_service.py
- [[A single detected question with its associated answer text.]] - rationale - backend/services/question_service.py
- [[Build Q&A segments from regex matches using position-based splitting.]] - rationale - backend/services/question_service.py
- [[Build question-only list from matches.]] - rationale - backend/services/question_service.py
- [[Detect and parse questions from raw text using regex patterns.]] - rationale - backend/services/question_service.py
- [[DetectedQuestion]] - code - backend/services/question_service.py
- [[Extract just questions (for question paper input).         Returns list of {que]] - rationale - backend/services/question_service.py
- [[Mock AssessmentService that returns predictable results.]] - rationale - backend/tests/test_evaluation_service.py
- [[Parse text into structured Q&A segments.          Detection strategy (layered)]] - rationale - backend/services/question_service.py
- [[TestAggregation]] - code - backend/tests/test_evaluation_service.py
- [[TestDetectQuestions]] - code - backend/tests/test_question_service.py
- [[TestEvaluateImage]] - code - backend/tests/test_evaluation_service.py
- [[TestEvaluatePdf]] - code - backend/tests/test_evaluation_service.py
- [[TestEvaluateWithQuestionPaper]] - code - backend/tests/test_evaluation_service.py
- [[TestExtractQuestionsOnly]] - code - backend/tests/test_question_service.py
- [[Tests for EvaluationService — multi-question assessment orchestration.]] - rationale - backend/tests/test_evaluation_service.py
- [[Tests for QuestionService — question detection and Q&A parsing.]] - rationale - backend/tests/test_question_service.py
- [[_has_answer_after()]] - code - backend/services/question_service.py
- [[_normalize_id()]] - code - backend/services/question_service.py
- [[mock_assessment_service()]] - code - backend/tests/test_evaluation_service.py
- [[mock_llm_service()]] - code - backend/tests/test_evaluation_service.py
- [[mock_ocr_fn()]] - code - backend/tests/test_evaluation_service.py
- [[mock_pdf_service()]] - code - backend/tests/test_evaluation_service.py
- [[mock_question_service()]] - code - backend/tests/test_evaluation_service.py
- [[mock_result_store()]] - code - backend/tests/test_evaluation_service.py
- [[question_service.py]] - code - backend/services/question_service.py
- [[service()]] - code - backend/tests/test_evaluation_service.py
- [[service()_4]] - code - backend/tests/test_question_service.py
- [[test_evaluation_service.py]] - code - backend/tests/test_evaluation_service.py
- [[test_question_service.py]] - code - backend/tests/test_question_service.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Question_Detection_&_Tests
SORT file.name ASC
```

## Connections to other communities
- 20 edges to [[_COMMUNITY_App Bootstrap & Services]]

## Top bridge nodes
- [[TestDetectQuestions]] - degree 12, connects to 1 community
- [[TestEvaluatePdf]] - degree 9, connects to 1 community
- [[TestAggregation]] - degree 7, connects to 1 community
- [[TestEvaluateImage]] - degree 7, connects to 1 community
- [[TestEvaluateWithQuestionPaper]] - degree 6, connects to 1 community