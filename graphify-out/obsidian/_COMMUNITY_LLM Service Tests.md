---
type: community
cohesion: 0.06
members: 36
---

# LLM Service Tests

**Cohesion:** 0.06 - loosely connected
**Members:** 36 nodes

## Members
- [[.__init__()_4]] - code - backend/tests/test_llm_service.py
- [[.monotonic()]] - code - backend/tests/test_llm_service.py
- [[.sleep()]] - code - backend/tests/test_llm_service.py
- [[.test_blocks_uncached_requests_after_daily_limit()]] - code - backend/tests/test_llm_service.py
- [[.test_cache_hit_skips_duplicate_api_call()]] - code - backend/tests/test_llm_service.py
- [[.test_cache_persists_across_service_restarts()]] - code - backend/tests/test_llm_service.py
- [[.test_calls_gemini_api()]] - code - backend/tests/test_llm_service.py
- [[.test_configured_with_key()]] - code - backend/tests/test_llm_service.py
- [[.test_duplicate_prompt_does_not_consume_daily_quota_twice()]] - code - backend/tests/test_llm_service.py
- [[.test_empty_list_returns_empty()]] - code - backend/tests/test_llm_service.py
- [[.test_empty_question_returns_empty()]] - code - backend/tests/test_llm_service.py
- [[.test_enforces_minimum_spacing_between_outbound_requests()]] - code - backend/tests/test_llm_service.py
- [[.test_honors_retry_after_header_when_backing_off()]] - code - backend/tests/test_llm_service.py
- [[.test_non_429_client_errors_do_not_retry()]] - code - backend/tests/test_llm_service.py
- [[.test_not_configured_without_key()]] - code - backend/tests/test_llm_service.py
- [[.test_processes_batch_sequentially()]] - code - backend/tests/test_llm_service.py
- [[.test_queues_requests_in_order()]] - code - backend/tests/test_llm_service.py
- [[.test_retries_429_with_exponential_backoff()]] - code - backend/tests/test_llm_service.py
- [[.test_returns_empty_on_api_failure()]] - code - backend/tests/test_llm_service.py
- [[.test_returns_list()]] - code - backend/tests/test_llm_service.py
- [[.test_returns_string()_1]] - code - backend/tests/test_llm_service.py
- [[.test_stops_after_max_retries_on_429()]] - code - backend/tests/test_llm_service.py
- [[.time()]] - code - backend/tests/test_llm_service.py
- [[Build a Google GenAI client error with optional retry-after header.]] - rationale - backend/tests/test_llm_service.py
- [[Create a mock Google GenAI client.]] - rationale - backend/tests/test_llm_service.py
- [[Deterministic clock for rate-limit and backoff tests.]] - rationale - backend/tests/test_llm_service.py
- [[FakeClock]] - code - backend/tests/test_llm_service.py
- [[TestGenerateBatchAnswers]] - code - backend/tests/test_llm_service.py
- [[TestGenerateModelAnswer]] - code - backend/tests/test_llm_service.py
- [[TestIsConfigured]] - code - backend/tests/test_llm_service.py
- [[Tests for LlmService — LLM model answer generation via Google Gemini.]] - rationale - backend/tests/test_llm_service.py
- [[fake_clock()]] - code - backend/tests/test_llm_service.py
- [[make_client_error()]] - code - backend/tests/test_llm_service.py
- [[mock_genai_client()]] - code - backend/tests/test_llm_service.py
- [[service()_5]] - code - backend/tests/test_llm_service.py
- [[test_llm_service.py]] - code - backend/tests/test_llm_service.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/LLM_Service_Tests
SORT file.name ASC
```

## Connections to other communities
- 8 edges to [[_COMMUNITY_App Bootstrap & Services]]

## Top bridge nodes
- [[TestGenerateModelAnswer]] - degree 16, connects to 1 community
- [[FakeClock]] - degree 8, connects to 1 community
- [[TestGenerateBatchAnswers]] - degree 5, connects to 1 community
- [[TestIsConfigured]] - degree 4, connects to 1 community
- [[Tests for LlmService — LLM model answer generation via Google Gemini.]] - degree 2, connects to 1 community