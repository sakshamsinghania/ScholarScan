# ScholarScan

ScholarScan is a prototype assessment platform for grading handwritten, scanned, and uploaded student answers. It pairs a Flask backend with a React dashboard and supports both direct teacher-guided grading and a longer async document pipeline for full answer sheets.

The repo currently supports two main workflows:

- `Manual assessment`: upload a single answer image and provide the reference answer yourself.
- `Document assessment`: upload an image or PDF answer sheet, optionally attach a question paper, and let the system extract, generate, score, and stream progress asynchronously.

Manual mode is the safer default for single-image grading. Document mode is stricter: it refuses to grade when it cannot ground reference answers in authoritative question text from the document or an uploaded question paper.

## Highlights

- Flask API for grading, health checks, history, and async task progress
- JWT authentication with role-based access and row-level authorization
- Rate limiting on sensitive endpoints (login, assessment)
- React + TypeScript dashboard for upload, live progress, results, and history
- **Frontend auth UI** — login/register gate, JWT token lifecycle with silent refresh, localStorage persistence
- **Authenticated API client** — auto-attached Bearer tokens, 401 refresh-and-retry, 403/429 error surfacing
- **Fetch-based SSE** — authenticated progress streaming (no EventSource header limitation), heartbeat + reconnect
- **Failure surfacing** — failed assessments shown in history with filter chips (All/Completed/Failed)
- **Toast system + rate-limit UX** — rate-limit countdown on submit button, role badge, admin tab placeholder
- **Post-OCR pipeline** — markdown-aware `QaExtractor` with 5-pattern question detection, P5 disambiguation (monotonic guard + Ans-prefix + question-stem), sequential ID relabeling, multi-page answer spans, and `preprocess_markdown_for_sbert` that preserves case/math/structure
- OCR and NLP preprocessing pipeline for noisy handwritten/scanned answers
- **Hybrid keyword scoring** — noun-chunk phrase extraction (spaCy), fuzzy OCR correction (rapidfuzz `token_set_ratio ≥ 85`), semantic synonym matching (SBERT cosine `≥ 0.70`), TF-IDF importance weighting per phrase; batch-encoded in one SBERT call
- **V2 scoring formula** — 5-component weighted scoring (SBERT 0.35, sentence similarity 0.25, concept coverage 0.25, TF-IDF 0.10, NLI 0.05) with graceful weight redistribution when components are unavailable; feature-flagged via `SCORING_V2_ENABLED`
- **Sentence-level similarity** — `SentenceSimilarityScorer` with mean-of-max recall aggregation over model sentences; `split_sentences` uses spaCy `sents` with regex fallback
- **Concept coverage** — `ConceptCoverageScorer` wraps keyword overlap with rich `MatchedConcept`/`MissingConcept` dataclasses tracking match type, similarity, and nearest candidates
- **Clean concept feedback** — output-layer phrase cleaning (dedup, length cap, generic-word filter, SBERT semantic dedup) produces readable "You covered / You missed" feedback instead of raw bag-of-words
- **Optional NLI entailment** — `NLIScorer` with lazy-loaded cross-encoder (`nli-deberta-v3-base`), top-K sentence pair selection, timeout guard, and config-gated activation
- LLM-backed reference answer generation for document workflows
- Capability-based health reporting instead of a simple up/down status
- **Postgres-backed result storage** with SQLAlchemy 2.0 + Alembic migrations (RAM fallback for local dev)
- **Celery + Redis durable job queue** — async assessment jobs survive worker restart (thread fallback behind `USE_CELERY` flag)
- **Redis pub/sub SSE streaming** — progress events published by workers, subscribed by SSE endpoints
- **OCR cascade** — pluggable provider chain (Mistral OCR → Google Vision → Tesseract) with per-provider retry, real confidence scores from `average_page_confidence_score`, and total timeout cap
- Pre-commit hooks (ruff, black, mypy, bandit) and GitHub Actions CI
- Full Docker Compose stack: web, Celery worker, Flower, Postgres, Redis

## Assessment Modes

### Manual Image Assessment

Use this when a teacher already knows the correct answer and wants a quick score for one uploaded answer image.

