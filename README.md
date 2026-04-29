# GraphRAG Explorer

An end-to-end GraphRAG web app that ingests your documents, extracts entities and relationships with an LLM, builds a queryable knowledge graph with community detection, and renders it as an interactive D3 visualization with a streaming chat interface.

**Runs fully locally** with LM Studio / Ollama, or on cloud APIs (OpenAI, Anthropic, Gemini).

> **New to GraphRAG Explorer?** The **[User Guide](USERGUIDE.md)** covers use cases, every feature explained in plain language, deployment options, and tips for adding content.

---

## Features

### Knowledge graph build

- **Hybrid 2-call extraction pipeline** - each document is compressed into a rich summary in one call, then entities and relationships are extracted from the summary in a second call. 2 LLM calls per document total, independent of length. Typically 4–6× faster than chunk-level extraction.
- **Multi-provider LLM support** - OpenAI, Anthropic Claude, Google Gemini, LM Studio, Ollama, or any OpenAI-compatible custom endpoint. Switchable per-request from the UI.
- **Three-layer deduplication:**
  1. Prompt-level naming rules (full names, American English, consistent casing).
  2. LLM semantic entity resolver that scans the full entity list and proposes synonym merges.
  3. Rule-based normalization (spelling variants, parenthetical acronyms).
- **Explicit alias system** - define per-topic synonyms in `ontology.json` (e.g. `{"Facebook": "Meta"}`) for hard merges the LLM might miss.
- **Leiden community detection** with LLM-generated 3–5 sentence summaries per cluster.
- **Per-node provenance** - every node tracks the list of source files it was extracted from. Visible in the node detail modal.
- **Build context / focus prompts** - before a full rebuild, describe what to prioritize (e.g. *"focus on ROI metrics and channel attribution"*); the context is saved and used in the extraction prompt.
- **Incremental builds** - re-running Build Graph only processes files whose mtime changed.
- **Auto-cleanup on file removal** - deleted files have their contributed nodes and edges pruned automatically on the next incremental build (nodes whose `sources` list becomes empty are removed; nodes that were also mentioned in surviving files keep their remaining provenance).
- **Thinking-mode support** - handles `<think>...</think>` output from Qwen3, DeepSeek-R1, and similar reasoning models without breaking JSON extraction.
- **Merge entities as a standalone task** — LLM-based synonym resolution runs separately from the build so you control timing. Learned merges are saved to `learned_aliases.json` and reapplied automatically on future builds — you only pay the LLM cost once per synonym pair.

### Chat / query engine

- **Two-phase community querying** - keyword + entity-index prefilter caps candidate communities at 15, parallel per-community relevance check, final synthesis pass.
- **Streaming responses** - NDJSON server-sent events render tokens as they arrive. Phase-1 progress is shown as a pulsing placeholder.
- **Two answer modes:**
  - *Graph only* - strictly grounded in the graph. The LLM is instructed to reply "Not in the graph." if evidence is insufficient, and a post-hoc filter drops uncited sentences from the streamed answer.
  - *Graph + AI knowledge* - LLM may fill gaps; output is split into *From the knowledge graph* and *From AI knowledge* sections.
- **Interactive citations** - entities in the answer are rendered as `[[Entity Name]]` chips that highlight and pan to the node in the graph when clicked.
- **Source transparency** - every answer shows which community clusters contributed, expandable to view the cluster summary text.
- **Pin answers to the topic** - useful Q&A pairs persist in `pinned_answers.json` and appear in the sidebar; click to replay any pinned answer back into the chat.
- **Optional embeddings pre-filter** - set `EMBEDDINGS_ENABLED=true` to rank communities by cosine similarity in addition to keyword overlap. Useful past ~200 communities, where keyword matching starts missing semantically related clusters. Cached per-summary on disk so subsequent queries pay only the query-encoding cost.

### Graph visualization

