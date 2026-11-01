# Architecture

## Pipeline
```
POST /documents (PDF)           -> store file, SHA-256 (dedupe)
POST /jobs {document, output_spec}
  output_spec = shape text  OR  natural-language request
  -> [if NL] LLM infers a shape                     (stage: inferring_shape)
  -> parse shape -> JSON Schema + Pydantic model    (core/shape.py, core/schema.py)
  -> Docling parse -> Markdown                      (cached: data/parsed/<sha256>.md)
  -> chunk (paragraph-aware, overlap)
  -> per chunk (each one a CHECKPOINT row in DB):
        prompt built from the shape
        LM Studio call, response_format=json_schema (strict)
        validate with Pydantic -> save ChunkResult -> emit SSE `chunk` + `partial`
  -> merge + dedupe -> final JSON -> job done
POST /feedback (after result)
```

## Components
```
Next.js  <--REST + SSE-->  FastAPI --> SQLite (documents, jobs, chunk_results, schemas, feedback)
                              |-----> Docling (thread/process)
                              '-----> LM Studio (OpenAI-compatible, LAN)
```

## Data model
- **Document**: id, filename, sha256, size, parsed_md_path, created_at
- **Job**: id, document_id, input_mode (`shape`|`natural_language`), input_text, resolved_shape (JSON Schema snapshot), model, status, chunks_done/total, error, result_json, timestamps
- **ChunkResult** (the checkpoints): job_id, chunk_index, result_json, attempts, duration_ms, created_at
- **SavedShape** (optional, v1.1): id, name, shape_text
- **Feedback**: id, job_id (nullable), rating, tags[], comment, email (nullable), app_version, created_at

The resolved shape is **snapshotted on the job**: later edits never alter past results.

## Shape language (user input) -> JSON Schema
Backend-owned parser (`core/shape.py`); frontend only sends text and renders errors/tree.

| Input | Meaning |
|---|---|
| `string` `number` `integer` `boolean` | scalar (nullable in schema, so the model can say "not found") |
| `date` | ISO 8601 string (`YYYY-MM-DD`, prompt guided, lenient format in schema) |
| `"val1" \| "val2"` | enum of string literals (maps to JSON Schema `enum`) |
| `T?` | optional field (in strict mode, stays in `required` but typed `[T, null]`) |
| `{ a: T, b: U }` | object (concrete fields required, no empty objects or `any`) |
| `[ T ]` or `T[]` | array of T (T may be an object -> array of objects) |
| `// text` after a field | description injected into the prompt and schema |
| Top-level array: `[ T ]` or `T[]` | allowed; wrapped internally as `{ items: [ T ] }` and unwrapped in final result |

Example: `{ people: [{ name: string, status: "active" | "inactive", birth_date: date?, age: number? // years }], summary: string }`

Rules: unquoted or quoted keys, `,` or `;` separators, trailing commas OK, max nesting depth 5, max 100 fields. Key names `^[A-Za-z_][A-Za-z0-9_]*$`. Strict mode in LM Studio: every property `required`, `additionalProperties: false`, scalars `["T","null"]`. No `any` and no object without fields. Mode detection: parse as shape first; if it fails and starts with `{` or `[`, keep shape mode with line/col errors; otherwise fallback to natural language.

## Natural-language mode
A single short LLM call: request text -> shape text (same language above) with descriptions. Result is validated by the same parser; on failure retry once with the parse error fed back. The inferred shape is stored on the job and shown to the user (editable via "Run again with edited shape").

## Merge rules (per node, recursive)
| Node | Rule |
|---|---|
| scalar | first non-null/non-empty, in chunk order |
| object | merge each child recursively |
| array of scalars | union, case-insensitive dedupe, keep first-seen order |
| array of objects | concatenate, then dedupe by canonical JSON of normalized values; if the shape has an obvious key (`name`, `id`, `title`) merge entries with the same key by filling nulls |

Known limitation: the same entity described differently in two chunks may stay duplicated. v1.1: optional **consolidation pass** (LLM merges near-duplicates over the merged result).

## Job lifecycle
`queued -> inferring_shape (NL only) -> parsing -> extracting -> merging -> done`; any -> `failed` / `cancelled`. On server restart, in-flight jobs are re-queued and resume from the last ChunkResult.

## Realtime
SSE `/jobs/{id}/events`. Events: `status`, `shape` (resolved shape), `chunk` (index, status, attempts, item counts), `partial` (merged-so-far JSON), `done`, `error`. On connect the server first replays current state, so refresh/reconnect is safe.

## Known issues in the prototype (fix during port)
1. `parsed_document.md` cache is a fixed filename -> different PDF reuses stale text. Key by SHA-256.
2. Checkpoint hash ignores chunk size / model / prompt version.
3. One failed chunk aborts the run; no retry.
4. `finish_reason == "length"` hard-fails; shrink chunk and retry.
5. Prompt rules are specific to the test schema; generate from the shape.
6. Non-overlapping chunks can split entities.
7. Global `START_TIME`, `print` logging, no cancel, no concurrency control.
8. Result order depends on dict insertion; sort by chunk index.
9. Flat schema only; now nested objects / arrays of objects are required.

## Non-goals (v1)
Auth, multi-user, cloud LLMs, OCR tuning UI, table extraction.