- Requires `model_answer`
- Supports image uploads only
- Returns synchronously
- Best suited for single-question grading

### Document Assessment

Use this when grading a full answer sheet or multi-question submission.

- Accepts image or PDF uploads as `answer_file`
- Optionally accepts a `question_file`
- Runs asynchronously in a background thread
- Returns a `task_id`
- Streams progress with Server-Sent Events
- Exposes a final task result endpoint once scoring completes

## Architecture

### Backend

- `backend/app.py`: Flask application factory, service wiring, auth and rate limiter init
- `backend/config.py`: environment-driven configuration
- `backend/routes`: API endpoints (auth, assess, health, progress, results, task_result)
- `backend/services`: orchestration, progress tracking, storage, LLM coordination, user management
- `backend/models`: Pydantic response contracts (assessment, health, user)
- `backend/core`: OCR, NLP preprocessing, similarity (hybrid keyword matching), scoring
- `backend/file_handling`: upload validation and temp file cleanup
- `backend/tests`: pytest suite

### Frontend

- `frontend/src/App.tsx`: dashboard shell with auth gate, task restoration
- `frontend/src/main.tsx`: mounts `AuthProvider` above `App`
- `frontend/src/auth/`: `AuthContext`, `useAuth` hook, `tokenStorage` (localStorage JWT persistence)
- `frontend/src/api/`: typed API helpers (`assessment-api`, `auth-api`, `sse` fetch-based SSE reader)
- `frontend/src/components/`: upload form, health badge, progress tracker, results, history, auth card
- `frontend/src/components/auth/`: `LoginForm`, `RegisterForm`, `AuthCard` (login/register gate)
- `frontend/src/hooks/`: `useToast` (lightweight toast system)
- `frontend/src/types/`: TypeScript interfaces for assessment, auth, progress
- `frontend/vite.config.ts`: dev proxy for `/api`

### Core Service Layer

The current graph metadata in `graphify-out/` identifies these as the main backend abstractions:

- `UserService`
- `LlmService`
- `ResultStorageService` — Postgres-backed (RAM fallback when `DATABASE_URL` unset)
- `PdfService` — pdfplumber + native Mistral PDF ingestion with `extract_result()` returning page-aware `OcrResult`
- `GroqRequestCoordinator` — LLM cache mirrors to `llm_cache` DB table alongside JSON file
- `EvaluationService` — rewired to use `QaExtractor` + page-aware `OcrResult` instead of flat text
- `QaExtractor` — markdown-aware Q&A segment extraction with sequential ID relabeling (replaces `QuestionService`)
- `ProgressService` — in-memory queue (thread mode) or Redis pub/sub (`USE_CELERY=true`)
- `AssessmentService` — provider-aware SBERT preprocessing (markdown-aware for Mistral, legacy for Vision/Tesseract)

### Keyword Scoring Pipeline

`backend/core/similarity.py` — `TFIDFSimilarity.keyword_overlap()` uses a three-stage hybrid system:

1. **Phrase extraction** (`extract_phrases`) — spaCy noun chunks preserve multi-word concepts (`"custom resource definition"` as one unit); falls back to lemmatized tokens if spaCy unavailable
2. **TF-IDF weighting** (`_compute_phrase_weights`) — each model phrase gets an importance weight `[0.3, 1.0]` derived from the fitted vectorizer; out-of-vocab phrases receive a 0.3 floor rather than zero
3. **Hybrid match** (`hybrid_match` / `keyword_score`) — per model phrase: fuzzy first (`token_set_ratio ≥ 85`, catches OCR noise like `"vales.yaml"`), then SBERT cosine on a pre-computed `[M × S]` batch matrix (`≥ 0.70`, catches synonyms like `"configurable" ≈ "overridable"`); all phrases encoded in one SBERT call

### NLP Scoring V2 (Phase 10)

The V2 scoring formula replaces the simple `0.3·TF-IDF + 0.7·SBERT` with a 5-component weighted formula gated by `SCORING_V2_ENABLED`:

