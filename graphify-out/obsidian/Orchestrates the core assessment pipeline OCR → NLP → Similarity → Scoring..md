---
source_file: "backend/services/assessment_service.py"
type: "rationale"
community: "App Bootstrap & Services"
location: "L1"
tags:
  - graphify/rationale
  - graphify/EXTRACTED
  - community/App_Bootstrap_&_Services
---

# Orchestrates the core assessment pipeline: OCR → NLP → Similarity → Scoring.

## Connections
- [[ResultStorageService]] - `uses` [INFERRED]
- [[assessment_service.py]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/EXTRACTED #community/App_Bootstrap_&_Services