# Change Log

> **Entry format (always follow this):**
> ### [Type]: [Short name]
> **Purpose:** Why this change was made — the problem it solves or goal it achieves.
> **Technical implementation:** What was changed and how — files, methods, key decisions.

---

## 2026-04-18 (session 1)

### Fix: Communities not loading in chat
**Purpose:** Graph showed 0 communities in the UI and chat returned "No community summaries found" despite `communities.json` existing on disk.
**Technical implementation:** `GraphRAGStore.load()` loaded `store.pkl` which had been saved before `build_communities()` ran, so `community_summaries` was empty. After pickle load, now checks if `community_summaries` is empty and patches from `communities.json` if it exists. Also regenerates `graph_data.json` on the spot so stats stay consistent. (`app/graph_store.py`)

### Fix: Stats row showing wrong counts
**Purpose:** Status bar showed 251/298/65 while the second stats row showed 223/273/0 — two different counts, both partly wrong.
**Technical implementation:** `graph_data.json` was saved before deduplication and community building, so it had stale pre-dedup counts. The `/api/topics/{topic}/graph` endpoint now lazily regenerates `graph_data.json` when it detects `communities: 0` but `communities.json` exists. Duplicate stats row removed from UI entirely. (`app/main.py`, `app/templates/index.html`, `app/static/js/app.js`, `app/static/js/graph.js`)

### Fix: Edge label slider direction reversed
**Purpose:** Lower slider value showed more labels, which is counterintuitive — users expect higher = more.
**Technical implementation:** Inverted the threshold formula to `10 - sliderValue`. Default value changed from 3 → 7 (same effective threshold). (`app/static/js/graph.js`, `app/templates/index.html`)

### Fix: Chat hanging with thinking LLM
**Purpose:** With a Qwen3 thinking model, each of 65 community relevance checks generated ~2000 reasoning tokens before answering, making total wait 5–15 minutes.
**Technical implementation:** `</think>` stripping applied to response text. Timeout moved to `as_completed(timeout=120s)` so partial results are used rather than blocking on all futures. `/no_think` prefix was attempted but reverted — LM Studio didn't recognise it and caused longer/confused responses. (`app/query_engine.py`)

### Feat: Keyword pre-filter for chat speed
**Purpose:** Cut the number of community LLM calls from 65 → 5–15 for specific queries, making chat usable with local models.
**Technical implementation:** Added `_select_candidates()` in `GraphRAGQueryEngine`: extracts non-stopword keywords from the query, scores each community summary by keyword overlap, discards zero-match summaries, caps at `max_communities=15` top-ranked. (`app/query_engine.py`)

### Feat: Node double-click Wikipedia-style modal
**Purpose:** Single click showed a sidebar; users wanted a richer, more immersive view of a node — inspired by Wikipedia article format.
**Technical implementation:** 280ms double-click detection via `_clickTimer`. `showNodeModal()` renders type badge, title, connection stats, description, and 2-column relationship grid. Relationship cards navigate to other nodes. ESC and backdrop click close the modal. (`app/static/js/graph.js`, `app/templates/index.html`, `app/static/css/style.css`)

### Feat: Claude and Gemini providers in LLM settings
**Purpose:** Users wanted to use Anthropic and Google models, not just OpenAI or local models.
**Technical implementation:** Added `anthropic` and `gemini` to the provider dropdown. Gemini uses OpenAI-compatible endpoint via `OpenAILike`. Claude uses `llama-index-llms-anthropic` with graceful fallback if package missing. JS pre-fills model name placeholders per provider. Added `llama-index-llms-anthropic` to `requirements.txt`. (`app/task_manager.py`, `app/templates/index.html`, `app/static/js/app.js`, `requirements.txt`)

### Feat: Header buttons pinned to right
**Purpose:** Theme and settings buttons were left-aligned, which looked unfinished.
**Technical implementation:** Wrapped buttons in `.header-right` div with `margin-left: auto`. (`app/templates/index.html`, `app/static/css/style.css`)

---

## 2026-04-18 (session 2)

