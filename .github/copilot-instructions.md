# Copilot instructions — DocExtract

Full rules: see `AGENTS.md` (root), `docs/FRONTEND.md` (UX flow), `backend/AGENTS.md`, `frontend/AGENTS.md`, and `docs/ARCHITECTURE.md`. Summary:

**Project:** local-first service. PDF -> Docling Markdown -> chunks -> local LLM (LM Studio, OpenAI-compatible, strict JSON schema) -> merged, deduplicated JSON based on a *user-defined output*: a nested shape like `{ people: [{ name: string, age: number }] }` or a plain-English request (inferred into a shape first).

**Stack:** FastAPI + Pydantic v2 + SQLModel/SQLite (backend, Python 3.11+, `uv`), Next.js App Router + TypeScript + Tailwind + shadcn/ui + TanStack Query (frontend).

**Always:**
- Build prompts and validation models dynamically from the user's schema; never hardcode field names.
- Validate all LLM output with Pydantic before saving.
- Run long work as background jobs (return 202, stream progress via SSE).
- Checkpoint after every chunk; cache by content hash.
- Type hints everywhere (Python), strict TS with no `any`.
- Use generated API types in the frontend; never hand-write backend types.
- Conventional Commits.

**Never:** commit `.env`/`data/`/PDFs, block the event loop with Docling, edit `legacy/`, add dependencies without noting it in `docs/DECISIONS.md`.
