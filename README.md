# Chunk Norris

> Convert PDF to JSON via local LLM

1. run an LLM in local server like LM Studio
<img width="580" height="86" alt="image" src="https://github.com/user-attachments/assets/94cb99ad-ef8a-47a2-a7a7-76489f07b5f0" />

2. upload pdf and provide a json structure
<img width="823" height="623" alt="image" src="https://github.com/user-attachments/assets/ef51857a-ef9c-4e83-8b2b-cdae50402a4d" />

3. Start and let the magic happen. Works best for 7B+ models :)
<img width="1088" height="510" alt="image" src="https://github.com/user-attachments/assets/84c99e2e-3f43-497c-8f51-907e22e51079" />

output summary:
```
{
  "chapters": [
    {
      "chapterNo": 1,
      "chapterName": "An Animal of No Significance",
      "chapterSummary": "About 13.5 billion years ago, matter, energy, time and space came into being in what is known as the Big Bang. The story of these fundamental features of our universe is called physics. About 300,000 years after their appearance, matter and energy started to coalesce into complex structures, called atoms, which then combined into molecules. The story of atoms, molecules and their interactions is called chemistry. About 3.8 billion years ago, on a planet called Earth, certain molecules combined to form particularly large and intricate structures called organisms. The story of organisms is called biology. About 70,000 years ago, organisms belonging to the species Homo sapiens started to form even more elaborate structures called cultures. The subsequent development of these human cultures is called history. Three important revolutions shaped the course of history: the Cognitive Revolution kick-started history about 70,000 years ago. The Agricultural Revolution sped it up about 12,000 years ago. The Scientific Revolution, which got under way only 500 years ago, may well end history and start something completely different. This book tells the story of how these three revolutions have affected humans and their fellow organisms."
    },...
```

Chunk Norris is a local-first document extraction engine. Upload any PDF, specify your target JSON structure (using concise TypeScript-like shape syntax or plain English), and extract validated structured JSON with zero cloud dependency—powered by Docling and your local LLM (LM Studio, Ollama, or OpenAI-compatible server).

---

## Features

- 📄 **Docling PDF Parsing**: High-accuracy document parsing with content-hash SHA-256 caching.
- ⚡ **Real-Time Pagewise Progress**: Live pagewise parsing updates (e.g., `processing page 32 of 834`).
- 🧩 **Concise Shape Language**: Define output schemas with intuitive TypeScript-like syntax (primitives, optional fields, string literal enums, nested objects, and arrays).
- 💬 **Plain English Inference**: Describe what you want in natural language; local LLM automatically drafts the exact shape definition.
- 🔄 **Chunk-by-Chunk Extraction**: Splits documents into token-safe overlapping chunks with automatic halving if token limits are encountered.
- 💾 **Resilient Checkpoints**: Each completed chunk is saved immediately as a database checkpoint; failed or interrupted runs can be resumed instantly without re-processing.
- 📡 **Server-Sent Events (SSE)**: Live streaming pipeline stages, chunk statuses (`in progress`, `Checkpoint Saved`), durations in seconds, and live partial merged preview.
- 🔒 **100% Local & Private**: No data leaves your machine. Runs against local inference engines.

---

## Quick Start

### 1. Configure Environment
```bash
cp .env.example .env
```
Ensure your local LLM server (e.g. LM Studio) is running with an active model loaded:
- Default: `http://localhost:1234/v1`

### 2. Backend Setup
```bash
cd backend
# Create virtual environment & install dependencies with uv
uv venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Run FastAPI backend
uvicorn app.main:app --reload --port 8000
```
API Documentation will be live at `http://localhost:8000/docs`.

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## Output Shape Specification

Define schemas using concise TypeScript-like shape syntax:

```typescript
{
  title: string,
  people: [
    {
      name: string,
      role: "speaker" | "attendee"?,
      age: number? // age in years
    }
  ],
  summary: string
}
```

### Syntax Overview
| Syntax | Meaning |
|---|---|
| `name: string` | Required primitive (`string`, `number`, `integer`, `boolean`, `date`) |
| `age: number?` | Optional field |
| `status: "open" \| "closed"` | String literal union enum |
| `tags: [string]` or `string[]` | Array of primitives |
| `items: [ { id: string } ]` | Array of nested objects |
| `// comment` | Field description passed to LLM prompt |

---

## Architecture Overview

```
[ PDF Upload ]
      │
      ▼
[ Docling Converter ] ──> Pagewise Progress Stream (e.g., page 32 of 834)
      │
      ▼
[ Content-Hash Cache ] ──> data/parsed/{hash}.md
      │
      ▼
[ Document Chunking ] ──> Paragraph-aware chunk splits
      │
      ▼
[ Local LLM Extraction ] ──> Per-chunk extraction with validation & checkpoints
      │
      ▼
[ Recursive Merger ] ──> Deduplicated, unified output JSON
```

---

## API Summary

- `POST /api/v1/documents` — Upload PDF file
- `POST /api/v1/schemas/parse` — Validate shape syntax / detect mode
- `POST /api/v1/schemas/infer` — Convert plain English request into shape syntax
- `POST /api/v1/jobs` — Enqueue extraction job
- `GET  /api/v1/jobs/{id}` — Job status and result details
- `GET  /api/v1/jobs/{id}/events` — Real-time Server-Sent Events (SSE) stream
- `POST /api/v1/jobs/{id}/cancel` — Cancel in-flight job
- `POST /api/v1/jobs/{id}/retry` — Resume job execution from saved checkpoint

---
<p align="center">Created with ❤️ by github/pratiknator44</p>
