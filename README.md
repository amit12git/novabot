# NovaBot — Self-Hosted RAG Chatbot Platform

Ask questions about your own documents. Upload a PDF, get grounded answers with source citations — running entirely on your machine, with an optional switch to OpenAI for faster responses.

Built as a microservices platform: every component runs in its own container, orchestrated with Docker Compose.

## Architecture

```
                        ┌─────────────────────────────┐
                        │        Web UI  (nginx)      │  :3000
                        │   React chat + doc upload   │
                        └──────┬───────────────┬──────┘
                        /api/* │               │ /ingest/*
                               ▼               ▼
              ┌────────────────────┐   ┌────────────────────┐
              │   Query Service    │   │ Ingestion Service  │  :8100
              │  (FastAPI)  :8000  │   │     (FastAPI)      │
              │                    │   │                    │
              │ Retrieve→Augment→  │   │ Load → Chunk →     │
              │ Generate + Cache   │   │ Embed → Store      │
              └──┬────┬────┬───┬───┘   └─────────┬──────────┘
                 │    │    │   │                 │
                 ▼    ▼    │   ▼                 ▼
          ┌────────┐┌─────┐│ ┌──────────────────────┐
          │Postgres││Redis││ │       Qdrant          │  :6333
          │ chat   ││cache││ │   vector database     │
          │history │└─────┘│ └──────────────────────┘
          └────────┘       ▼
                    LLM provider (switchable)
                    Ollama (local) / OpenAI API
```

**Query path (real-time):** question → cache check → vector similarity search (Qdrant) → prompt assembly with retrieved context → LLM generation → answer + sources, stored in chat history.

**Indexing path:** document upload → text extraction (pypdf) → overlapping chunking → embedding (fastembed, all-MiniLM-L6-v2) → vector upsert to Qdrant.

## Features

- **Document upload from the browser** — PDF, TXT, and Markdown
- **Grounded answers with citations** — every answer shows which document and similarity score backed it; the model is instructed to say "I don't know" rather than invent
- **Similarity threshold filtering** — irrelevant questions short-circuit before ever reaching the LLM
- **Answer caching (Redis)** — repeated questions return in milliseconds instead of seconds, with cache status and response time shown in the UI
- **Switchable LLM provider** — local Ollama (free, private) or OpenAI, chosen by one env var, no code change
- **Persistent chat history (PostgreSQL)** — survives restarts, per-session
- **One-command startup** — `docker compose up`

## Prerequisites

