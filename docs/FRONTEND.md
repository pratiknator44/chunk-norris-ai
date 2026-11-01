# Frontend flow & UX spec

Single main screen (`/`) + job screen (`/jobs/[id]`).

## Flow
1. **Pick PDF** — dropzone (drag/drop or browse), shows filename + size. PDF only, max `MAX_UPLOAD_MB`.
2. **Describe output** — one textarea, two accepted forms (auto-detected, with a badge + manual toggle):
   - **Shape**: `{ people: [{ name: string, age: number }], summary: string }`
     Bare words as types, unquoted keys, trailing commas, `// comments` (become field descriptions), `type?` = optional, `[ {...} ]` or `{...}[]` for lists.
   - **Plain English**: `return a json with list of all names in this pdf with one liner intros`
     The backend first *infers a shape* from the sentence (LLM call), then runs the same pipeline.
   - Live validation: debounce -> `POST /schemas/parse`; show errors with line/col, show the resolved shape as a collapsible tree.
   - Optional **"Preview shape"** button for plain English: shows the inferred shape, editable, before extracting.
3. **Extract** button — uploads PDF (`POST /documents`) then creates the job (`POST /jobs`) and navigates to `/jobs/[id]`.
4. **Progress** (SSE) — stage stepper: `Uploaded -> Parsing PDF -> Inferring shape (if NL) -> Extracting -> Merging -> Done`.
   - Chunk timeline: one row/pill per chunk (queued / running / saved / retried / failed) — **each "saved" pill is a checkpoint**, click to see that chunk's raw extracted JSON.
   - "Live result" panel: the merged-so-far JSON updates after every checkpoint.
   - Elapsed time, ETA (from avg chunk time), Cancel button. Refresh-safe: reconnecting to SSE replays state.
5. **Result** — JSON viewer (collapsible tree + raw tab), Copy, Download `.json`, "Run again with edited shape" (keeps PDF).
6. **Feedback drawer** — right-side slide-over, appears ~2s after the result renders (and via a persistent "Feedback" edge tab).
   - Rating (thumbs or 1–5), quick tags (`Missing items`, `Wrong values`, `Too slow`, `Confusing UI`, `Great`), free text, optional email.
   - Checkbox "Include this job's id" (default on). **Never send PDF text or result content.**
   - Dismissible; remember dismissal per job in `localStorage`; never auto-open twice for the same job.

## States to design for
Empty, uploading, parse error (unreadable/scanned PDF), LM Studio unreachable (banner from `/health`), no model loaded, shape invalid, job failed (show error + "Resume from checkpoint"), cancelled, huge result (virtualize).

## Components
`upload-dropzone`, `shape-editor` (CodeMirror/Monaco-lite, monospace, mode badge), `shape-tree`, `stage-stepper`, `chunk-timeline`, `live-result`, `json-viewer`, `feedback-drawer`, `health-banner`.