| Component | Weight | Class | Description |
| --- | --- | --- | --- |
| SBERT (doc-level) | 0.35 | `SBERTSimilarity` | Full-document semantic similarity |
| Sentence similarity | 0.25 | `SentenceSimilarityScorer` | Mean-of-max recall over model sentences |
| Concept coverage | 0.25 | `ConceptCoverageScorer` | Rich phrase-level matching with match type (exact/fuzzy/semantic) |
| TF-IDF | 0.10 | `TFIDFSimilarity` | Lexical surface overlap |
| Entailment (NLI) | 0.05 | `NLIScorer` | Cross-encoder entailment scoring (optional, off by default) |

Key features:
- **Graceful weight redistribution** — if a component is unavailable (SBERT missing, NLI disabled), its weight redistributes proportionally across remaining components
- **Sentence-level scoring** — `split_sentences()` in `nlp.py` uses spaCy `sents` with regex fallback; `SentenceSimilarityScorer` computes `[M × S]` cosine matrix and aggregates via mean-of-max (recall-oriented)
- **Concept coverage** — `ConceptCoverageScorer` wraps keyword_overlap with rich `MatchedConcept`/`MissingConcept` dataclasses tracking match type, similarity, and nearest candidates
- **Clean concept output** — output-layer phrase cleaning pipeline (`clean_phrase` → `is_valid_phrase` → `dedupe_phrases`) ensures readable feedback: deduplicates words within phrases, caps at 5 words, rejects generic-only phrases, and removes semantically redundant concepts via SBERT cosine (>0.85) or substring dedup
- **Structured feedback** — `feedback` key in scoring result provides top-5 covered/missing concepts with a human-readable summary ("You covered: X, Y. You missed: A, B.")
- **NLI entailment** — optional `NLIScorer` loads `cross-encoder/nli-deberta-v3-base` via lazy singleton; selects top-K sentence pairs by cosine, scores via softmax(logits), aggregates with relevance weighting
- **Tiered reference scoring** — `LlmService.generate_tiered_model_answer()` produces structured JSON with `core`/`supporting`/`extended` concept tiers; `ConceptCoverageScorer` uses tier-aware scoring where core concepts drive the denominator and supporting concepts provide bonus credit (capped at `SUPPORTING_BONUS_CAP`); missing core concepts appear as "Missing (required)", missing supporting as "Could strengthen with"; feature-flagged via `TIERED_REFERENCE_ENABLED`
- **EmbeddingContext** — per-call cache sharing phrase and sentence embeddings across scorers
- **Debug mode** — `debug=True` on `compute_similarity` attaches per-component matrices, timings, and weight details
- All legacy keys (`tfidf_score`, `sbert_score`, `combined_score`, `keyword_overlap`, `missing_keywords`) preserved; new keys (`concept_coverage`, `matched_concepts`, `missing_concepts`, `sentence_similarity`, `entailment_score`, `component_weights`, `feedback`) added alongside

### Persistence Layer (Phase 2)

- `backend/db/session.py` — SQLAlchemy engine + context-manager session factory
- `backend/db/models.py` — ORM models: `Assessment`, `QuestionResult`, `LlmCache`, `ProgressEvent`
- `backend/repositories/` — `assessment_repository`, `llm_cache_repository`
- `backend/migrations/` — Alembic env + initial migration (`0001_initial_schema`)
- Activated by `DATABASE_URL` env var; unset → RAM fallback (tests unaffected)

### Job Queue (Phase 3)

- `backend/workers/celery_app.py` — Celery app with Flask `ContextTask`
- `backend/workers/tasks.py:evaluate_assessment` — durable Celery task replacing `threading.Thread`
- Activated by `USE_CELERY=true`; default `false` keeps existing thread path
- Progress published to Redis channel `progress:{task_id}`; SSE route subscribes

### OCR Cascade (Phase 8)

- `backend/adapters/ocr/base.py` — `OcrProvider` Protocol + `OcrResult`/`OcrPage` dataclasses + shared preprocessing
- `backend/adapters/ocr/mistral_ocr.py` — Mistral OCR primary (`mistral-ocr-latest`); base64 data-URI upload, real `average_page_confidence_score` from API, per-page markdown in `OcrResult.page_data`
- `backend/adapters/ocr/google_vision.py` — Google Cloud Vision `DOCUMENT_TEXT_DETECTION` fallback
- `backend/adapters/ocr/tesseract.py` — local offline last-resort fallback
- `backend/services/ocr_service.py` — cascade orchestrator with tenacity retry + confidence short-circuit
- `backend/scripts/bench_ocr.py` — benchmark harness (CER/WER table against fixture ground-truth)
- Provider chain controlled by `OCR_CASCADE` env var; per-provider timeout 60s + total 120s cap

