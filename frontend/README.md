# ScholarScan Frontend

React 19 + Vite dashboard for submitting assessments, watching async grading progress, checking backend capabilities, and reviewing result history.

## Commands

```bash
npm install
npm run dev
npm run lint
npm run build
```

## Dev API Wiring

- On localhost, the app talks directly to `http://localhost:5050/api` by default
- `vite.config.ts` keeps `/api` proxied to the same backend port as a fallback for local tooling
- Override with `VITE_API_BASE_URL` when you want a full custom API URL, or `VITE_API_PORT` when you only need a different local backend port

## UI Behavior

- Manual mode is the default for image uploads and requires a teacher-provided model answer
- Question-paper uploads are only available in auto/document mode
- History renders separate single-question and multi-question summaries
- Health status exposes OCR, semantic, LLM, and PDF capability chips instead of a single coarse badge
