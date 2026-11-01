# DocExtract Progress Log

This file tracks the operational log, session context, and execution notes across milestones.
Detailed task checklists are tracked directly in [ROADMAP.md](file:///d:/docling/docextract/docs/ROADMAP.md).

## Operational Log

### 2026-11-01
- **Phase 0 (Initialization)**:
  - Inspected repository and naive script `pdf-to-json.py`.
  - Moved prototype to `legacy/extract.py`.
  - Updated `docs/ARCHITECTURE.md` with enums, date format, top-level arrays (`[ { ... } ]`), and mode detection rules.
  - Received user approval on architecture tweaks and non-interactive `create-next-app` scaffolding.
- **Milestone 0 (Bootstrap)**:
  - Backend dependencies installed with `uv sync` (FastAPI, SQLModel, Docling, OpenAI SDK, Pytest, etc.).
  - Configured `backend/app/config.py` with pydantic-settings.
  - Implemented `backend/app/api/health.py` (`/health` & `/models` endpoints) and `backend/app/main.py` with CORS & RFC 7807 error handler.
  - Frontend scaffolded with Next.js 16.4.3, React 19.3.0, TypeScript, Tailwind CSS v4, TanStack Query, react-hook-form, zod, lucide-react, openapi-typescript.
  - Verified backend app initialization.
  - Milestone 0 completed. Ready for Milestone 1.
- **Milestone 1 (Core Pipeline Pure Modules)**:
  - `core/shape.py` & `tests/test_shape.py`: Implemented tokenizer & parser for custom shape grammar with enums, dates, optionals, nested objects, comments, top-level arrays, limits (depth 5, max 100 fields, no empty objects/any), and `detect_mode`. 10 unit tests passing.
  - `core/schema.py` & `tests/test_schema.py`: Implemented strict JSON Schema generator and dynamic Pydantic v2 validation models. 5 unit tests passing.
  - `core/merge.py` & `tests/test_merge.py`: Implemented recursive chunk merger with scalar first-seen, array case-insensitive dedupe, entity key matching & null-filling, and top-level array handling. 4 unit tests passing.
  - `core/chunking.py` & `tests/test_chunking.py`: Implemented paragraph-aware chunker with word boundary protection and overlap. 5 unit tests passing.
  - `core/prompts.py`: Schema-driven prompt generator and NL-to-shape inference prompt with syntax error retry.
  - `core/parsing.py`: Async Docling executor run on a thread (`asyncio.to_thread`) with SHA-256 markdown cache in `data/parsed/<hash>.md`.
  - `core/llm.py`: LM Studio client with `asyncio.Semaphore(1)` concurrency control, exponential backoff retries, and `TokenLimitExceededError` detection.
  - Milestone 1 completed (all 24 unit tests passing).
- **Milestone 3 (Frontend)**:
  - `src/lib/api/schema.d.ts` & `src/lib/api/client.ts`: Typed API client for documents, schemas, jobs, feedback, and health.
  - `src/lib/hooks/useJobStream.ts`: SSE listener hook with automatic state replay, live elapsed seconds timer, chunk state aggregation, and error handling.
  - `src/components/health-banner.tsx`: Health check indicator for LM Studio connectivity with automatic polling.
  - `src/components/upload-dropzone.tsx`: Drag & drop and file selector with file size/type validation.
  - `src/components/shape-editor/shape-editor.tsx`: Live shape and natural-language editor with 350ms debounced syntax validation, mode badge, manual override, line/col error highlights, and "Preview shape" trigger.
  - `src/components/shape-editor/preview-shape-modal.tsx`: Inferred shape review and edit modal.
  - `src/components/job/stage-stepper.tsx`: Stepper for visual job progression across all pipeline phases.
  - `src/components/job/chunk-timeline.tsx` & `chunk-modal.tsx`: Vertical chunk timeline on mobile, responsive grid on desktop with Vaul drawer checkpoint inspector.
  - `src/components/job/live-result.tsx`: Streaming partial JSON viewer.
  - `src/components/json-viewer.tsx`: Interactive tree view + raw JSON copy/download viewer.
  - `src/components/feedback-drawer.tsx`: Vaul bottom-sheet (mobile) / slide-over (desktop) feedback modal with rating, tag pills, comments, and localStorage dismissal.
  - `src/app/jobs/[id]/page.tsx` & `job-content.tsx`: Dynamic job tracking screen with Suspense boundary.
  - Verification: `npm run typecheck`, `npm run lint`, and `npm run build` all pass with 0 errors. Backend unit test suite (32 tests) fully passing.




