# Career Advisor

AI career-intelligence platform combining Retrieval-Augmented Generation, resume parsing, and live job search behind a FastAPI backend, a Next.js frontend, and a Model Context Protocol (MCP) server.

## Overview

Career Advisor is a dual-tier application: a Python backend exposing RAG-grounded chat, resume analysis, skill-gap scoring, roadmap generation, and job search, consumed by a Next.js/TypeScript frontend, an interactive CLI, and any MCP-compatible agent (Claude Desktop, Claude Code).

| Module | What it does |
|---|---|
| **RAG Chat** | Retrieves relevant chunks from an indexed PDF (career guide or user-uploaded doc) via ChromaDB + sentence-transformer embeddings, and answers with cited context. Falls back to un-grounded chat when retrieval isn't needed. |
| **Resume Analyzer** | Parses PDF/DOCX/TXT resumes, extracts skills, and produces an ATS-style summary with strengths, gaps, and suggested target roles. |
| **Skill Gap Matrix** | Diffs a candidate's skills against a target role's expected skill set, returning a readiness tier (high/medium/low) per skill. |
| **Learning Roadmap** | Generates a milestone-based curriculum scoped to a configurable duration and focus skills. |
| **Job Matcher** | Live search via the Adzuna API, with a bundled dataset fallback when no API credentials are configured. |
| **MCP Server** | Exposes the same tools over stdio so external agents (Claude Desktop/Code) can call them directly. |

## Architecture

```
┌───────────────────────────────┐
│  Next.js 16 / React 19 (3000) │
└───────────────┬───────────────┘
                │ REST (CORS)
                ▼
┌───────────────────────────────┐
│  FastAPI backend (8000)       │
│  backend/server.py            │
├───────────────────────────────┤
│  rag_service.py    – conversation + retrieval orchestration
│  rag_pipeline.py   – PDF chunking, embeddings, Chroma store
│  career_tools.py   – resume / skill-gap / roadmap / job logic
│  resume_pipeline.py– multi-format resume parsing
│  llm_providers.py  – Groq / Gemini adapter
│  mcp_server.py     – MCP tool exposure (stdio)
│  main.py           – terminal CLI
│  config.py         – env-driven settings, validated eagerly
│  errors.py         – exceptions + retry/backoff
│  tracing.py        – LangSmith tracing
│  evaluation.py     – eval harness
└───────────────────────────────┘
```

**RAG data flow:** PDF upload → `PyPDFLoader` → `RecursiveCharacterTextSplitter` → `sentence-transformers/all-MiniLM-L6-v2` embeddings → persisted Chroma store. On query, the LLM first decides whether retrieval is needed; if so, a similarity search + relevance-threshold filter builds the grounded context before generation.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full diagram and directory breakdown.

## Tech Stack

- **Backend:** Python 3.10+, FastAPI, Uvicorn, LangChain, ChromaDB, sentence-transformers, Groq / Google Gemini
- **Frontend:** Next.js 16, React 19, TypeScript
- **Observability:** LangSmith tracing (optional)
- **Interfaces:** REST API, terminal CLI, MCP server (stdio)
- **Testing:** pytest (87 tests), ESLint

## Project Layout

