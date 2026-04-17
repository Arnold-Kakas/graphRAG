# GraphRAG — Multi-Topic Knowledge Graph Web App

An end-to-end GraphRAG web application that ingests your documents, extracts entities and relationships using LLMs, builds a queryable knowledge graph, and renders it as an interactive visualization.

## Overview

Drop documents into a topic folder, trigger the pipeline from the UI, and query the resulting knowledge graph in natural language. Supports OpenAI and any OpenAI-compatible local model (LM Studio, Ollama, etc.).

## Tech Stack

| Layer | Tools |
|-------|-------|
| LLM / RAG | LlamaIndex, OpenAI-compatible API |
| Document parsing | PyMuPDF, python-docx, Trafilatura, BeautifulSoup |
| Graph analysis | NetworkX, Graspologic (Leiden community detection) |
| Visualization | D3.js v7 |
| Backend | FastAPI, Uvicorn |
| Data | Pandas, Pydantic |

## Project Structure

```
graphrag/
├── app/
│   ├── main.py           # FastAPI routes
│   ├── config.py         # Settings (loaded from .env)
│   ├── parser.py         # Document parser (PDF, DOCX, HTML, TXT, MD, CSV)
│   ├── pipeline.py       # GraphRAG pipeline (extraction, clustering, summarization)
│   ├── query_engine.py   # Query engine
│   ├── graph_store.py    # Graph persistence
│   ├── task_manager.py   # Background task management
│   ├── models.py         # Pydantic models
│   ├── templates/        # Jinja2 HTML templates
│   └── static/           # CSS and JS assets
├── raw/                  # Input documents, organized by topic (raw/<topic>/)
├── graphs/               # Generated graph data (persisted across restarts)
├── Dockerfile
├── docker-compose.yml
└── .env                  # API keys and settings (not committed)
```

## Prerequisites

- Docker and Docker Compose
- An OpenAI API key **or** a local LLM running an OpenAI-compatible API (LM Studio, Ollama)

## Setup

1. **Clone the repo:**
   ```bash
   git clone <repo-url>
   cd graphRAG
   ```

2. **Create your `.env` file:**
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` with your settings.

3. **Configure your LLM provider** in `.env`:

   **Option A — OpenAI:**
   ```env
   OPENAI_API_KEY=sk-...
   EXTRACTION_MODEL=gpt-4o-mini
   QUERY_MODEL=gpt-4o
   ```

   **Option B — Local model (LM Studio):**
   ```env
   OPENAI_API_KEY=not-needed
   LLM_BASE_URL=http://host.docker.internal:1234/v1
   EXTRACTION_MODEL=your-model-name
   QUERY_MODEL=your-model-name
   LLM_CONTEXT_WINDOW=8192
   ```

   **Option C — Local model (Ollama):**
   ```env
   OPENAI_API_KEY=not-needed
   LLM_BASE_URL=http://host.docker.internal:11434/v1
   EXTRACTION_MODEL=your-model-name
   QUERY_MODEL=your-model-name
   LLM_CONTEXT_WINDOW=8192
   ```

   > **Note for Docker:** Use `host.docker.internal` to reach services on your host machine. If that doesn't work on Linux, use your LAN IP (e.g. `http://192.168.1.100:1234/v1`) instead.

4. **Add your documents** — create a folder under `raw/` for each topic and place your files inside:
   ```
   raw/
   └── my-topic/
       ├── document1.pdf
       ├── article.html
       └── notes.txt
   ```
   Supported formats: `.pdf`, `.docx`, `.html`, `.htm`, `.txt`, `.md`, `.csv`

5. **Build and run:**
   ```bash
   docker-compose up --build
   ```

6. **Open the app** at `http://localhost:8000`

## Usage

1. Select a topic from the dropdown
2. Click **Build Graph** to run the pipeline (entity extraction, community detection, summarization)
3. Explore the interactive graph visualization
4. Ask questions in natural language via the chat interface

### Adding documents to an existing topic

Just drop new files into `raw/<topic>/` and click **Build Graph** again. The pipeline runs **incrementally** — it compares each file's last-modified time against the previous build and only re-processes new or changed files. Unchanged files are skipped, saving significant LLM costs on large topic folders.

After the incremental run, community detection and summaries are regenerated over the full (merged) graph.

#### Incremental build limitations

- **Deleted files** — nodes extracted from a deleted file remain in the graph until you do a full rebuild. The graph has no record of which file each node came from.
- **Modified files** — re-extracted and merged in; the old nodes from that file stay too (LlamaIndex deduplicates by entity name where possible, but duplicates can occur for substantially rewritten content).

To force a complete rebuild from scratch, tick the **Full rebuild** checkbox next to the Build Graph button before triggering the build.

## Pipeline Parameters

Tunable via `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_DOCUMENTS` | 50 | Max documents processed per build (full builds only) |
| `NUM_WORKERS` | 4 | Parallel LLM workers for extraction |
| `MAX_PATHS_PER_CHUNK` | 20 | Max entity-relationship triplets per document chunk |
| `MAX_CLUSTER_SIZE` | 10 | Max nodes per community cluster |
| `LLM_CONTEXT_WINDOW` | 8192 | Context window size (set to your model's actual limit) |
