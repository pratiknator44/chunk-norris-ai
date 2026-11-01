# Decision log (ADR-lite)
Format: date — decision — why — alternatives.

## 001 — Backend is Python/FastAPI, not Node
Docling is Python-only. A Node backend would need a Python sidecar anyway (two runtimes, two deploys). FastAPI gives native Pydantic validation (already used in the prototype), automatic OpenAPI -> typed TS client for Next.js, and async + SSE. *Alternative:* NestJS + Docling as a separate service — rejected for v1 complexity; revisit if the team wants a TS-only API gateway.

## 002 — Frontend is Next.js App Router + TypeScript
Per project requirement. UI talks to the backend over REST + SSE only; no Next.js API routes holding business logic (they may proxy to avoid CORS in prod).

## 003 — SQLite + SQLModel for state
Single-user local-first. Replaces the JSON checkpoint file. Swap to Postgres later by changing the URL.

## 004 — In-process job worker, concurrency 1
Local LLM + GPU can't parallelize usefully. Avoids Redis/Celery. Interface is isolated in `jobs/queue.py` so it can become `arq`/Redis later.

## 005 — SSE over WebSockets
One-way progress stream; simpler, proxy-friendly, native `EventSource`.

## 006 — Schema-driven prompts
Field descriptions are the only domain knowledge in prompts. No entity-specific rules in code.

## 007 — Content-hash caching
Parsed Markdown and chunk results keyed by SHA-256 (+ chunk size + model + prompt version).

## 008 — User input is a shape language OR plain English
Users can paste a TypeScript-like shape (`{ people: [{ name: string, age: number }] }`) or write a sentence. Shape parsing lives only in the backend (`core/shape.py`) so there is one grammar; the frontend just renders errors/tree. Plain English is converted to a shape by an LLM step, shown to the user, and then follows the identical pipeline. *Alternative:* raw JSON Schema input — rejected, too heavy for the target user.

## 009 — Progress via checkpoints streamed over SSE
Each saved chunk is both the resume point and a UI event (`chunk` + `partial`). One mechanism serves durability and UX.

## 010 — Feedback stored locally, content-free
Feedback table holds rating/tags/comment/optional email and an optional job id. PDF text and extraction results are never attached.

## 011 — Frontend scaffolded with Next.js 16.4.3 & React 19.3.0
Scaffolded non-interactively via `create-next-app@latest` with App Router, TypeScript, ESLint, and Tailwind CSS v4. Added TanStack Query v5, lucide-react, react-hook-form, zod, vaul/sheet for mobile UX, and openapi-typescript for contract generation.

