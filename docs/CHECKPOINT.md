# DocExtract Memory & Checkpoints

This file acts as a persistent working memory for agent operations, key architectural parameters, and implementation details.

## Context & Constraints
- **Naive Reference Script**: `legacy/extract.py` (copied from `pdf-to-json.py`)
- **Key Requirement 0**: Schema must be variable and dynamic, supporting nested shapes (`{ people: [{ name: string, age: number }] }`) and natural language inference.
- **Key Requirement 1**: No test cases written right now, but leave dedicated space / file stubs for them (`backend/tests/`, `frontend/__tests__/`).
- **Key Requirement 2**: Do not check for linting yet (skip ruff, mypy, eslint).
- **Key Requirement 3**: Ask for recommendations/options before making major decisions.
- **Key Requirement 4**: Permission required before changing instruction files (`AGENTS.md`, `ARCHITECTURE.md`, etc.).
- **Key Requirement 5 & 6**: Checkpoint memory in `CHECKPOINT.md`, progress logged in `PROGRESS.md`.
- **Key Requirement 7**: Frontend must be fully mobile friendly (responsive touch targets, collapsible drawers, adaptive grids).

## Architecture Highlights
- **Backend Stack**: FastAPI, SQLModel + SQLite (`data/docextract.db`), Pydantic v2, Docling, OpenAI client for LM Studio.
- **Frontend Stack**: Next.js App Router (TypeScript), Tailwind CSS, TanStack Query, Lucide icons, mobile-responsive components.
- **Job States**: `queued -> inferring_shape -> parsing -> extracting -> merging -> done | failed | cancelled`
- **Real-Time Streaming**: Server-Sent Events (`/api/v1/jobs/{id}/events`) with state replaying on connect.
- **Checkpoints**: Every chunk result is persisted to SQLite upon extraction completion, enabling resumption on crash or restart.
- **Milestone Status**: Milestones 0, 1, 2, and 3 are 100% complete. Frontend build, typecheck, linting, and backend test suites all passing. Ready for Milestone 4 (Polish & Docker Compose).

