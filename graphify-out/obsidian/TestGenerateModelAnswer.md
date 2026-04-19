---
source_file: "backend/tests/test_llm_service.py"
type: "code"
community: "LLM Service Tests"
location: "L88"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/LLM_Service_Tests
---

# TestGenerateModelAnswer

## Connections
- [[.test_blocks_uncached_requests_after_daily_limit()]] - `method` [EXTRACTED]
- [[.test_cache_hit_skips_duplicate_api_call()]] - `method` [EXTRACTED]
- [[.test_cache_persists_across_service_restarts()]] - `method` [EXTRACTED]
- [[.test_calls_gemini_api()]] - `method` [EXTRACTED]
- [[.test_duplicate_prompt_does_not_consume_daily_quota_twice()]] - `method` [EXTRACTED]
- [[.test_empty_question_returns_empty()]] - `method` [EXTRACTED]
- [[.test_enforces_minimum_spacing_between_outbound_requests()]] - `method` [EXTRACTED]
- [[.test_honors_retry_after_header_when_backing_off()]] - `method` [EXTRACTED]
- [[.test_non_429_client_errors_do_not_retry()]] - `method` [EXTRACTED]
- [[.test_queues_requests_in_order()]] - `method` [EXTRACTED]
- [[.test_retries_429_with_exponential_backoff()]] - `method` [EXTRACTED]
- [[.test_returns_empty_on_api_failure()]] - `method` [EXTRACTED]
- [[.test_returns_string()_1]] - `method` [EXTRACTED]
- [[.test_stops_after_max_retries_on_429()]] - `method` [EXTRACTED]
- [[LlmService]] - `uses` [INFERRED]
- [[test_llm_service.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/LLM_Service_Tests