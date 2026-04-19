# Frontend Review Findings

## Finding 1

**File:** `frontend/src/App.tsx:114`  
**Severity:** P0  
**Title:** Results history can never appear

`historyEmpty` starts as `true`, and `ResultsHistory` is only rendered when it is already `false`. Because the only code that can flip that flag lives inside `ResultsHistory`, the history panel is permanently unreachable, even after a successful assessment.

## Finding 2

**File:** `frontend/src/components/ProgressTracker.tsx:72-75`  
**Severity:** P1  
**Title:** Progress stream treats disconnects as completion fallback

Any `EventSource` error closes the stream and immediately starts result polling. A transient SSE disconnect or a task that legitimately runs longer than the 10 polling attempts will be surfaced as a frontend failure, even though the backend task may still be healthy.

## Finding 3

**File:** `frontend/src/api/assessment-api.ts:40-45`  
**Severity:** P1  
**Title:** API helpers ignore non-OK responses

`getResults()` and `getHealth()` return `res.json()` without checking `res.ok`, and `assess()` assumes error bodies are always JSON. That makes 4xx/5xx responses show up as parsing failures or false success states instead of controlled UI errors.

## Finding 4

**File:** `frontend/src/api/assessment-api.ts:23-27`  
**Severity:** P1  
**Title:** Manual mode conflicts with PDF uploads

The form allows PDF uploads while manual mode sends the file under the legacy `image` field. Unless the backend explicitly accepts PDFs on that path, `PDF + Manual model answer` is a contract bug that will break for users.

Scope: I reviewed every project-authored frontend file: `src/`, `public/`, `index.html`, `package.json`, `vite.config.ts`, `tsconfig*`, `eslint.config.js`, `README.md`, `.gitignore`, and asset references. Verification: `npm run build` passes, `npm run lint` fails with 5 issues, and there are no project tests.

### 1. 🚨 Critical Bugs (Must Fix Immediately)
- File: [App.tsx](/Users/sakshamsinghania/Documents/ScholarScan/assessment-system/frontend/src/App.tsx:114). Issue: `ResultsHistory` never mounts because `historyEmpty` starts `true` and the component that could change it is hidden behind that same flag. Fix: always mount `ResultsHistory` and let it render `loading` / `empty` / `error` internally.
- File: [assessment-api.ts](/Users/sakshamsinghania/Documents/ScholarScan/assessment-system/frontend/src/api/assessment-api.ts:23). Issue: manual mode sends every file as `image`, but the UI allows PDFs; `PDF + Manual` is a broken or at least ambiguous API contract. Fix: disable manual mode for PDFs or split the API into explicit legacy/manual and async/document endpoints.
- File: [assessment-api.ts](/Users/sakshamsinghania/Documents/ScholarScan/assessment-system/frontend/src/api/assessment-api.ts:40). Issue: API helpers do not consistently check `res.ok`, so server failures become JSON parse crashes or silent bad states. Fix: centralize fetch/error parsing in one typed request helper.
- File: [ProgressTracker.tsx](/Users/sakshamsinghania/Documents/ScholarScan/assessment-system/frontend/src/components/ProgressTracker.tsx:43). Issue: the SSE lifecycle is brittle; any stream error closes the real-time channel and falls back to short polling that can falsely fail long jobs. Fix: only poll after confirmed completion, keep reconnect behavior, and make polling abortable with backoff.

### 2. ⚠️ Potential Issues
- File: [ResultsHistory.tsx](/Users/sakshamsinghania/Documents/ScholarScan/assessment-system/frontend/src/components/ResultsHistory.tsx:14). Issue: fetch failure is treated as “empty history,” so users get silence instead of an error. Fix: add explicit `error` state with retry UI.
- File: [HealthBadge.tsx](/Users/sakshamsinghania/Documents/ScholarScan/assessment-system/frontend/src/components/HealthBadge.tsx:9). Issue: if `/health` fails once, the badge sits on “Checking…” forever and never refreshes. Fix: store `loading | ready | degraded | unavailable` separately and allow retry/polling.
- File: [AssessmentForm.tsx](/Users/sakshamsinghania/Documents/ScholarScan/assessment-system/frontend/src/components/AssessmentForm.tsx:204). Issue: `questionFile` skips the type validation used for the main answer upload, and there is no size limit for either file. Fix: share one validator for both inputs and enforce size ceilings before upload.
- File: [ProgressTracker.tsx](/Users/sakshamsinghania/Documents/ScholarScan/assessment-system/frontend/src/components/ProgressTracker.tsx:32). Issue: lint already flags impure render logic and effect dependency problems. Fix: remove `Date.now()` from render initialization, hoist callbacks, and satisfy hook deps cleanly.

