---
source_file: "backend/services/llm_service.py"
type: "rationale"
community: "Gemini API Coordination"
location: "L23"
tags:
  - graphify/rationale
  - graphify/EXTRACTED
  - community/Gemini_API_Coordination
---

# Generates model answers via Google Gemini.     Degrades gracefully — returns emp

## Connections
- [[GeminiRequestCoordinator]] - `uses` [INFERRED]
- [[LlmService]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/EXTRACTED #community/Gemini_API_Coordination