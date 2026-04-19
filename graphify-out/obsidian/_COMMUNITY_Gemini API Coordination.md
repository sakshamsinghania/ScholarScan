---
type: community
cohesion: 0.09
members: 34
---

# Gemini API Coordination

**Cohesion:** 0.09 - loosely connected
**Members:** 34 nodes

## Members
- [[.__init__()_5]] - code - backend/services/gemini_request_coordinator.py
- [[._build_cache_key()]] - code - backend/services/llm_service.py
- [[._compute_retry_delay()]] - code - backend/services/gemini_request_coordinator.py
- [[._get_cached_response_locked()]] - code - backend/services/gemini_request_coordinator.py
- [[._load_state()]] - code - backend/services/gemini_request_coordinator.py
- [[._persist_state_locked()]] - code - backend/services/gemini_request_coordinator.py
- [[._process_request()]] - code - backend/services/gemini_request_coordinator.py
- [[._prune_request_timestamps_locked()]] - code - backend/services/gemini_request_coordinator.py
- [[._request_model_answer()]] - code - backend/services/llm_service.py
- [[._reserve_request_slot()]] - code - backend/services/gemini_request_coordinator.py
- [[._run_worker()]] - code - backend/services/gemini_request_coordinator.py
- [[.close()]] - code - backend/services/gemini_request_coordinator.py
- [[.generate_batch_answers()]] - code - backend/services/llm_service.py
- [[.generate_model_answer()]] - code - backend/services/llm_service.py
- [[.get_cached_response()]] - code - backend/services/gemini_request_coordinator.py
- [[.submit()]] - code - backend/services/gemini_request_coordinator.py
- [[Check if the LLM service has a valid API key.]] - rationale - backend/services/llm_service.py
- [[GeminiRequestCoordinator]] - code - backend/services/gemini_request_coordinator.py
- [[Generate a concise model answer for a single question.          Returns empty st]] - rationale - backend/services/llm_service.py
- [[Generate model answers for multiple questions using serialized calls.]] - rationale - backend/services/llm_service.py
- [[Generate model answers using Google Gemini LLM API.]] - rationale - backend/services/llm_service.py
- [[Generates model answers via Google Gemini.     Degrades gracefully — returns emp]] - rationale - backend/services/llm_service.py
- [[Internal representation of one queued Gemini request.]] - rationale - backend/services/gemini_request_coordinator.py
- [[Queue a Gemini request or join an identical in-flight request.]] - rationale - backend/services/gemini_request_coordinator.py
- [[Queue, throttle, retry, and cache Gemini API requests.]] - rationale - backend/services/gemini_request_coordinator.py
- [[Return a cached response immediately, if available.]] - rationale - backend/services/gemini_request_coordinator.py
- [[Serialize Gemini requests with disk-backed cache and quota tracking.]] - rationale - backend/services/gemini_request_coordinator.py
- [[Stop the worker thread.]] - rationale - backend/services/gemini_request_coordinator.py
- [[_QueuedRequest]] - code - backend/services/gemini_request_coordinator.py
- [[_normalize_question()]] - code - backend/services/llm_service.py
- [[_parse_retry_after()]] - code - backend/services/gemini_request_coordinator.py
- [[gemini_request_coordinator.py]] - code - backend/services/gemini_request_coordinator.py
- [[is_configured()]] - code - backend/services/llm_service.py
- [[llm_service.py]] - code - backend/services/llm_service.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Gemini_API_Coordination
SORT file.name ASC
```

## Connections to other communities
- 8 edges to [[_COMMUNITY_App Bootstrap & Services]]

## Top bridge nodes
- [[GeminiRequestCoordinator]] - degree 21, connects to 1 community
- [[.generate_model_answer()]] - degree 5, connects to 1 community
- [[llm_service.py]] - degree 4, connects to 1 community
- [[._build_cache_key()]] - degree 3, connects to 1 community
- [[.generate_batch_answers()]] - degree 3, connects to 1 community