### 3. 🧹 Code Smells & Clutter
- File: [ResultsDisplay.tsx](/Users/sakshamsinghania/Documents/ScholarScan/assessment-system/frontend/src/components/ResultsDisplay.tsx:10). Problem: one file owns score math, badges, accordions, summary cards, and multiple result layouts. Cleanup: extract `ScoreRing`, `GradeBadge`, `QuestionCard`, and score utilities.
- File: [assessment-api.ts](/Users/sakshamsinghania/Documents/ScholarScan/assessment-system/frontend/src/api/assessment-api.ts:49). Problem: dead/half-wired abstractions: unused `getTaskResult`, unused `questionId` path from the UI, and unused `ApiError` type in [assessment.ts](/Users/sakshamsinghania/Documents/ScholarScan/assessment-system/frontend/src/types/assessment.ts:62). Cleanup: wire them properly or delete them.
- File: [README.md](/Users/sakshamsinghania/Documents/ScholarScan/assessment-system/frontend/README.md:1). Problem: the frontend ships with default Vite boilerplate docs. Cleanup: replace it with real setup, API contract, run, build, and troubleshooting docs.
- File: `frontend/src/assets/hero.png`, `frontend/src/assets/react.svg`, `frontend/src/assets/vite.svg`, `frontend/public/icons.svg`, `frontend/public/favicon.svg`. Problem: these assets are unreferenced, and `dist/` plus `node_modules/` exist despite being ignored in [.gitignore](/Users/sakshamsinghania/Documents/ScholarScan/assessment-system/frontend/.gitignore:10). Cleanup: remove dead assets and stop treating generated output as source.

### 4. 🎨 UI/UX Improvements
- Problem: it fails the AI-slop test. Improvement: the interface is another dark, rounded, card-heavy dashboard with safe icon/header patterns. Example: make the intake side feel like a purposeful “grading desk” and render results more like an annotated paper than stacked dashboard cards.
- Problem: the copy is vague. Improvement: rename `Submit`, `AI Generated`, `Settings`, and `Ready` to task-specific language. Example: `Upload for grading`, `Generate model answer`, `Assessment options`, `Backend ready`.
- Problem: mobile layouts are weak. Improvement: the always-two-column settings grid, wide history table, and side-by-side score blocks need breakpoint-aware restructuring. Example: `grid-cols-1 sm:grid-cols-2`, mobile cards for history, and stacked score summaries under `md`.
- Problem: failure and empty states do not guide recovery. Improvement: teach users what happened and what to do next. Example: `We couldn’t load assessment history. Check the API connection and try again.`

### 5. ⚡ Performance Improvements
- File: [AssessmentForm.tsx](/Users/sakshamsinghania/Documents/ScholarScan/assessment-system/frontend/src/components/AssessmentForm.tsx:36). Issue: `readAsDataURL()` loads large images into memory as base64 strings. Optimization: switch to `URL.createObjectURL()` and revoke it on cleanup.
- File: [App.tsx](/Users/sakshamsinghania/Documents/ScholarScan/assessment-system/frontend/src/App.tsx:21). Issue: `historyKey` forces remounting to refresh history. Optimization: keep the component mounted and trigger refresh with a prop or query invalidation.
- File: [ProgressTracker.tsx](/Users/sakshamsinghania/Documents/ScholarScan/assessment-system/frontend/src/components/ProgressTracker.tsx:84). Issue: short-loop polling is network-wasteful and failure-prone. Optimization: centralize retry/backoff and stop polling when the component unmounts.
- File: [index.html](/Users/sakshamsinghania/Documents/ScholarScan/assessment-system/frontend/index.html:9). Issue: Google Fonts adds external render-blocking requests. Optimization: self-host the fonts or preload only the exact weights you use.