### Post-OCR Pipeline (Phase 9)

- `backend/core/markdown_parser.py` — parses Mistral OCR markdown into typed `Block` stream (`BlockKind`: heading, bold, numbered, paragraph, table, math, code, blank)
- `backend/services/qa_extractor.py` — `QaExtractor` replaces `QuestionService`; detects questions via 5-pattern hierarchy (P1–P5) with P5 disambiguation (monotonic guard, Ans-prefix lookahead, question-stem check); assigns sequential IDs (`Q1`, `Q2`, …) regardless of student labeling; extracts multi-page answer spans with markdown fidelity
- `backend/core/nlp.py` — added `preprocess_markdown_for_sbert()` that preserves case, math symbols, and structure (unlike the legacy `preprocess_for_sbert` which lowercases and strips special chars)
- `backend/services/pdf_service.py` — `extract_result()` routes PDFs through Mistral OCR natively when available, falls back to pdfplumber+OCR-per-page
- Golden test fixture: `backend/tests/fixtures/zeeya_extracted.md` — 5-page handwritten OCR output, 7 questions with mislabeled numbers and inline numbered lists

### Tiered Reference Scoring (Phase 11)

- `backend/core/similarity.py` — `TieredReference` dataclass, tier-aware `ConceptCoverageScorer.score()` with `core_recall` + `supporting_bonus` formula
- `backend/services/llm_service.py` — `generate_tiered_model_answer()` with JSON-mode prompt, fenced-code stripping, retry-with-repair, and legacy fallback
- `backend/services/evaluation_service.py` — tiered generation behind `TIERED_REFERENCE_ENABLED` flag, tier snapshot in `per_question_results`
- `backend/services/assessment_service.py` — `tiered_reference` param forwarded to `compute_similarity`
- Scoring formula: `coverage = min(1.0, core_recall + BONUS_CAP × supporting_bonus)` — full marks possible from core alone; supporting only lifts partial scores
- Missing core concepts → "Missing (required)"; missing supporting → "Could strengthen with"
- Feature-flagged: `TIERED_REFERENCE_ENABLED=false` default; legacy path fully preserved

### Authentication & Authorization

All data routes require a valid JWT access token (`Authorization: Bearer <token>`). The health endpoint remains public.

- **Register** → `POST /api/auth/register` — creates a user, returns access + refresh tokens.
- **Login** → `POST /api/auth/login` — validates credentials, returns tokens. Rate-limited to 10/minute.
- **Refresh** → `POST /api/auth/refresh` — exchanges a refresh token for a new access token.
- **Row-level access** — each task and stored result is tagged with the creating user's ID. Users can only view their own tasks, progress streams, and result history. Unauthorized cross-user access returns `403`.
- **Feature flag** — set `AUTH_REQUIRED=false` to disable auth entirely for local development.

## How the Pipeline Works

### Manual flow

1. Upload a single image.
2. Provide the model answer.
3. Backend validates the file and runs OCR.
4. NLP preprocessing normalizes extracted text.
5. Similarity scoring combines lexical and semantic signals.
6. A score, marks, grade, and feedback payload is returned immediately.

### Document flow

1. Upload an answer sheet image or PDF.
2. Backend stores the upload and creates an async task.
3. Progress updates are emitted during processing.
4. The system extracts a page-aware `OcrResult` from images/PDF pages (Mistral OCR natively ingests PDFs).
5. `QaExtractor` parses OCR markdown into sequential Q&A segments with disambiguation rules.
6. The LLM generates grounded model answers.
7. Each question response is scored with provider-aware SBERT preprocessing.
8. The final aggregated result is stored and made available by task ID.

## API Summary

### `POST /api/auth/register`

Create a new user account. Returns user info, access token, and refresh token.

