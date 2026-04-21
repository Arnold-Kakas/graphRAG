# Architecture

This document covers the internal design of GraphRAG Explorer — the data flow, module responsibilities, persistence layout, and the key architectural decisions. See the main [README](../README.md) for user-facing features and setup.

---

## Data flow

```
┌────────────────────────────────────────────────────────────────────────┐
│ raw/<topic>/*.{pdf,docx,html,htm,txt,md,csv}                           │
└────────────────────┬───────────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│ parser.py — per-format text extraction                                 │
│   PyMuPDF · python-docx · Trafilatura · BeautifulSoup                  │
└────────────────────┬───────────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│ pipeline.py — build_topic_graph()                                      │
│                                                                        │
│  Incremental guard:                                                    │
│    stored_mtimes ← manifest.json                                       │
│    removed_files ← stored - current                                    │
│    if removed_files: GraphRAGStore.remove_source_references()          │
│    docs_to_process ← files whose mtime > stored                        │
│                                                                        │
│  For each doc in parallel (NUM_WORKERS):                               │
│    summary       ← _summarise_document(text, llm)        [1 LLM call]  │
│    entities,rels ← GraphRAGExtractor.extract(summary)    [1 LLM call]  │
│    graph_store.upsert_nodes_merge(entities)                            │
│    graph_store.upsert_relations(rels)                                  │
│                                                                        │
│  resolve_entities(llm)    — LLM semantic synonym merge                 │
│  deduplicate_nodes()      — rule-based + alias-based merge             │
│  build_communities(llm)   — Leiden clustering + per-cluster summary    │
│  build_index()            — flat entity catalog                        │
│  save(topic_dir)          — pickle + JSON artefacts                    │
└────────────────────┬───────────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│ query_engine.py — GraphRAGQueryEngine                                  │
│                                                                        │
│  Phase 1 — candidate selection:                                        │
│    keywords  ← stopword-filtered query terms                           │
│    score     ← keyword hits in summary + hits in community entities    │
│    top 15    → parallel per-community relevance check                  │
│    _NO_RELEVANT_INFO sentinel filters out empty answers                │
│                                                                        │
│  Phase 2 — aggregation:                                                │
│    build_aggregate_prompt(mode)                                        │
│      mode=graph   : strict grounding, "Not in the graph" fallback      │
│      mode=extended: two-section "graph + AI knowledge"                 │
│    citation rule  : require [[Entity Name]] around every entity        │
│    astream_complete → NDJSON token stream                              │
│    mode=graph: post-hoc strip of uncited claim sentences               │
│                   (emits a `replace` event if altered)                 │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Module responsibilities

| Module | Responsibility |
|---|---|
| `app/main.py` | FastAPI routes; topic discovery; query-engine cache (`_query_engines` dict — bypassed when a per-request LLM config is supplied); streaming endpoint `/api/topics/{topic}/query/stream`; lazy regeneration of stale `graph_data.json`. |
| `app/config.py` | Pydantic `Settings` loaded from `.env`. Everything tunable lives here. |
| `app/models.py` | API request/response schemas; `OntologyConfig` (entity types, relation types, aliases); `LLMConfig` (per-request, browser-provided, never persisted). |
| `app/parser.py` | Per-format text extraction. |
| `app/pipeline.py` | `build_topic_graph()` orchestrator. Hybrid 2-call-per-doc pipeline. Incremental build via `manifest.json` mtime diffing. Auto-cleanup on file removal. |
| `app/graph_store.py` | `GraphRAGStore(SimplePropertyGraphStore)`: provenance-aware upsert, entity resolver, deduplication, community detection, on-demand wiki generation, source-reference cleanup, save/load, D3 export, entity index. |
| `app/query_engine.py` | Two-phase query engine. Streaming and non-streaming paths. Citation-enforcement post-filter for graph-only mode. |
| `app/task_manager.py` | `TaskManager` runs builds in background threads; `make_llm()` factory returns `OpenAI` for the OpenAI provider and `OpenAILike` (bypasses model-name validation) for everything else. |
| `app/static/js/app.js` | Topic list, build trigger, streaming chat consumer, Settings modal (sessionStorage only), Build Context modal, LLM navbar indicator, citation chip click handler. |
| `app/static/js/graph.js` | D3 force layout, node/edge interaction, detail panel, wiki modal, `window.graphSelectByLabel` API for chat citations. |

---

## Key architectural decisions

### Hybrid 2-call extraction pipeline

The upstream LlamaIndex GraphRAG pipeline makes one extraction call per chunk (often 10–20 per document). Each call sees only a chunk's worth of context, so cross-page relationships get lost.

Replaced with:

1. **`_summarise_document(text, llm)`** — one call over the entire document (or the first `LLM_CONTEXT_WINDOW * 3` characters). Prompt instructs the model to preserve every entity, relationship, fact, and metric.
2. **`GraphRAGExtractor.extract(summary)`** — one call on the summary producing structured JSON.

Total: 2 calls per document regardless of length. Typically 4–6× faster than chunk-level extraction.

Downside: long documents that exceed the summary budget lose tail content. Mitigated by raising `LLM_CONTEXT_WINDOW` on LM Studio / Ollama, and by the summary prompt being aggressive about compression.

### Structured vs plain-text extraction

`GraphRAGExtractor.extract()` has two paths:

1. **`astructured_predict`** — function-calling / JSON-schema mode. Fast, clean output, but fails on thinking models that emit `<think>...</think>` before the JSON.
2. **`_acomplete_extract`** — plain-text completion, regex-extract the first balanced `{...}` block.

The structured path is tried first. On `AttributeError`, `"0 tool calls"`, or `"could not be parsed"`, it falls back to plain-text. For Qwen3-style reasoning models, users should tick **Enable thinking** in the UI to go straight to the plain-text path and avoid the retry cost.

### Three-layer deduplication

Running the LLM at extraction time produces duplicates: "Marketing Mix Modeling", "MMM", "media mix modelling", "mixed media model" end up as four nodes.

- **Layer 1 — prompt rules:** full names, American English, no abbreviation suffixes. Catches most duplicates at extraction time.
- **Layer 2 — `resolve_entities(llm)`:** after extraction, send the full entity list to the LLM in character-budgeted batches (~6k chars each) and ask for synonym groups. Returns a merge map.
- **Layer 3 — `deduplicate_nodes(aliases)`:** rule-based name normalization + alias dictionary application. Collapses self-loops and merges duplicate `(src, label, tgt)` edges, concatenating relation descriptions so no provenance text is lost.

The `OntologyConfig.aliases` dict lets users hard-code merges for known rebrands ("Facebook" → "Meta") that the LLM might miss.

### Per-node provenance

Every `EntityNode` tracks `sources: list[str]` — the filenames that contributed to it. Seeded on first insertion, appended on every subsequent `upsert_nodes_merge` call for the same node. Surfaced in the node detail modal as chips.

This enables:
- Auto-cleanup on file removal (nodes whose `sources` becomes empty are deleted).
- Users seeing which sources a node draws from — important for trust.
- Future filtering (e.g. "show only nodes from this subset of files").

### Incremental build + auto-cleanup

`manifest.json` stores `{filename: mtime}` at save time. On the next build:

- `docs_to_process = {f : current[f] > stored.get(f, 0)}` — new or modified files.
- `removed_files = stored.keys() - current.keys()` — deleted files.
- If anything is removed, `GraphRAGStore.remove_source_references(removed_files)` runs first: strips removed filenames from each node's `sources`, deletes nodes whose `sources` becomes empty, prunes incident edges.
- Extraction runs on `docs_to_process` only.
- `resolve_entities` is skipped when `docs_to_process` is empty (no new entities to resolve, no point paying for LLM tokens).
- Community detection and save always run — the Leiden partition changes whenever the graph does.

### Stale `graph_data.json`

The pickle (`store.pkl`) and `communities.json` are ground truth. `graph_data.json` is a D3-ready denormalization that can go stale if a prior build saved before community detection ran.

`main.py`'s `/api/topics/{topic}/graph` endpoint detects this (`graph_data.communities == 0` but `communities.json` exists) and regenerates lazily on request.

### LLM client selection

`task_manager.make_llm(llm_config)` returns:

- `llama_index.llms.openai.OpenAI` for provider `"openai"`, with optional `api_base` override.
- `llama_index.llms.openai_like.OpenAILike` for everything else — bypasses OpenAI model-name validation so custom models ("qwen/qwen3.5-9b", etc.) work.

Per-request LLM config (from the browser Settings modal) takes precedence over `.env` and bypasses the `_query_engines` cache.

### Streaming chat protocol

`POST /api/topics/{topic}/query/stream` returns `StreamingResponse(media_type="application/x-ndjson")`. One JSON object per line:

```
{"type": "status",  "message": "Checking 12 communities..."}
{"type": "meta",    "communities_checked": 12, "relevant_communities": 4, "sources": [...]}
{"type": "token",   "text": " part of"}
{"type": "token",   "text": " the answer"}
{"type": "replace", "text": "<post-hoc cleaned full answer>"}   // graph-only mode, only if altered
{"type": "done"}
```

The frontend reads via `ReadableStream` + `TextDecoder`, buffers partial lines on `\n`, and updates the chat bubble incrementally. The `replace` event swaps the whole streamed body with the post-hoc citation-filtered version.

### Citation enforcement

Graph-only mode tightens grounding in two stages:

1. **Prompt:** "Wrap every entity reference in `[[Name]]`. If the evidence doesn't cover the question, reply exactly 'Not in the graph.' Do not guess, speculate, or fill gaps."
2. **Post-hoc filter (`_enforce_citations`):** splits the answer into lines; for each non-structural line ≥ 50 characters without "not in the graph" text, splits into sentences and keeps only those containing a `[[...]]` citation. Structural lines (headers, bullets, tables, short connectors) pass through.

Caveat: this is a soft mechanism. The model's training weights always influence phrasing. Users who need hard guarantees should treat the system as a retrieval aid with human review, not an unsupervised oracle.

### Wikipedia-style node articles

`GraphRAGStore.generate_entity_wiki(node_id, llm)` generates on double-click:

- Pulls the node's description, all its relationships (with descriptions), and the community summary it belongs to.
- Prompts the LLM for a 3–5 paragraph encyclopedic article.
- Caches the result in `entity_wikis.json` keyed by `node_id`.

Inspired by Andrej Karpathy's LLM Wiki pattern: store the *synthesised* view, not the raw documents, so downstream consumers read a compounding artefact rather than re-deriving knowledge on every query.

---

## Extension points

- **New document formats:** add a parser to `app/parser.py`, extend the filetype dispatcher.
- **New LLM providers:** extend `app/task_manager.make_llm()` and the provider dropdown in `app/templates/index.html`.
- **Custom ontologies:** edit `graphs/<topic>/ontology.json` (entity types, relation types, aliases) and trigger a full rebuild.
- **Stricter grounding:** `query_engine._enforce_citations` is the single point where sentence-level filtering happens. Swap in a more sophisticated checker (embedding similarity, NLI, etc.) without touching the rest of the pipeline.
- **Graph-level analytics:** the `GraphRAGStore.graph` property exposes the underlying `PropertyGraph`. Walk nodes/edges directly for custom metrics (centrality, shortest paths, diff-between-builds).
- **Larger graphs:** opt into `EMBEDDINGS_ENABLED=true` to add a sentence-embedding pre-filter (`app/embeddings.py`). Vectors persist in `graphs/<topic>/community_embeddings.json` keyed by sha1 of the summary, so changed/removed communities self-invalidate without a full rebuild.
- **External tools:** `GraphRAGStore.export_obsidian()` writes a markdown-per-entity vault with `[[wiki links]]`. `GET /api/topics/{topic}/export/obsidian` zips it on demand. The same pattern can be reused for Roam, Logseq, or any backlinks-based tool by tweaking the front-matter / link syntax.
- **Pinned answers:** `pinned_answers.json` per topic stores `{id, question, answer, mode, sources, created_at}` items via `GET/POST/DELETE /api/topics/{topic}/pinned`. The frontend lists them in the sidebar; clicking replays a pinned Q&A back into the chat without re-querying the LLM.
