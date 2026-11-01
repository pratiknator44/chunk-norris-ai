# backend/AGENTS.md
Inherits everything from the root `AGENTS.md`. Backend-specific rules:

## Structure
```
backend/app/
  main.py            FastAPI app factory, CORS, lifespan (starts worker)
  config.py          pydantic-settings; reads .env
  api/               routers: documents.py, schemas.py, jobs.py, health.py
  core/
    parsing.py       Docling wrapper + content-hash cache
    chunking.py      split_document()  (pure)
    shape.py         parse shape language -> shape tree, with line/col errors  (pure)
    schema.py        shape tree -> strict JSON Schema + Pydantic model  (pure)
    prompts.py       build prompts FROM schema + field descriptions
    llm.py           LM Studio client, retries, finish_reason handling
    merge.py         merge_results()  (pure)
  jobs/              queue.py, worker.py, events.py (SSE pub/sub)
  db/                models.py (SQLModel), session.py
  tests/
```

## Rules
- Routers are thin: validate -> call service -> return. No business logic in routers.
- Docling is **blocking and CPU/GPU heavy** — run it with `asyncio.to_thread` / a process pool, never on the event loop.
- Only ONE LLM request in flight at a time by default (`LLM_CONCURRENCY=1`); local GPUs choke otherwise.
- Retry LLM calls (max 3, exponential backoff) on timeout / invalid JSON. `finish_reason == "length"` is **not** retryable as-is: halve chunk size for that chunk and retry.
- The shape grammar lives in ONE place (`core/shape.py`); JSON Schema generation in `core/schema.py`. Supported: scalars, optional (`?`), nested objects, arrays (incl. arrays of objects). Grammar changes require updating `docs/ARCHITECTURE.md` + tests.
- Plain-English input goes through an LLM *shape inference* step whose output is re-parsed by `core/shape.py`; never trust it unparsed.
- Job states: `queued -> inferring_shape -> parsing -> extracting -> merging -> done | failed | cancelled`.
- Errors returned as RFC 7807 problem JSON.

## Commands
```bash
uv sync
uv run fastapi dev app/main.py
uv run pytest
uv run ruff check . && uv run ruff format .
uv run mypy app
```