- **Docker Desktop** (or another Docker runtime) — [docker.com](https://www.docker.com/products/docker-desktop/)
- **Ollama** (for the free local LLM option) — [ollama.com](https://ollama.com)
  ```bash
  # macOS
  brew install ollama
  ollama pull llama3.2
  ```
  Skip this if you'll only use OpenAI.
- ~4GB free RAM for the containers, plus whatever your Ollama model needs

## Quick Start

```bash
# 1. Clone
git clone <your-repo-url> novabot
cd novabot

# 2. Configure
cp .env.example .env
# Edit .env if you want OpenAI — otherwise the Ollama defaults work as-is

# 3. Launch everything
docker compose up --build -d

# 4. Open the app
open http://localhost:3000
```

First build takes a few minutes (image downloads, dependency installs). Subsequent starts are seconds.

**Then:** click **Upload document**, pick a PDF, wait for "indexed — N chunks", and ask a question about it.

## Configuration

All settings live in `.env` (copied from `.env.example`, never committed):

| Variable         | Default  | Purpose                                  |
| ---------------- | -------- | ---------------------------------------- |
| `LLM_PROVIDER`   | `ollama` | `ollama` (local, free) or `openai`       |
| `OPENAI_API_KEY` | —        | Required only when `LLM_PROVIDER=openai` |

Switching provider is a one-line edit plus:

```bash
docker compose up -d query-service
```

Additional tuning knobs (set in `docker-compose.yml` under `query-service` → `environment`):

| Variable         | Default    | Purpose                                           |
| ---------------- | ---------- | ------------------------------------------------- |
| `OLLAMA_MODEL`   | `llama3.2` | Any model you've pulled (`ollama pull <model>`)   |
| `MIN_SIMILARITY` | `0.10`     | Retrieval threshold; raise for stricter relevance |
| `TOP_K`          | `3`        | Chunks retrieved per question                     |

## Service Endpoints

| Service          | URL                             | Notes                          |
| ---------------- | ------------------------------- | ------------------------------ |
| Chat UI          | http://localhost:3000           | Main app                       |
| Query API        | http://localhost:8000/docs      | Interactive API docs (FastAPI) |
| Ingestion API    | http://localhost:8100/docs      | Upload + document list         |
| Qdrant dashboard | http://localhost:6333/dashboard | Browse your vectors            |

Useful API calls:

```bash
# What documents are indexed?
curl http://localhost:8100/documents

# Ask a question via API
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?", "session_id": "cli"}'

# Conversation history for a session
curl http://localhost:8000/history/cli
```

## Common Operations

```bash
# Watch the query service work (timing, cache hits)
docker compose logs -f query-service

# Clear the answer cache (force fresh LLM generations)
docker compose exec redis redis-cli FLUSHALL

# Bulk-index documents from a folder (host-side, needs Python venv)
# Put files in services/ingestion-service/data/documents/ then:
cd services/ingestion-service && python src/ingest.py

# Stop everything (data persists in volumes)
docker compose down

# Stop everything AND delete all data (vectors, chat history)
docker compose down -v
```

## Project Structure

```
novabot/
├── docker-compose.yml           # Full-stack orchestration
├── .env.example                 # Configuration template
├── services/
│   ├── ingestion-service/       # Upload API: load → chunk → embed → store
│   │   └── src/
│   │       ├── main.py          # FastAPI: /upload, /documents
│   │       ├── loaders/         # PDF / TXT extraction
│   │       ├── chunker.py       # Overlapping word-based chunking
│   │       └── embedder.py      # fastembed + Qdrant client
│   └── query-service/           # Chat API: retrieve → augment → generate
│       └── src/
│           ├── main.py          # FastAPI: /chat, /history
│           ├── rag.py           # The RAG pipeline
│           ├── llm.py           # Provider abstraction (Ollama / OpenAI)
│           ├── cache.py         # Redis answer cache
│           ├── db.py            # PostgreSQL chat history
│           └── config.py        # Env-based configuration
└── web-ui/                      # React chat frontend, served by nginx
```

## How It Answers a Question

1. Question arrives at `/chat`; saved to chat history
2. **Cache check** — exact match (normalized) returns instantly
3. **Retrieve** — the question is embedded and Qdrant returns the top-k most similar chunks; anything below the similarity threshold is dropped
4. **Guard** — if nothing relevant survives, respond "no relevant information" without calling the LLM
5. **Augment** — retrieved chunks are assembled into a prompt that instructs the model to answer _only_ from the provided context
6. **Generate** — the prompt goes to the configured LLM provider
7. Answer + sources returned, cached, and saved to history

## Troubleshooting

**"Couldn't reach the query service"** — check `docker ps`; all containers up? `docker compose logs query-service` for the error.

**Answers are slow** — local Ollama speed depends on your hardware. Try a smaller model (`ollama pull llama3.2:1b`, update `OLLAMA_MODEL`), or switch to OpenAI. Repeated questions are always fast (cache).

**Upload fails** — files must be .pdf/.txt/.md and under 20MB. `docker compose logs ingestion-service` shows parse errors.

**The model answers from general knowledge instead of my documents** — check the sources shown under the answer. If none appear, retrieval found nothing relevant; the question may not match your indexed content.

**Ollama connection refused** — Ollama must be running on the host (`ollama serve`) with the model pulled. Containers reach it via `host.docker.internal`.

## Roadmap / Ideas

- Streaming responses (token-by-token answers)
- Semantic cache (similar-but-not-identical questions hit the cache)
- Delete/re-index documents from the UI
- Prometheus metrics + Grafana dashboard (latency, cache hit rate)
- Split retrieval and generation into dedicated services

## License

MIT — see [LICENSE](LICENSE).
