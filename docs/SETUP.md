# Local setup

## 1. Prerequisites
- Python 3.11+ and `uv`  (`pipx install uv` or see uv docs)
- Node 20+
- LM Studio: load a model, enable **Local Server**, note the URL (e.g. `http://192.168.0.5:1234/v1`). Enable "serve on local network" if it runs on another machine.

## 2. Environment
```bash
cp .env.example .env
```
Edit `LM_STUDIO_URL` and (optionally) `LLM_MODEL`. Leave empty to auto-pick the first loaded model.

## 3. Install & run
```bash
make setup
make dev
```

## 4. Move the prototype
Copy your original script to `legacy/extract.py` (reference only).

## Troubleshooting
- **Connection refused to LM Studio**: check firewall, LAN IP, and that the server toggle is on.
- **Docling first run is slow**: it downloads layout models once.
- **`finish_reason=length`**: lower `CHUNK_MAX_CHARS` or raise `LLM_MAX_OUTPUT_TOKENS`.
- **GPU out of memory**: keep `LLM_CONCURRENCY=1`; Docling and the LLM compete for VRAM, so don't run them on a small card at the same time (parsing finishes before extraction begins, which helps).