- **D3 force-directed layout** - pan, zoom, drag, node colour by entity type, size by degree.
- **Sidebar controls** - link distance, node charge, edge-label density threshold.
- **Legend with type filtering** - click a type to hide/show those nodes.
- **Index-aware search dropdown** - matches on label, type, and description; ranks by where the match lands (label > type > description) and breaks ties by node degree, so well-connected hubs surface first. Each result shows its degree and cluster ID.
- **Obsidian-style detail panel** - click a node to see its description, edges, source files, and community membership.
- **Wikipedia-style wiki articles** - double-click a node to generate a 3–5 paragraph encyclopedic article synthesized from its description, relationships, and community context. Cached per node after first generation.
- **Obsidian vault export** - sidebar button downloads a zip with one `.md` per entity (YAML frontmatter, inline `[[wiki links]]` to neighbours, cluster context, cached wiki article). Drop the unzipped folder into an Obsidian vault and the graph view + backlinks light up automatically.
- **Blog post generation** — sidebar button opens a dialog to set your angle, outline, and length target. Generates a structured blog post grounded in community summaries and entity relationships, with optional interactive Chart.js charts and source citations as footnotes. Export as raw Markdown or standalone HTML.

### UX niceties

- **LLM indicator in navbar** - shows the active provider/model and whether it's coming from browser session or server `.env`.
- **Light / dark theme toggle.**
- **Per-session LLM override** - Settings gear opens a modal to set API key, base URL, and model names; stored in `sessionStorage` only (never sent to disk, never persisted across tab closes).
- **Graceful fallbacks** - stale `graph_data.json` is regenerated on demand; legacy pickles load without provenance; `entity_index.json` rebuilds from the graph if missing.

---

## Quick start (Docker)

```bash
git clone <repo-url>
cd graphRAG
cp .env.example .env
# Edit .env - see "Configure your LLM" below
docker compose up --build
```

Open <http://localhost:8000>.

Drop documents into `raw/<topic-name>/`, select the topic in the UI, click **Build Graph**.

Supported formats: `.pdf`, `.docx`, `.html`, `.htm`, `.txt`, `.md`, `.csv`.

---

## Configure your LLM

`.env` options:

**OpenAI:**
```env
OPENAI_API_KEY=sk-...
EXTRACTION_MODEL=gpt-4o-mini
QUERY_MODEL=gpt-4o
```

**LM Studio (local):**
```env
OPENAI_API_KEY=not-needed
LLM_BASE_URL=http://host.docker.internal:1234/v1
EXTRACTION_MODEL=your-model-name
QUERY_MODEL=your-model-name
LLM_CONTEXT_WINDOW=8192
LLM_MAX_TOKENS=8192
```

**Ollama (local):**
```env
OPENAI_API_KEY=not-needed
LLM_BASE_URL=http://host.docker.internal:11434/v1
EXTRACTION_MODEL=your-model-name
QUERY_MODEL=your-model-name
```

> **Docker networking:** `host.docker.internal` resolves to the host on Docker Desktop (Windows/Mac). On Linux add `extra_hosts: ["host.docker.internal:host-gateway"]` to `docker-compose.yml`, or use your LAN IP directly.
>
> **LM Studio binding:** "Serve on local network" must be enabled, and the server must be **started** (the toggle configures binding; the green Start button actually launches it).

**Per-session override:** the Settings gear in the app lets you set API key / model / base URL for the current browser tab only. These take precedence over `.env`, are stored in `sessionStorage`, and are never written to disk. The navbar indicator shows which source is active (`Provider - Model`, coloured when the browser session is overriding).

---

## Tunable parameters (`.env`)

