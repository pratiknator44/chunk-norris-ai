# Roadmap / task list
Agents: pick the first unchecked task, finish it fully (code + tests + docs), tick it.

## Milestone 0 — Bootstrap
- [x] Move prototype to `legacy/extract.py`
- [x] `backend`: `uv init`, add deps (fastapi, uvicorn, pydantic-settings, sqlmodel, openai, docling, python-multipart, httpx, pytest, pytest-asyncio, ruff, mypy)
- [x] `frontend`: `npx create-next-app@latest` (TS, Tailwind, App Router, src dir), add shadcn/ui, TanStack Query, zod, react-hook-form, openapi-typescript
- [x] `config.py`, `/health` endpoint, CORS
- [x] Makefile targets work

## Milestone 1 — Core pipeline as pure modules (backend)
- [x] `core/shape.py` (+ tests) — lenient shape-language parser (see ARCHITECTURE): bare types, `?`, nested objects, arrays of objects, `//` descriptions, line/col errors
- [x] `core/schema.py` (+ tests) — shape tree -> strict JSON Schema + dynamic Pydantic model (nested)
- [x] `core/chunking.py` (+ tests) — port `split_document`, add overlap
- [x] `core/merge.py` (+ tests) — recursive merge (scalars, objects, arrays, arrays of objects), sort by chunk index
- [x] `core/prompts.py` — shape-driven prompts + natural-language -> shape inference prompt (retry with parse error)
- [x] `core/parsing.py` — Docling in thread, SHA-256 cache
- [x] `core/llm.py` — retries, length handling, model discovery

## Milestone 2 — API + jobs
- [x] DB models + migrations (Alembic or `create_all` for v1)
- [x] `POST /documents`, `POST /schemas/parse`, `POST /schemas/infer`
- [x] Job queue + worker + resume on restart
- [x] `POST /jobs`, `GET /jobs/{id}`, `/jobs/{id}/chunks`, SSE (state replay on connect, `chunk` + `partial` events), cancel, retry
- [x] `POST /feedback` + Feedback table
- [x] Integration test with mocked LLM

## Milestone 3 — Frontend (spec: docs/FRONTEND.md)
- [x] API client generation (`make gen-client`)
- [x] Main screen: PDF dropzone + shape/plain-English editor with auto-detect badge and live validation
- [x] "Preview shape" for plain English (editable)
- [x] Job page: stage stepper, chunk/checkpoint timeline, live merged result, cancel, resume
- [x] Result viewer: tree + raw, copy, download, "run again with edited shape"
- [x] Feedback slide-over drawer (rating, tags, comment, optional email, job id opt-in)
- [x] Health banner (LM Studio down / no model)

## Milestone 4 — Polish
- [ ] Docker Compose (backend + frontend; LM Studio stays on host)
- [ ] Consolidation pass (LLM merges near-duplicate objects)
- [ ] Saved shapes + job history page
- [ ] Evidence/citations: return source chunk for each extracted value
- [ ] Optional OCR toggle for scanned PDFs
- [ ] CI (GitHub Actions: lint, types, tests)
