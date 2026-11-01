# AGENTS.md — DocExtract

> Canonical instructions for ALL AI coding agents (Claude Code, Copilot, Gemini CLI, Cursor, Codex, Windsurf, Aider, Cline…).
> Tool-specific files (`CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.cursor/rules/*`) point here. **Edit this file, not the pointers.**

## What this project is
DocExtract is a local-first microservice that turns a PDF into **custom structured JSON**.
The user describes the output either as a **nested shape** (`{ people: [{ name: string, age: number }] }`) or in **plain English**; the service parses the PDF with **Docling**, chunks the text,
asks a **local LLM (LM Studio, OpenAI-compatible API)** to extract the fields from each chunk using strict JSON-schema output,
then merges + deduplicates the chunk results into one JSON document.

It evolved from a single-file prototype (`legacy/extract.py`). Behaviour of that prototype is the reference; see `docs/ARCHITECTURE.md`.

## Monorepo layout
```
backend/    FastAPI service (Python 3.11+, uv)      -> see backend/AGENTS.md
frontend/   Next.js App Router (TypeScript)         -> see frontend/AGENTS.md
docs/       ARCHITECTURE, API, FRONTEND (UX spec), SETUP, DECISIONS, ROADMAP
legacy/     original prototype script (read-only reference)
data/       runtime files (uploads, parsed markdown, SQLite) — gitignored
```

## Tech stack (decided — see docs/DECISIONS.md before changing)
| Layer | Choice |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic v2, SQLModel + SQLite, `uv` for deps |
| PDF parsing | `docling` (Markdown export, cached by file SHA-256) |
| LLM | LM Studio via `openai` SDK, `response_format=json_schema` (strict) |
| Jobs | In-process async worker queue (concurrency = 1), progress via SSE |
| Frontend | Next.js (App Router) + TypeScript + Tailwind + shadcn/ui + TanStack Query |
| Contract | OpenAPI from FastAPI -> generated TS client (`openapi-typescript`) |
| Dev infra | Docker Compose optional; plain `make dev` is the default |

## Commands
```bash
make setup      # install backend + frontend deps
make dev        # run backend (:8000) and frontend (:3000) together
make test       # pytest + vitest
make lint       # ruff + mypy + eslint + tsc --noEmit
make gen-client # regenerate frontend API types from backend OpenAPI
```
Backend only: `cd backend && uv run fastapi dev app/main.py`  
Frontend only: `cd frontend && npm run dev`

## Hard rules
1. **Never hardcode extraction logic for specific fields.** The old prompt mentions "character names" and "countries" — that was a test schema. Prompts must be generated from the user's resolved shape + field descriptions.
2. **Never commit** `.env`, `data/`, uploaded PDFs, or parsed output.
3. **LLM output is untrusted.** Always validate with the dynamically built Pydantic model before saving.
4. **Long work is never done inside a request handler.** Create a job, return `202`, stream progress.
5. **Checkpoint per chunk.** A crash at chunk 40/50 must resume at 40.
6. **Cache keys are content hashes**, never fixed filenames (the prototype's fixed `parsed_document.md` is a known bug).
7. **API contract first.** Change backend schemas -> run `make gen-client` -> then touch frontend.
8. Frontend behaviour/UX is specified in `docs/FRONTEND.md` — follow it. Feedback payloads never contain PDF text or results.
9. No new dependency without a line in `docs/DECISIONS.md`.
10. Don't edit `legacy/`.

## Code style
- Python: ruff (format + lint), full type hints, `async def` for I/O, no bare `except`, structured logging via `logging` (no `print`).
- TypeScript: strict mode, no `any`, server components by default, `"use client"` only when needed.
- Small modules, small functions. Prefer pure functions for chunking / merging / schema building so they're unit-testable.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).

## Testing expectations
- Pure logic (schema builder, chunker, merger) -> unit tests, no network.
- LLM calls -> mocked client in unit tests; one opt-in integration test marked `@pytest.mark.llm`.
- API -> `httpx.AsyncClient` against the FastAPI app.
- Every bug fix gets a regression test.

## Definition of done
Lint + types + tests pass, docs updated if API/behaviour changed, no TODOs without a ticket in `docs/ROADMAP.md`.

## When unsure
Read `docs/ARCHITECTURE.md`, then `docs/DECISIONS.md`. If still ambiguous, ask the human — don't guess on schema semantics or job lifecycle.