### `POST /api/auth/login`

Authenticate with email and password. Returns tokens. Rate-limited to 10 requests/minute per IP.

### `POST /api/auth/refresh`

Exchange a refresh token for a new access token.

### `GET /api/health`

Returns overall health plus capability flags such as:

- OCR availability
- semantic similarity availability
- LLM availability
- PDF support
- supported grading modes

No authentication required.

### `POST /api/assess`

Main assessment endpoint. **Requires JWT.**

- returns a synchronous result for manual single-image grading
- returns `202 Accepted` with a `task_id` for async document grading
- rate-limited to 30 requests/hour per user

Supported form fields include:

- `answer_file` or `image`
- `question_file`
- `model_answer`
- `question_id`
- `student_id`
- `max_marks`

### `GET /api/progress/stream/<task_id>`

Streams task progress as Server-Sent Events. **Requires JWT.** Only the task owner can access the stream.

### `GET /api/task/<task_id>/result`

Returns the final result when complete, `202` while processing, or `404` if the task does not exist. **Requires JWT.** Owner-gated.

### `GET /api/results`

Returns stored history, with optional filters for:

- `student_id`
- `question_id`

**Requires JWT.** Returns only the authenticated user's results.

## Runtime Notes

- Max upload size: `16 MB`
- Backend local dev default port: `http://localhost:5050`
- `PORT` overrides the backend port
- Allowed file extensions default to `jpg`, `jpeg`, `png`, and `pdf`
- Frontend local dev calls `http://localhost:5050/api` by default on localhost
- Health reporting is capability-based: OCR, semantic similarity, LLM, and PDF support are exposed separately
- In-memory task/result storage is bounded, but it is not durable across restarts
- Authentication is enabled by default; set `AUTH_REQUIRED=false` to disable for local development
- Login is rate-limited to 10 requests/minute; assessment to 30/hour per user

## Quick Start

### Full stack (Docker Compose — Phase 2 + 3)

```bash
cp .env.example .env        # set GROQ_API_KEY + JWT_SECRET_KEY + MISTRAL_API_KEY
docker compose up --build
# Web:    http://localhost:5050
# Flower: http://localhost:5555
```

### Backend (local dev — RAM mode, no DB/Redis required)

```bash
cd backend
pip install -r requirements.txt
python3.11 -m pytest tests
AUTH_REQUIRED=false python3.11 app.py
```

### Backend with Postgres + Celery (local)

```bash
export DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/scholarscan
export REDIS_URL=redis://localhost:6379/0
export USE_CELERY=true
cd backend && alembic upgrade head
python3.11 app.py &
celery -A workers.celery_app.celery worker --loglevel=info
```

### Frontend

```bash
cd frontend
npm install && npm run dev
```

---

## Configuration

The backend loads environment variables from `.env` when available.

### Core settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode |
| `UPLOAD_FOLDER` | `uploads` | Temporary upload and cache directory |
| `MAX_CONTENT_LENGTH` | `16777216` | Maximum upload size in bytes |
| `RESULT_STORE_MAX_ENTRIES` | `500` | In-memory history cap |
| `TASK_TTL_SECONDS` | `3600` | Task progress/result retention |
| `ALLOWED_EXTENSIONS` | `jpg,jpeg,png,pdf` | Allowed file types |
| `PORT` | `5050` fallback | Runtime backend port |
| `CORS_ORIGIN` | localhost defaults | Allowed frontend origins |

