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
- OCR and NLP preprocessing pipeline for noisy handwritten/scanned answers
- Semantic and lexical similarity scoring
- LLM-backed reference answer generation for document workflows
- Capability-based health reporting instead of a simple up/down status
- **Postgres-backed result storage** with SQLAlchemy 2.0 + Alembic migrations (RAM fallback for local dev)
- **Celery + Redis durable job queue** — async assessment jobs survive worker restart (thread fallback behind `USE_CELERY` flag)
- **Redis pub/sub SSE streaming** — progress events published by workers, subscribed by SSE endpoints
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
- `backend/core`: OCR, NLP preprocessing, similarity, scoring
- `backend/file_handling`: upload validation and temp file cleanup
- `backend/tests`: pytest suite

### Frontend

- `frontend/src/App.tsx`: dashboard shell
- `frontend/src/api`: typed API helpers
- `frontend/src/components`: upload form, health badge, progress, results, history
- `frontend/vite.config.ts`: dev proxy for `/api`

### Core Service Layer

The current graph metadata in `graphify-out/` identifies these as the main backend abstractions:

- `UserService`
- `LlmService`
- `ResultStorageService` — Postgres-backed (RAM fallback when `DATABASE_URL` unset)
- `PdfService`
- `GroqRequestCoordinator` — LLM cache mirrors to `llm_cache` DB table alongside JSON file
- `EvaluationService`
- `QuestionService`
- `ProgressService` — in-memory queue (thread mode) or Redis pub/sub (`USE_CELERY=true`)
- `AssessmentService`

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
4. The system extracts text from images/PDF pages.
5. Questions are detected from the answer content or optional question paper.
6. The LLM generates grounded model answers.
7. Each question response is scored.
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
cp .env.example .env        # set GROQ_API_KEY + JWT_SECRET_KEY
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
│   ├── services/
│   ├── workers/                # Phase 3: Celery
│   │   ├── celery_app.py
│   │   └── tasks.py
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   └── types/
│   └── vite.config.ts
├── uploads/
├── extras/
├── graphify-out/
├── CLAUDE.md
└── README.md
```

## Limitations

- Result history is Postgres-backed when `DATABASE_URL` is set; otherwise in-memory (lost on restart)
- User storage is still in-memory dict — Postgres user table planned for a future phase
- Rate limiter uses in-memory backend — Redis backend planned for a future phase
- Async tasks use Celery when `USE_CELERY=true`; otherwise `threading.Thread` (not restart-safe)
- Document grading quality depends on OCR quality and question extraction accuracy
- LLM-backed workflows depend on configured credentials and quota controls

## Verification Snapshot

- Backend tests: `160 passed, 1 failed (pre-existing), 8 skipped` — no regressions from Phase 2/3
- Frontend lint: passes
- Frontend build: passes
- Graphify graph: 887 nodes, 1253 edges, 126 communities (rebuilt post Phase 2/3)

## Contributor Notes

- `CLAUDE.md` instructs contributors to use `graphify-out/GRAPH_REPORT.md` when answering architecture or codebase questions
- If code is modified, the graph is expected to be rebuilt to keep project structure docs current
- Keep this README aligned with the actual grading modes and capability checks in code
