# Change Log

## 2026-04-18 (session 2)

### Feat: Hybrid extraction pipeline (`app/pipeline.py`)
- Replaced chunk-per-call extraction (N_chunks × 1 LLM call) with 2-call-per-document hybrid:
  1. Summarise full document via `_summarise_document()` (preserves all entities/facts)
  2. Extract entities + relationships from the summary
- Skips summarisation for documents shorter than 1500 chars
- `GraphRAGExtractor` refactored from LlamaIndex `TransformComponent` to plain async class with `extract(text, source_metadata)` method
- `build_topic_graph()` now uses `_process_doc()` coroutines run via `run_jobs`
- Expected ~4-6× faster ingestion for typical document lengths

### Feat: Entity deduplication in pipeline (`app/pipeline.py`, `app/graph_store.py`)
- `upsert_nodes_merge()` added to `GraphRAGStore`: merges `entity_description` instead of overwriting when the same node appears across multiple documents
- `deduplicate_nodes()` and `resolve_entities()` (LLM-based synonym detection) integrated into pipeline

### Feat: Wikipedia-style wiki articles on node double-click
- **`app/graph_store.py`**: Added `entity_wikis: dict`, `node_community: dict`, `generate_entity_wiki()` async method
  - `generate_entity_wiki()` builds context from node description, all relationships, community summary; calls LLM to write 3-5 paragraph encyclopedic article; caches result in `entity_wikis`
  - `build_communities()` now populates `node_community` (node_id → cluster_id)
  - `save()` writes `entity_wikis.json`; `load()` reads it back
- **`app/main.py`**: New `GET /api/topics/{topic}/nodes/{node_id}?generate=true` endpoint
  - Returns full node detail including wiki_article, community_summary, outgoing/incoming relationship lists
  - If `generate=true` and no cached wiki: generates via LLM and persists to `entity_wikis.json`
- **`app/static/js/graph.js`**: `showNodeModal()` now fetches from API with loading spinner; falls back to local D3 data on error
  - Wiki article rendered as flowing paragraphs
  - Community cluster context shown as highlighted aside
  - Relationship cards navigate to other nodes
- **`app/static/css/style.css`**: Added `.nm-loading`, `.nm-spinner`, `.nm-wiki-article`, `.nm-community-summary` styles



## 2026-04-18

### Fix: Communities not loading in chat (`app/graph_store.py`)
- `GraphRAGStore.load()` loaded `store.pkl` successfully but the pickle had been saved before communities were built, so `community_summaries` was empty.
- After loading from pickle, now checks if `community_summaries` is empty and patches from `communities.json` if it exists.
- Also regenerates `graph_data.json` on the spot when patching, so stats stay consistent.

### Fix: Stats row showing wrong counts (`app/main.py`, `app/graph_store.py`)
- `graph_data.json` for the MMM graph was saved before deduplication and community building, so it showed 223 nodes / 273 edges / 0 communities instead of 251 / 298 / 65.
- The `/api/topics/{topic}/graph` endpoint now lazily regenerates `graph_data.json` when it detects `communities: 0` but `communities.json` exists.

### Fix: Edge label slider direction reversed (`app/static/js/graph.js`, `app/templates/index.html`)
- Slider was inverted: lower value = more labels shown, which is counterintuitive.
- Fixed by inverting the threshold formula to `10 - sliderValue`, so higher slider = more labels.
- Default value changed from 3 → 7 (same effective threshold of `minD >= 3`).

### Fix: Chat hanging with thinking LLM (`app/query_engine.py`)
- With a Qwen3 thinking model (e.g. qwen3.5-9b), each of the 65 community relevance checks was generating ~2000 reasoning tokens before answering, making the total wait 5–15 minutes.
- `</think>` stripping applied to response text.
- Timeout moved to `as_completed(timeout=...)` so partial results are used rather than blocking.
- **Reverted** `/no_think` prefix — model server didn't recognise it, causing longer responses instead.

### Fix: Duplicate stats row removed (`app/templates/index.html`, `app/static/js/app.js`, `app/static/js/graph.js`)
- Removed the `nodes | edges | communities` stats row below the graph — it duplicated the top status bar but used stale `graph_data.json` counts, causing visible discrepancy.
- Live extraction counts (nodes/edges extracted during build) moved inline into the top status bar message.

### Feat: Chat speed — keyword pre-filter + community cap (`app/query_engine.py`)
- Added `_select_candidates()`: extracts non-stopword keywords from the query, scores each community summary by keyword overlap, discards zero-match summaries, and caps at `max_communities=15` (top-ranked).
- For specific queries this cuts LLM calls from 65 → 5–10; for broad queries it caps at 15 instead of 65.
- Timeout raised to 120s to give the remaining calls room.

### Fix: Header buttons pushed to right side (`app/templates/index.html`, `app/static/css/style.css`)
- Wrapped theme + settings buttons in `.header-right` div with `margin-left: auto` to pin them to the far right.

### Feat: Claude and Gemini providers in LLM settings (`app/templates/index.html`, `app/static/js/app.js`, `app/task_manager.py`, `requirements.txt`)
- Added `anthropic` and `gemini` options to the provider dropdown.
- Gemini uses OpenAI-compatible endpoint (`generativelanguage.googleapis.com/v1beta/openai/`) via `OpenAILike`.
- Claude uses `llama-index-llms-anthropic` (added to requirements.txt); graceful error if package missing.
- JS pre-fills sensible model name placeholders per provider (e.g. `claude-sonnet-4-6`, `gemini-2.5-pro-preview-05-06`).

### Feat: Node double-click opens Wikipedia-style modal (`app/static/js/graph.js`, `app/templates/index.html`, `app/static/css/style.css`)
- Single click still shows the side detail panel.
- Double-click (two clicks within 280ms) opens a full modal with large title, type badge, connection stats, full description, and a 2-column relationship grid.
- Clicking a relationship card inside the modal navigates to that node's modal.
- ESC key and backdrop click close the modal.
