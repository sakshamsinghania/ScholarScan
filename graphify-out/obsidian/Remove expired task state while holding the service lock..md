---
source_file: "backend/services/progress_service.py"
type: "rationale"
community: "Progress Service Core"
location: "L181"
tags:
  - graphify/rationale
  - graphify/EXTRACTED
  - community/Progress_Service_Core
---

# Remove expired task state while holding the service lock.

## Connections
- [[._evict_expired_locked()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/EXTRACTED #community/Progress_Service_Core