### Model and LLM settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `SBERT_MODEL_NAME` | `all-MiniLM-L6-v2` | Sentence Transformer model |
| `GROQ_API_KEY` | empty | Groq API key |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` | Groq base URL |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | Reference answer generation model |
| `LLM_MIN_INTERVAL_SECONDS` | `2` | Minimum delay between LLM calls |
| `LLM_DAILY_REQUEST_LIMIT` | `14000` | Daily quota safeguard |
| `LLM_MAX_RETRIES` | `5` | Retry limit |
| `LLM_BACKOFF_BASE_SECONDS` | `2` | Retry backoff floor |
| `LLM_BACKOFF_MAX_SECONDS` | `60` | Retry backoff ceiling |
| `LLM_CACHE_PATH` | `uploads/groq-cache.json` | Disk-backed LLM cache |

### Auth and rate limiting

| Variable | Default | Purpose |
| --- | --- | --- |
| `JWT_SECRET_KEY` | random (dev only) | HMAC signing key for JWTs — **must be set in production** |
| `JWT_ACCESS_TOKEN_EXPIRES` | `3600` | Access token TTL in seconds |
| `JWT_REFRESH_TOKEN_EXPIRES` | `2592000` | Refresh token TTL in seconds (30 days) |
| `AUTH_REQUIRED` | `true` | Enable JWT auth on data routes; set `false` for local dev |
| `RATE_LIMIT_ASSESS` | `30/hour` | Per-user assessment rate limit |
| `RATE_LIMIT_LOGIN` | `10/minute` | Per-IP login rate limit |
| `RATE_LIMIT_GLOBAL` | `300/hour` | Global per-IP rate limit |

### Persistence and job queue (Phase 2 + 3)

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | empty | SQLAlchemy DB URL. Unset → in-memory fallback. Example: `postgresql+psycopg://user:pass@localhost:5432/scholarscan` |
| `USE_CELERY` | `false` | Route async jobs through Celery. `false` → threading fallback |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker + progress pub/sub channel |

### OCR cascade (Phase 8)

| Variable | Default | Purpose |
| --- | --- | --- |
| `OCR_CASCADE` | `mistral,vision,tesseract` | Comma-separated provider chain order |
| `MISTRAL_API_KEY` | empty | API key for Mistral OCR (platform.mistral.ai) |
| `MISTRAL_OCR_MODEL` | `mistral-ocr-latest` | Mistral OCR model identifier |
| `GOOGLE_VISION_API_KEY` | empty | API key for Google Vision OCR |
| `GOOGLE_APPLICATION_CREDENTIALS` | empty | Optional service account JSON fallback for Google Vision |
| `OCR_PROVIDER_TIMEOUT_SECONDS` | `60` | Per-provider wall-clock timeout |
| `OCR_TOTAL_TIMEOUT_SECONDS` | `120` | Total cascade timeout |
| `OCR_RETRIES_PER_PROVIDER` | `2` | Retry attempts per provider (exponential backoff) |

### NLP scoring V2 (Phase 10)

| Variable | Default | Purpose |
| --- | --- | --- |
| `SCORING_V2_ENABLED` | `true` | Enable 5-component scoring formula; `false` → legacy 0.3·TF-IDF + 0.7·SBERT |
| `SENTENCE_SIM_ENABLED` | `true` | Enable sentence-level similarity scorer |
| `NLI_ENABLED` | `false` | Enable entailment (NLI) scoring — requires `transformers` + `torch` |
| `NLI_MODEL_NAME` | `cross-encoder/nli-deberta-v3-base` | NLI cross-encoder model |
| `NLI_TOP_N` | `16` | Max sentence pairs for NLI scoring |
| `NLI_TIMEOUT_MS` | `4000` | NLI forward-pass timeout in milliseconds |
| `SCORE_WEIGHT_SBERT` | `0.35` | V2 weight for doc-level SBERT |
| `SCORE_WEIGHT_SENTENCE` | `0.25` | V2 weight for sentence-level similarity |
| `SCORE_WEIGHT_CONCEPT` | `0.25` | V2 weight for concept coverage |
| `SCORE_WEIGHT_TFIDF` | `0.10` | V2 weight for TF-IDF |
| `SCORE_WEIGHT_NLI` | `0.05` | V2 weight for NLI entailment |

### Tiered reference scoring (Phase 11)

| Variable | Default | Purpose |
| --- | --- | --- |
| `TIERED_REFERENCE_ENABLED` | `false` | Enable tiered reference answer generation; `false` → legacy flat model answer |
| `SUPPORTING_BONUS_CAP` | `0.15` | Maximum bonus from supporting concepts (added to core recall) |
| `TIERED_LLM_MAX_RETRIES` | `2` | Retry attempts for tiered JSON parse failures before falling back to legacy |