```
career-advisor/
├── backend/            # Python package: server, RAG, tools, CLI, MCP
│   └── requirements.txt
├── frontend/            # Next.js 16 web app (src/app, src/components, src/lib)
├── tests/                # Backend unit & integration tests
├── scripts/              # Utility scripts (e.g. default guide builder)
├── app.py                # Unified CLI runner (api / cli / mcp / doctor / status)
├── pyproject.toml        # Project + pytest/ruff/black config
├── package.json           # Root npm script wrapper (dev/build/preview)
└── .env.example
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js (for the frontend)
- A Groq or Google Gemini API key

### 1. Install & configure

```bash
pip install -r backend/requirements.txt
python app.py setup          # scaffolds .env from .env.example
# edit .env — set GROQ_API_KEY (or GOOGLE_API_KEY)
```

On first run, the bundled `Career_Advisor_Guide_2025.pdf` (or any PDF you upload via the Knowledge & RAG Hub) is chunked, embedded, and persisted to `CHROMA_PERSIST_DIR` (default `chroma_db/`, gitignored). Subsequent runs reuse the index; delete the directory to force a rebuild.

### 2. Verify configuration

```bash
python app.py doctor
```

Runs a live preflight in request order — config → LLM provider call → embeddings → Chroma → end-to-end RAG answer → job search — printing PASS/FAIL/SKIP with actionable fixes per stage. Exits non-zero on failure, so it's CI-friendly.

### 3. Run

```bash
python app.py api    # FastAPI backend      → http://127.0.0.1:8000
npm run dev           # Next.js frontend     → http://localhost:3000
python app.py cli     # Terminal CLI
python app.py mcp     # MCP server (stdio)
python app.py status  # Environment diagnostics
```

### 4. Test

```bash
python -m pytest      # backend: 87 tests
npm run lint            # ESLint
npm run build            # Production build
```

> `npm install` prints an `eslint@9.x` deprecation warning — expected. `eslint-config-next@16.3.3` currently bundles a version of `eslint-plugin-react` that breaks under ESLint 10, so the project pins ESLint 9 until upstream ships compatibility. See the header comment in `frontend/eslint.config.mjs`.

## Configuration Reference

All settings are centralized in `backend/config.py` and validated eagerly at startup — missing or malformed required values fail fast with an actionable message rather than mid-request. Key variables (full list in `.env.example`):

| Variable | Default | Notes |
|---|---|---|
| `LLM_PROVIDER` | `groq` | `groq` or `gemini` |
| `GROQ_API_KEY` / `GOOGLE_API_KEY` | — | One required, matching `LLM_PROVIDER` |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `500` / `50` | RAG chunking |
| `MAX_CONTEXT_DOCS` | `3` | Chunks injected per query |
| `RELEVANCE_SCORE_THRESHOLD` | `0.35` | Minimum similarity to include a chunk |
| `CHROMA_PERSIST_DIR` | `chroma_db` | Vector store location (gitignored) |
| `AUTO_INDEX_DEFAULT_DOCUMENT` | `true` | Index the default guide on first run |
| `STRICT_CAREER_ONLY` | `true` | Refuse out-of-scope questions |
| `MAX_UPLOAD_SIZE_MB` / `MAX_RESUME_SIZE_MB` | `15` / `10` | Upload limits |
| `MAX_HISTORY_TURNS` | `6` | Conversation memory window |
| `LLM_REQUEST_TIMEOUT_SECONDS` / `LLM_MAX_RETRIES` | `30` / `3` | External call resilience |
| `LANGSMITH_TRACING` | `false` | Enable LangSmith tracing/eval |
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | — | Optional; live job search vs. bundled dataset |

## API

FastAPI backend at `http://127.0.0.1:8000`, OpenAPI docs at `/docs`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/status` | Health / diagnostics |
| `GET` | `/api/history` | List conversation history |
| `POST` | `/api/history` | Create history entry |
| `DELETE` | `/api/history/{item_id}` | Delete a history entry |
| `DELETE` | `/api/history` | Clear all history |
| `POST` | `/api/chat` | RAG-grounded chat turn |
| `POST` | `/api/chat/clear` | Reset chat session |
| `POST` | `/api/resume/upload` | Upload a resume file |
| `POST` | `/api/resume/analyze` | Run resume analysis |
| `POST` | `/api/skill-gap` | Compute skill-gap matrix |
| `POST` | `/api/roadmap` | Generate a learning roadmap |
| `POST` | `/api/jobs/search` | Search jobs (live or fallback dataset) |
| `POST` | `/api/documents/upload` | Upload & index a reference PDF |

## MCP Integration

Register the server with Claude Desktop (or any MCP client) via `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "career-advisor": {
      "command": "python",
      "args": ["-m", "backend.mcp_server"]
    }
  }
}
```

## Responsive Design

The frontend is verified at 375/393/412/768px with no horizontal overflow: below 900px the sidebar collapses into an off-canvas drawer, grids drop to a single column, tap targets meet the 44px minimum, and inputs use 16px font to prevent iOS Safari zoom-on-focus.

## Known Limitations

- **No authentication or authorization.** `/api/*` routes are unauthenticated; CORS is the only access control. Do not expose the FastAPI backend to the public internet without adding an auth layer.
- **Groq API rate limits.** The default `LLM_PROVIDER=groq` is subject to Groq's per-key rate/token limits (varies by tier). `LLM_MAX_RETRIES` / `LLM_REQUEST_TIMEOUT_SECONDS` add exponential backoff on transient failures, but sustained high-volume or concurrent usage can still exhaust quota and return `LLMError`. Switch `LLM_PROVIDER=gemini` or raise your Groq tier for production load.
- **No request-level rate limiting.** The backend itself doesn't throttle incoming traffic — abusive or bursty clients hit the LLM provider directly.
- **Single-writer vector store.** ChromaDB is used as a local persisted store (`CHROMA_PERSIST_DIR`); it isn't designed for concurrent writes from multiple backend instances.
- **Job search fallback is static.** Without `ADZUNA_APP_ID`/`ADZUNA_APP_KEY`, `/api/jobs/search` serves a small bundled dataset rather than live listings.

## Contributing

1. Fork and branch from `main`.
2. Run `python -m pytest` and `npm run lint` before opening a PR.
3. Keep formatting consistent with `black`/`ruff` (config in `pyproject.toml`).
