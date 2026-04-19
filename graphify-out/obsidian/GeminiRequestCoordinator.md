---
source_file: "backend/services/gemini_request_coordinator.py"
type: "code"
community: "Gemini API Coordination"
location: "L33"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Gemini_API_Coordination
---

# GeminiRequestCoordinator

## Connections
- [[.__init__()_5]] - `method` [EXTRACTED]
- [[._compute_retry_delay()]] - `method` [EXTRACTED]
- [[._get_cached_response_locked()]] - `method` [EXTRACTED]
- [[._load_state()]] - `method` [EXTRACTED]
- [[._persist_state_locked()]] - `method` [EXTRACTED]
- [[._process_request()]] - `method` [EXTRACTED]
- [[._prune_request_timestamps_locked()]] - `method` [EXTRACTED]
- [[._reserve_request_slot()]] - `method` [EXTRACTED]
- [[._run_worker()]] - `method` [EXTRACTED]
- [[.close()]] - `method` [EXTRACTED]
- [[.get_cached_response()]] - `method` [EXTRACTED]
- [[.submit()]] - `method` [EXTRACTED]
- [[Check if the LLM service has a valid API key.]] - `uses` [INFERRED]
- [[Generate a concise model answer for a single question.          Returns empty st]] - `uses` [INFERRED]
- [[Generate model answers for multiple questions using serialized calls.]] - `uses` [INFERRED]
- [[Generate model answers using Google Gemini LLM API.]] - `uses` [INFERRED]
- [[Generates model answers via Google Gemini.     Degrades gracefully — returns emp]] - `uses` [INFERRED]
- [[LlmService]] - `uses` [INFERRED]
- [[Release background resources owned by the service.]] - `uses` [INFERRED]
- [[Serialize Gemini requests with disk-backed cache and quota tracking.]] - `rationale_for` [EXTRACTED]
- [[gemini_request_coordinator.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Gemini_API_Coordination