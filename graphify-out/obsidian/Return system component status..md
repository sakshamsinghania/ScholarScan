---
source_file: "backend/routes/health.py"
type: "rationale"
community: "Health Model"
location: "L14"
tags:
  - graphify/rationale
  - graphify/EXTRACTED
  - community/Health_Model
---

# Return system component status.

## Connections
- [[HealthStatus]] - `uses` [INFERRED]
- [[health_check()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/EXTRACTED #community/Health_Model