### Frontend env vars

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `/api` (prod) / `localhost:5050/api` (dev) | Backend API base URL |
| `VITE_AUTH_REQUIRED` | `true` | Set `false` when backend `AUTH_REQUIRED=false` to skip auth gate |
| `VITE_REFRESH_LEEWAY_SEC` | `60` | Refresh access token this many seconds before expiry |


## Repository Layout

```text
assessment-system/
├── .github/workflows/ci.yml
├── .pre-commit-config.yaml
├── Dockerfile                  # web (multi-stage)
├── Dockerfile.worker           # Celery worker
├── docker-compose.yml          # full stack: web, worker, flower, postgres, redis
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── alembic.ini
│   ├── adapters/                # Phase 8: OCR provider adapters
│   │   └── ocr/
│   │       ├── base.py          # OcrProvider Protocol + OcrResult + preprocessing
│   │       ├── mistral_ocr.py   # Mistral OCR primary (mistral-ocr-latest)
│   │       ├── google_vision.py # Google Cloud Vision fallback
│   │       └── tesseract.py     # offline last-resort fallback
│   ├── core/
│   ├── db/                     # Phase 2: SQLAlchemy engine + ORM models
│   │   ├── session.py
│   │   └── models.py
│   ├── file_handling/
│   ├── migrations/             # Phase 2: Alembic migrations
│   │   ├── env.py
│   │   └── versions/0001_initial_schema.py
│   ├── models/
│   ├── repositories/           # Phase 2: DB access layer
│   │   ├── assessment_repository.py
│   │   └── llm_cache_repository.py
│   ├── routes/
│   ├── scripts/                # Phase 8: bench_ocr.py benchmark harness
│   ├── services/
│   ├── workers/                # Phase 3: Celery
│   │   ├── celery_app.py
│   │   └── tasks.py
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── api/              # assessment-api, auth-api, sse
│   │   ├── auth/             # AuthContext, useAuth, tokenStorage
│   │   ├── components/
│   │   │   ├── auth/         # LoginForm, RegisterForm, AuthCard
│   │   │   ├── ToastHost.tsx
│   │   │   └── ...           # AssessmentForm, HealthBadge, etc.
│   │   ├── hooks/            # useToast
│   │   └── types/            # assessment.ts, auth.ts
│   └── vite.config.ts
├── uploads/
└── README.md
```

## Limitations

- Result history is Postgres-backed when `DATABASE_URL` is set; otherwise in-memory (lost on restart)
- User storage is still in-memory dict — Postgres user table planned for a future phase
- Rate limiter uses in-memory backend — Redis backend planned for a future phase
- Async tasks use Celery when `USE_CELERY=true`; otherwise `threading.Thread` (not restart-safe)
- Document grading quality depends on OCR quality and question extraction accuracy
- LLM-backed workflows depend on configured credentials and quota controls
- Tokens stored in `localStorage` are XSS-readable; `httpOnly` cookie path planned for a future phase

## Verification Snapshot

- Backend tests: `238 passed` — includes markdown_parser, qa_extractor, zeeya golden, evaluation service/progress, full similarity + scoring suite, concept coverage, sentence similarity, NLI, compute_similarity contract
- Frontend lint: passes (post frontend F1–F5)
- Frontend build: passes (post frontend F1–F5)
- Frontend new files: 10 (auth, toast, SSE modules + auth UI components)
- OCR cascade: 3 providers (mistral, vision, tesseract) with tenacity retry + real API confidence scores + short-circuit
- Post-OCR pipeline: QaExtractor passes 17/17 golden assertions against zeeya_extracted.md (7 questions, mislabeled numbers, inline lists rejected)
- Hybrid keyword scoring: phrase extraction + fuzzy OCR correction + semantic synonym matching
- NLP V2 scoring: ConceptCoverageScorer, SentenceSimilarityScorer, NLIScorer, 5-component weighted formula with redistribution; 4 new test files (concept, sentence, NLI, contract) all passing
- Tiered reference scoring: TieredReference dataclass, tier-aware ConceptCoverageScorer, LLM tiered generation with JSON parse + fallback, pipeline plumbing through EvaluationService → AssessmentService → compute_similarity; 3 new test files (llm_tiered, concept_coverage_tiered, tiered_calibration) all passing