| Variable | Default | Effect |
|---|---|---|
| `NUM_WORKERS` | 4 | Extraction parallelism. Set to 1 for slow local models. |
| `MAX_DOCUMENTS` | 50 | Hard cap per full build. |
| `MAX_PATHS_PER_CHUNK` | 20 | Max entity-relationship triplets per document (hybrid pipeline = per document, not per chunk). Raise for long dense papers. |
| `MAX_CLUSTER_SIZE` | 10 | Leiden cluster cap. Larger → fewer, broader communities. |
| `LLM_CONTEXT_WINDOW` | 8192 | Must match the context the model is actually loaded with (check LM Studio's model settings). |
| `LLM_MAX_TOKENS` | 4096 | Max output tokens. Raise to 8192–16384 for thinking models whose `<think>` block consumes the budget before JSON. |
| `LLM_REQUEST_TIMEOUT` | 300 | Seconds. Increase for large local models. |
| `EMBEDDINGS_ENABLED` | `false` | Opt-in semantic community pre-filter. Requires `pip install sentence-transformers` (pulls torch). |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Sentence-transformers model id used when embeddings are enabled. `BAAI/bge-small-en-v1.5` and `intfloat/e5-small-v2` are good drop-ins. |

---

## Project structure

```
graphRAG/
├── app/
│   ├── main.py            # FastAPI routes, query engine cache, streaming endpoint
│   ├── config.py          # Pydantic settings from .env
│   ├── models.py          # API schemas, OntologyConfig, LLMConfig
│   ├── parser.py          # Per-format text extraction
│   ├── pipeline.py        # build_topic_graph: hybrid extraction + dedup + communities
│   ├── graph_store.py     # GraphRAGStore, upsert, dedup, wiki generation, persistence
│   ├── query_engine.py    # Two-phase query + streaming + citation enforcement
│   ├── task_manager.py    # Background build threads, make_llm() factory
│   ├── templates/         # Jinja HTML
│   └── static/
│       ├── css/style.css
│       └── js/
│           ├── app.js     # Topic list, build, chat, settings modal
│           └── graph.js   # D3 force layout, node/edge interaction, wiki modal
├── raw/<topic>/           # Source documents (mounted into container)
├── graphs/<topic>/        # Persisted graph artifacts (mounted into container)
├── USERGUIDE.md           # End-user feature guide and deployment docs
├── log.md                 # Change log
└── docker-compose.yml
```

### Per-topic persisted files (`graphs/<topic>/`)

| File | Contents |
|---|---|
| `store.pkl` | Full `GraphRAGStore` pickle - ground truth for nodes, edges, community summaries. |
| `communities.json` | `{community_id: summary}` - one paragraph per Leiden cluster. |
| `entity_wikis.json` | Cache of on-demand Wikipedia articles per node. |
| `entity_index.json` | Flat entity catalog used for prompt injection and search. |
| `graph_data.json` | D3-ready `{nodes, links, communities}`. Regenerated lazily if stale. |
| `build_meta.json` | Build stats: node/edge/community counts, timestamp. |
| `manifest.json` | `{file: mtime}` for incremental build diffing. |
| `ontology.json` | Entity types, relation types, and aliases used for this build. |
| `build_context.txt` | Last focus/purpose prompt used. Pre-filled when you re-open the build modal. |
| `pinned_answers.json` | List of `{id, question, answer, mode, sources, created_at}` items pinned from chat. |
| `community_embeddings.json` | Cached community summary embeddings (only when `EMBEDDINGS_ENABLED=true`). |
| `learned_aliases.json` | `{alias: canonical}` cache of LLM-discovered synonym merges. Reapplied on every subsequent build, including incremental and removal-only, so resolver work isn't repeated. |

---

## Architecture

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for the full data-flow and module-responsibility breakdown.

Short version:

```
raw/<topic>/*.{pdf,docx,html,txt,md,csv}
  → parser: per-format text extraction
  → pipeline:
      → for each doc (parallel, NUM_WORKERS):
          → _summarise_document   (1 LLM call)
          → GraphRAGExtractor     (1 LLM call, structured or plain-text JSON)
          → upsert_nodes_merge    (provenance-aware merge)
      → resolve_entities          (LLM semantic synonym merge)
      → deduplicate_nodes         (rule-based + alias application)
      → build_communities         (Leiden + per-cluster LLM summary)
      → build_index, save
  → query_engine:
      → keyword + entity-index prefilter (top 15 communities)
      → parallel per-community relevance checks
      → aggregate with citation enforcement
      → stream NDJSON to browser
```

---

## Incremental vs full build

- **Incremental** (default) - only files whose `mtime` changed since the stored `manifest.json` are re-extracted. Removed files have their contributions pruned. Communities are regenerated over the merged graph.
- **Full rebuild** - tick the checkbox before clicking Build. Discards the existing graph and re-extracts every file from scratch. Use after ontology changes, large ingest quality issues, or to force reinterpretation under a new build context.

---

## License

MIT. See `LICENSE`.

---

## Contributing / feedback

The change log lives in `log.md`. Each entry uses the format:

```
### [Type]: [Short name]
**Purpose:** Why this change - the problem it solves or goal it achieves.
**Technical implementation:** What was changed and how - files, methods, key decisions.
```

Issues and PRs welcome.
