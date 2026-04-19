# ScholarScan

ScholarScan is a prototype assessment platform for grading handwritten, scanned, and uploaded student answers. It pairs a Flask backend with a React dashboard and supports both direct teacher-guided grading and a longer async document pipeline for full answer sheets.

The repo currently supports two main workflows:

- `Manual assessment`: upload a single answer image and provide the reference answer yourself.
- `Document assessment`: upload an image or PDF answer sheet, optionally attach a question paper, and let the system extract, generate, score, and stream progress asynchronously.

Manual mode is the safer default for single-image grading. Document mode is stricter: it refuses to grade when it cannot ground reference answers in authoritative question text from the document or an uploaded question paper.

## Highlights

- Flask API for grading, health checks, history, and async task progress
- React + TypeScript dashboard for upload, live progress, results, and history
- OCR and NLP preprocessing pipeline for noisy handwritten/scanned answers
- Semantic and lexical similarity scoring
- LLM-backed reference answer generation for document workflows
- Capability-based health reporting instead of a simple up/down status
- Bounded in-memory result history and task tracking

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

- `backend/app.py`: Flask application factory and service wiring
- `backend/config.py`: environment-driven configuration
- `backend/routes`: API endpoints
- `backend/services`: orchestration, progress tracking, storage, LLM coordination
- `backend/models`: Pydantic response contracts
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

- `LlmService`
- `ResultStorageService`
- `PdfService`
- `GroqRequestCoordinator`
- `EvaluationService`
- `QuestionService`
- `ProgressService`
- `AssessmentService`

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

### `GET /api/health`

Returns overall health plus capability flags such as:

- OCR availability
- semantic similarity availability
- LLM availability
- PDF support
- supported grading modes

### `POST /api/assess`

Main assessment endpoint.

- returns a synchronous result for manual single-image grading
- returns `202 Accepted` with a `task_id` for async document grading

Supported form fields include:

- `answer_file` or `image`
- `question_file`
- `model_answer`
- `question_id`
- `student_id`
- `max_marks`

### `GET /api/progress/stream/<task_id>`

Streams task progress as Server-Sent Events.

### `GET /api/task/<task_id>/result`

Returns the final result when complete, `202` while processing, or `404` if the task does not exist.

### `GET /api/results`

Returns stored history, with optional filters for:

- `student_id`
- `question_id`

## Runtime Notes

- Max upload size: `16 MB`
- Backend local dev default port: `http://localhost:5050`
- `PORT` overrides the backend port
- Allowed file extensions default to `jpg`, `jpeg`, `png`, and `pdf`
- Frontend local dev calls `http://localhost:5050/api` by default on localhost
- Health reporting is capability-based: OCR, semantic similarity, LLM, and PDF support are exposed separately
- In-memory task/result storage is bounded, but it is not durable across restarts

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

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
python3.11 -m pytest tests
python3.11 app.py
```

### Frontend

```bash
cd frontend
npm install
npm run lint
npm run build
npm run dev
```

## Repository Layout

```text
assessment-system/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── core/
│   ├── file_handling/
│   ├── models/
│   ├── routes/
│   ├── services/
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

- Result history is not persisted beyond process lifetime
- Async task tracking is in memory and expires after a TTL
- Production concerns like authentication, durable queues, and persistent storage are not fully implemented
- Document grading quality depends on OCR quality and question extraction accuracy
- LLM-backed workflows depend on configured credentials and quota controls

## Verification Snapshot

The current project documentation records this baseline:

- Backend tests: `115 passed, 8 skipped`
- Frontend lint: passes
- Frontend build: passes

## Contributor Notes

- `CLAUDE.md` instructs contributors to use `graphify-out/GRAPH_REPORT.md` when answering architecture or codebase questions
- If code is modified, the graph is expected to be rebuilt to keep project structure docs current
- Keep this README aligned with the actual grading modes and capability checks in code