### Feat: Hybrid extraction pipeline
**Purpose:** Ingestion was slow because the old pipeline made one LLM call per chunk (N_chunks × 1 call per document). Goal was 4–6× speedup.
**Technical implementation:** Each document now processed in exactly 2 LLM calls: (1) `_summarise_document()` compresses the full document into a rich summary preserving all entities and facts; (2) `GraphRAGExtractor.extract()` extracts entities and relationships from the summary. `GraphRAGExtractor` refactored from LlamaIndex `TransformComponent` to a plain async class. `build_topic_graph()` uses `_process_doc()` coroutines run via `run_jobs`. Summarisation skipped for documents under 1500 chars. (`app/pipeline.py`)

### Feat: Description-merging node upsert
**Purpose:** When the same entity appears across multiple documents, the old upsert overwrote its description. Wanted richer, multi-source descriptions.
**Technical implementation:** Added `upsert_nodes_merge()` to `GraphRAGStore`: if a node already exists, appends the new `entity_description` rather than replacing it (skips if identical). (`app/graph_store.py`)

### Feat: On-demand Wikipedia-style wiki articles
**Purpose:** Double-click modal showed only the extracted description (one sentence). Wanted a full encyclopedic article synthesised from all available context — inspired by Karpathy's LLM Wiki pattern.
**Technical implementation:** Added `generate_entity_wiki()` async method to `GraphRAGStore`: builds a prompt from the node's description, all outgoing/incoming relationships with their context, and the community summary for the node's cluster; calls LLM to write 3–5 flowing paragraphs; caches result in `entity_wikis` dict. Added `entity_wikis: dict` and `node_community: dict` class attributes. `build_communities()` now populates `node_community` (node_id → cluster_id) from Leiden output. `save()` writes `entity_wikis.json`; `load()` reads it back. New `GET /api/topics/{topic}/nodes/{node_id}?generate=true` endpoint generates and persists the article on first call, returns cached version after. `showNodeModal()` in JS fetches from this endpoint with a loading spinner, falls back to local D3 data on error. (`app/graph_store.py`, `app/main.py`, `app/static/js/graph.js`, `app/static/css/style.css`)

---

## 2026-04-19

### Fix: Wiki articles truncated mid-sentence
**Purpose:** Articles generated via Claude API were cut off because `acomplete()` was using the LLM client's default `max_tokens`, which is too low for a 3–5 paragraph article.
**Technical implementation:** Added `max_tokens=2048` to the `llm.acomplete(prompt, max_tokens=2048)` call in `generate_entity_wiki()`. To regenerate already-truncated articles, delete `entity_wikis.json` from the topic's graph folder and double-click nodes again. (`app/graph_store.py`)


### Feat: Search with dropdown and graph pan
**Purpose:** The existing search only found the first matching node with no visual feedback. Users wanted to search by name or description and navigate to the result on the graph.
**Technical implementation:** Replaced the single-match `nodes.find()` with a scored list of up to 10 results searching both `label` and `description`. Exact/prefix matches rank first. Results render in a `#search-dropdown` div with type badge, name, and description snippet. Keyboard navigation: ↑/↓ to move, Enter to select, Escape to close. On selection: highlights the node, opens the detail panel, and smoothly pans/zooms the graph to centre on the node (`panToNode()` via `d3.zoomIdentity`). (`app/static/js/graph.js`, `app/templates/index.html`, `app/static/css/style.css`)

### Fix: Wiki article generation ignoring session LLM config
**Purpose:** Double-click wiki generation always used the server `.env` LLM even when the user had switched to a different provider (e.g. Claude API) in the UI settings modal.
**Technical implementation:** Changed `GET /api/topics/{topic}/nodes/{node_id}` to `POST`, accepting an optional `NodeRequest` body with `generate: bool` and `llm: Optional[LLMConfig]`. `make_llm()` now receives the per-request config, falling back to server settings when absent. JS `showNodeModal()` sends a POST with `{ generate: true, llm: getLLMConfig() }` so the session's provider/key is forwarded. (`app/main.py`, `app/static/js/graph.js`)

---

### Chore: CLAUDE.md, log.md, karpathy gist.md added
**Purpose:** Establish session memory, change tracking, and reference material for the Karpathy LLM Wiki pattern that inspired the wiki article feature.
**Technical implementation:** `CLAUDE.md` documents run commands, architecture, key constraints. `log.md` tracks changes per session. `karpathy gist.md` is the source reference. All committed to repo.
