# API (v1) — source of truth is `/openapi.json`; this is the design contract
Base: `http://localhost:8000/api/v1`

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness + LM Studio reachability + loaded models |
| GET | `/models` | models reported by LM Studio |
| POST | `/documents` | multipart PDF -> `201 {id, sha256}` (dedupes by hash) |
| GET | `/documents/{id}/markdown` | parsed Markdown |
| POST | `/schemas/parse` | `{text}` -> `{ok, shape_tree, json_schema}` or `{ok:false, errors:[{line,col,message}]}`. Detects whether text is a shape |
| POST | `/schemas/infer` | `{request}` (plain English) -> `{shape_text, shape_tree}`; powers "Preview shape" |
| POST | `/jobs` | `{document_id, input_text, input_mode?: "auto"\|"shape"\|"natural_language", model?, chunk_size?}` -> `202 {id}` |
| GET | `/jobs` | history |
| GET | `/jobs/{id}` | status, progress, resolved shape, result when done |
| GET | `/jobs/{id}/chunks` | all checkpoints (index, status, result_json) |
| GET | `/jobs/{id}/events` | **SSE** stream (see below) |
| POST | `/jobs/{id}/cancel` | cancel |
| POST | `/jobs/{id}/retry` | resume from last checkpoint |
| GET | `/jobs/{id}/result.json` | download final JSON |
| POST | `/feedback` | `{job_id?, rating, tags[], comment?, email?}` -> `201` |

## SSE events
```
event: status   data: {"stage":"extracting"}
event: shape    data: {"shape_text":"{ people: [...] }","json_schema":{...}}
event: chunk    data: {"index":12,"total":50,"status":"saved","attempts":1,"duration_ms":4210,"result":{...}}
event: partial  data: {"merged":{...}}
event: done     data: {"result":{...}}
event: error    data: {"message":"..."}
```

## Errors
RFC 7807 `application/problem+json`.