### 6. 🔗 API Layer Improvements
- Problem: response handling is inconsistent across `assess`, `getResults`, `getHealth`, and progress polling. Fix: create one `requestJson<T>()` helper with `res.ok` checks, safe JSON parsing, and typed error messages.
- Problem: progress result fetching bypasses the API layer entirely. Fix: move polling/SSE helpers into `api/assessment-api.ts` so the UI stops owning transport logic.
- Problem: the submission API mixes two contracts in one method. Fix: split it into explicit `submitManualAssessment()` and `submitDocumentAssessment()` calls.
- Problem: there is no timeout or cancellation policy. Fix: add `AbortController` to submissions, health checks, and result polling.

### 7. 🔐 Security Issues
- Risk: no obvious XSS or secret leak is present in the React layer; rendering API strings in text nodes is the right choice. Fix: keep feedback rendering text-only and never move it to `dangerouslySetInnerHTML`.
- Risk: unvalidated `questionFile` and no file-size limit widen the backend attack surface and DoS risk. Fix: validate MIME, extension, and size for both uploads.
- Risk: external Google Fonts introduces third-party data leakage, which is not ideal for an education product. Fix: self-host fonts or use a privacy-safe fallback.

### 8. 🧪 Testing Improvements
- Missing: there is no test runner or `test` script in [package.json](/Users/sakshamsinghania/Documents/ScholarScan/assessment-system/frontend/package.json:6). Suggestion: add `vitest`, `@testing-library/react`, and `msw`.
- Missing: upload contract tests. Suggestion: cover `image + manual`, `image + auto`, `pdf + auto`, and rejected `pdf + manual`.
- Missing: async workflow tests. Suggestion: integration-test SSE progress, disconnect recovery, delayed result availability, and history refresh after success.
- Missing: UI regression coverage. Suggestion: add keyboard/a11y tests and mobile snapshot tests for the form, result views, and history.

### 9. ✨ Refactored Components (IMPORTANT)
`App.tsx` core flow:
```tsx
const [historyRefreshToken, setHistoryRefreshToken] = useState(0)

const handleResult = useCallback((next: AnyAssessmentResult) => {
  setResult(next)
  setError(null)
  setActiveTaskId(null)
  setHistoryRefreshToken((token) => token + 1)
}, [])

<ResultsHistory refreshToken={historyRefreshToken} />
```

`assessment-api.ts` request helper:
```ts
async function requestJson<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const res = await fetch(input, init)
  const text = await res.text()
  const data = text ? JSON.parse(text) : null

  if (!res.ok) {
    throw new Error(data?.error ?? `Request failed (${res.status})`)
  }

  return data as T
}
```

`ProgressTracker.tsx` safer completion flow:
```tsx
const fetchResult = useCallback(async (signal: AbortSignal) => {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    const res = await fetch(`/api/task/${taskId}/result`, { signal })
    if (res.status === 200) return onComplete(await res.json())
    if (res.status !== 202) throw new Error(`Unexpected status ${res.status}`)
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
  throw new Error('Timed out waiting for the final result')
}, [taskId, onComplete])

useEffect(() => {
  const controller = new AbortController()
  const es = new EventSource(`/api/progress/stream/${taskId}`)
  es.onmessage = (event) => { /* update steps; call fetchResult only after completed */ }
  return () => { controller.abort(); es.close() }
}, [taskId, fetchResult])
```

### 10. 📊 Overall Rating
- Code Quality: `4/10`
- UI/UX: `4/10`
- Performance: `5/10`
- Production Readiness: `3/10`

### 11. 🧠 Final Verdict
This frontend is not production-ready. It is a decent prototype with a coherent visual tone, but it still has a broken history flow, brittle async lifecycle management, weak API/error abstraction, silent failure states, no test safety net, and obvious mobile/accessibility debt.

What is holding it back is not “polish.” It is reliability. Thousands of users will hit edge cases, slow jobs, disconnects, backend errors, and phones first. Right now the frontend handles those scenarios poorly or not at all. Build passes, but lint already fails, and the failure paths are the weakest part of the app.