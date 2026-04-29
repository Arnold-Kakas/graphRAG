# Change Log

> **Entry format (always follow this):**
> ### [Type]: [Short name]
> **Purpose:** Why this change was made — the problem it solves or goal it achieves.
> **Technical implementation:** What was changed and how — files, methods, key decisions.

---

## 2026-04-29

### Fix: Detail panel reserves space even when hidden
**Purpose:** When a graph is loaded but no node or edge is selected, the right-side detail panel was always occupying 260 px of horizontal space, leaving a blank strip beside the graph canvas.
**Technical implementation:** The panel previously used `transform: translateX(100%)` to slide off-screen while still participating in flex layout at full width. Switched to `width: 0; padding: 0; overflow: hidden` as the collapsed default, with `width: 260px; padding: 16px 14px; overflow-y: auto` restored on `.visible`. Added `transition: width 0.22s ease, padding 0.22s ease` to keep the slide-in animation smooth. No JS changes — the existing `.visible` class toggle already drives the state. (`app/static/css/style.css`)

---

## 2026-04-27

### Fix: Merge task running forever — no timeout on resolve_entities LLM calls
**Purpose:** `resolve_entities` used `llm.complete()` (synchronous, no timeout). With a local reasoning model generating tokens in an infinite loop, this blocked indefinitely — confirmed case of 8+ hour hang.
**Technical implementation:** Converted `resolve_entities` and `_resolve_one_pass` to `async def`, switching from `llm.complete()` to `await asyncio.wait_for(llm.acomplete(prompt), timeout=timeout)`. Default timeout is 120 s per batch (overridden to `config.llm_request_timeout` when called from `merge_topic_entities`). Timed-out batches log a warning and are skipped; the rest of the pass continues. Added `import asyncio` to `graph_store.py`. Updated caller in `pipeline.py` to `await` the now-async call. (`app/graph_store.py`, `app/pipeline.py`)

---

### Feat: LLM re-summarization of merged entity descriptions
**Purpose:** When two nodes are merged, their `entity_description` fields are concatenated — the result is redundant, verbose, and incoherent. The concatenated text then pollutes wiki generation, community summaries, and future resolution prompts.
**Technical implementation:** `deduplicate_nodes()` now tracks which winner nodes had their description extended by a loser's text (returned as `set[str]` alongside the existing count — call sites that don't need it unpack with `_`). New async `resummmarize_merged_descriptions(node_ids, llm)` method on `GraphRAGStore` iterates those nodes and asks the LLM to rewrite the combined text into a single 2–4 sentence description, stripping redundancy while preserving unique facts. Strips `</think>` tokens for reasoning models. Called from `merge_topic_entities()` in `pipeline.py` after deduplication; the build pipeline ignores the winners set since rule-based-only deduplication rarely produces meaningful concatenations. (`app/graph_store.py`, `app/pipeline.py`)

---

### Feat: Merge entities as a standalone task
**Purpose:** LLM-based entity resolution (`resolve_entities`) was baked into every build, making builds slow and prone to reasoning-model loops. Users had no control over when the expensive synonym-merging step ran. Separating it lets users build quickly, inspect the graph, then decide to merge.
**Technical implementation:** Removed `resolve_entities()` call from `build_topic_graph()` in `pipeline.py` — builds now only apply rule-based `deduplicate_nodes()` with existing learned and ontology aliases. New `merge_topic_entities()` async function in `pipeline.py` loads the existing store, runs `resolve_entities()` + `deduplicate_nodes()`, persists `learned_aliases.json`, rebuilds the index, saves, and updates `build_meta.json`. New `start_merge()` / `_run_merge()` methods on `TaskManager` follow the same background-task pattern as builds. New `POST /api/topics/{topic}/merge` endpoint (202). New `MergeRequest` model in `models.py`. New "Merge entities" button in the header (disabled until a graph exists), wired to the same polling mechanism as builds. (`app/pipeline.py`, `app/task_manager.py`, `app/main.py`, `app/models.py`, `app/templates/index.html`, `app/static/js/app.js`)

---

### Fix: Reasoning-model loops in entity resolution + misleading checkbox label
**Purpose:** When a reasoning/thinking model (DeepSeek R1, QwQ, etc.) is loaded in LM Studio, `resolve_entities()` sent up to 60 entities per batch. The model would loop through the full list repeatedly in its chain-of-thought, never emitting the JSON result and eventually timing out. The "Enable thinking" checkbox label was also misleading — it doesn't add `/think` to prompts; it switches extraction from `astructured_predict()` to raw `acomplete()` so `</think>` tokens don't break structured parsing.
**Technical implementation:** Reduced `max_entities_per_batch` default in `resolve_entities()` from 60 → 25 (15 when `thinking=True` is explicitly set). Added `"Output ONLY a raw JSON array ... No commentary, no explanation, no step-by-step reasoning."` directive at the top of the `_resolve_one_pass` prompt to discourage chain-of-thought before the answer. Renamed checkbox from "Enable thinking" to "Reasoning model" with an accurate tooltip explaining what the flag actually does. (`app/graph_store.py`, `app/pipeline.py`, `app/templates/index.html`)

---

## 2026-04-25

### Fix: Runaway thinking-mode builds timing out after hours
**Purpose:** When thinking mode was enabled during a build, `_summarise_document` and `_acomplete_extract` both called `llm.acomplete()` with no per-call time limit. The LLM client's `timeout` constructor argument controls the HTTP connection timeout, not the total generation duration. On a slow local model with `max_tokens=16384`, a thinking model could spend many hours generating reasoning tokens for a single document, with no way to interrupt it.
**Technical implementation:** Wrapped both `acomplete()` calls in `asyncio.wait_for(..., timeout=config.llm_request_timeout)`. Added a `timeout` parameter to `GraphRAGExtractor.__init__` (stored as `self._timeout`) and `_summarise_document`. `build_topic_graph` now threads `config.llm_request_timeout` through to both. The existing `except Exception` handlers already catch `asyncio.TimeoutError` and fall back gracefully (empty extraction result / raw text fallback), so a timed-out call just moves on to the next document. (`app/pipeline.py`)

---

### Feat: Blog post generation with interactive charts, references, and export
**Purpose:** Allow users to turn the knowledge graph into a publishable blog post. The graph contains rich structured knowledge but no way to produce long-form content from it. The new feature lets the user describe their angle and preferred structure, then generates a blog post grounded in community summaries and entity relationships, with optional interactive Chart.js visualisations and source references traced back to the original documents.
**Technical implementation:**
- New `BlogRequest` model in `app/models.py` (`ideas`, `outline`, `length`, `llm`).
- Two helper functions in `app/main.py`: `_build_blog_context()` collects top-20 community summaries, top-30 entities by centrality, top-40 relationships, and a numbered source-file reference list derived from entity `sources` properties; `_build_blog_prompt()` assembles the LLM prompt with chart example and footnote referencing instructions.
- New streaming endpoint `POST /api/topics/{topic}/blog/stream` (NDJSON, same protocol as `/query/stream`): loads the store, builds context, calls `llm.astream_complete()`, streams `status|token|done|error` events.
- Frontend: "Write Blog Post" button added to the sidebar Export section; blog input modal (ideas textarea, optional outline, 3-way length selector); full-screen blog result overlay (900 px wide, 90 vh tall) with live streaming preview and final Chart.js render.
- `renderBlogMarkdown(text, preview)` in `app.js`: full markdown parser for blog typography (h1–h3, p, ul, ol, table, pre); ` ```chartjs ` fences become placeholder divs in preview mode and `<canvas>` elements in full mode; `[^N]` footnote references rendered as superscripts; `[^N]: text` definitions collected and appended as a References block.
- Export to MD: raw markdown download. Export to HTML: standalone file with Chart.js CDN, inline `<script>` initialises each chart on DOMContentLoaded, plain readable CSS.
- Chart.js 4.4.1 CDN added to `index.html`; blog input and result modals added before `<script>` tags.
(`app/models.py`, `app/main.py`, `app/templates/index.html`, `app/static/js/app.js`, `app/static/css/style.css`)

---

## 2026-04-21

### Fix: Synonym duplicates surviving incremental builds
**Purpose:** Adding documents to an existing topic produced near-duplicate nodes that should have collapsed: "Marketing Mix Modeling" alongside "Marketing Mix Model", "Media Mix Model", "Media Mix Modeling"; "ROAS" alongside "Return on Ads Spend". Three problems compounded — (a) `_normalize_name` only handled case + spelling so "Modeling"/"Model" stayed distinct; (b) the LLM resolver ran a single pass with alphabetical ordering, so synonymous variants rarely landed in the same batch; (c) merges discovered by the LLM in one build were thrown away, so the same tokens kept burning resolver calls every incremental build.
**Technical implementation:**
- New helpers in `graph_store.py`: `_stem_token` (gerund/plural-aware, with -ss/-us/-is/-os/-as exclusions so "ROAS"/"Status"/"Bayes" survive), `_token_signature` (token-order-preserving stem-aware key — "Marketing Mix Modeling" and "Marketing Mix Model" both reduce to "marketing mix model"), `_acronym_pairs` (initials-match detection so "ROAS" pairs with "Return on Ads Spend").
- `deduplicate_nodes` now runs four signals — normalized-name groups, token-signature groups, acronym ↔ expansion pairs, and explicit aliases — funneling them through a single `_record_merge` helper that flattens transitive chains (A→B and B→C collapse to A→C) and a `_pick_canonical` priority of (edge_count, name length, name). Before deletion, the loser's `entity_description` and `sources` are merged into the winner so no provenance text is lost.
- `resolve_entities` refactored into a thin two-pass driver around new `_resolve_one_pass`. Pass 1 sorts by token signature so likely synonyms end up batched together; pass 2 sorts by type → name and only considers nodes not already merged in pass 1. Prompt loosened with "when in doubt, MERGE" guidance and explicit examples for gerund/noun, noun-order swaps, and acronym ↔ expansion. Falls back to longest in-graph alias if the LLM rewrites the canonical to a name that isn't in the graph.
- `pipeline.py` now persists LLM merges to `graphs/<topic>/learned_aliases.json` and reapplies them on every subsequent build — including incremental and removal-only builds where the resolver is skipped — so once a synonym is discovered, all later builds collapse it for free. Precedence: ontology aliases (user-curated) > learned aliases > current-pass merges (already inside learned).
(`app/graph_store.py`, `app/pipeline.py`)

---

## 2026-04-20

### Feat: Search inside the graph index
**Purpose:** Sidebar search matched only on label and description in the loaded graph. It missed type-name searches ("which methods are PROCESS entities?"), and ranked alphabetically — central hubs sank below obscure same-named nodes when many entities share a substring. No way to see at a glance which cluster a result belonged to.
**Technical implementation:** `loadGraph` now fetches `/api/topics/{topic}/index` in parallel with the graph payload and passes it to `initGraph(data, index)`. The search handler scores matches by where they hit (label exact > prefix > contains > type > description), then breaks ties by `degree` from the entity index so well-connected entities rank first. Each result row now shows `<degree> links · cluster <id>` in a `.sri-meta` badge so the cluster is visible without opening the node. (`app/static/js/app.js`, `app/static/js/graph.js`, `app/static/css/style.css`)

### Feat: Embeddings-based community pre-filter (opt-in)
**Purpose:** Past ~200 communities, keyword overlap starts missing semantically related communities — a query for "budget allocation" misses a community that talks about "spend optimization." The keyword filter is fast but blunt at scale, and the LLM relevance pass is bottlenecked by however many communities the pre-filter let through.
**Technical implementation:** New `app/embeddings.py` wraps sentence-transformers behind a small `CommunityEmbeddingIndex` that caches per-community vectors in `graphs/<topic>/community_embeddings.json` (keyed by sha1 of the summary, so stale entries auto-invalidate when summaries change). `_select_candidates` blends cosine similarity (scaled ×10) with keyword + entity-index hits — embeddings are additive, not replacement, so the existing keyword path stays useful for short literal queries. Opt-in via `EMBEDDINGS_ENABLED=true` and `EMBEDDING_MODEL=` (default `all-MiniLM-L6-v2`); `sentence-transformers` is listed but commented out in `requirements.txt` since it pulls torch. The query engine takes a new `embedding_cache_path` field that `main.py` wires per topic. (`app/embeddings.py` [new], `app/query_engine.py`, `app/config.py`, `app/main.py`, `requirements.txt`)

### Feat: Pin chat answers to the topic
**Purpose:** Useful answers from the chat had no shelf life — they scrolled away on the next question and were gone if the page reloaded. Users wanted to keep good Q&A pairs as a topic-level reference, similar to how the wiki articles persist.
**Technical implementation:** Three new endpoints store/list/delete `pinned_answers.json` per topic: `GET /api/topics/{topic}/pinned`, `POST` (creates an item with uuid + timestamp), and `DELETE /api/topics/{topic}/pinned/{id}`. Frontend: each finalised assistant message gets a "📌 Pin answer" button that POSTs the question, answer, mode, and sources. A new sidebar section "Pinned answers" lists short Q&A previews; clicking a pinned item replays it into the chat (without re-querying the LLM), and the `×` button removes it. The streaming code path now passes `query` and `answerText` to `finalizeStreamingMessage` so the pin payload is available. (`app/main.py`, `app/static/js/app.js`, `app/templates/index.html`, `app/static/css/style.css`)

### Feat: Obsidian-compatible export
**Purpose:** Users wanted to take the graph offline into their note-taking workflow. The internal pickle and JSON files are great for the app but useless inside Obsidian, where backlinks and the graph view rely on filename-based `[[wiki links]]` between markdown files.
**Technical implementation:** `GraphRAGStore.export_obsidian(target_dir, topic)` writes one `.md` per entity with YAML frontmatter (`id`, `type`, `degree`, `community`, `sources`, `tags`) and a body containing the description, cached wiki article (if any), cluster context, and `[[Other Entity]]` links to every connected node. Filenames are sanitised for cross-OS safety with disambiguation suffixes when names collapse. A top-level `_index.md` lists top hubs and a per-type roll-up. New endpoint `GET /api/topics/{topic}/export/obsidian` builds the export into a tempdir, zips it in-memory, and serves it as `Content-Disposition: attachment`. Sidebar gets an "Obsidian vault (.zip)" button that triggers the download. (`app/graph_store.py`, `app/main.py`, `app/templates/index.html`, `app/static/js/app.js`, `app/static/css/style.css`)

### Feat: CSV / structured-data ingestion beyond text columns
**Purpose:** Previous CSV parsing called `df.to_string()` on the entire DataFrame, which truncates wide tables and gives the LLM a poor representation. CSVs that are clearly entity tables (e.g. a list of tools with name + category + description columns) were getting flattened into noise instead of becoming first-class graph nodes.
**Technical implementation:** `_parse_csv` now picks one of three modes based on column shape and records the choice in document metadata as `csv_mode`. Mode 1 (`narrative`): a recognised text column (`full_text`/`text`/`content`/`body`/`article`/`description`) wins outright — rows joined with `---`. Mode 2 (`entity_per_row`): a name-like AND a type-like column trigger per-row markdown blocks (`## <name>` / `- **Type:** <kind>` / `- **<col>:** <val>` for every other column). Mode 3 (`table`): generic CSVs get a schema preamble plus key=value lines, capped at 200 rows with `truncated_to` recorded in metadata. New `_csv_cell` helper handles NaN/None/whitespace consistently. (`app/parser.py`)

### Feat: Build Context modal on incremental builds + auto-grow chat textarea
**Purpose:** Two UI papercuts: (1) The build-context input was gated to first builds and full rebuilds, so users adding a few new files couldn't update the focus instructions. (2) The chat input was a fixed 40-pixel textarea — typing a multi-line question scrolled inside the box instead of growing it, hiding earlier lines.
**Technical implementation:** (1) Removed the `!currentTopicHasGraph || force` gate from `onBuild`; the context modal now opens for every build, prefilled with the previous build context. The skip button still bypasses it. (2) Replaced the textarea's `height: 40px` with `min-height: 40px; max-height: 200px`. New `autosizeTextarea(el)` helper sets height to `auto` then to `scrollHeight` (capped) on every `input` event; reset on send. (`app/static/js/app.js`, `app/static/css/style.css`)

### Debug: Log failing extraction text
**Purpose:** When plain-text JSON extraction failed, the warning said only "no parseable JSON" with no indication of what the model actually returned — impossible to diagnose whether the problem was truncation, prose wrapping, or a thinking-block overrun.
**Technical implementation:** `_acomplete_extract` now logs the first 300 chars and (when long) the last 200 chars of the unparseable response alongside its length. Lets the user quickly classify the failure mode. (`app/pipeline.py`)

### Docs: README rewrite and ARCHITECTURE.md
**Purpose:** README had drifted heavily — it still documented the "deleted files stay in the graph" limitation that was just fixed, and omitted most features added over the last few sessions (streaming chat, citation chips, per-node sources, build context, per-session LLM override, wiki articles, LLM indicator). No deeper technical reference existed.
**Technical implementation:** Rewrote `README.md` as a feature-forward user-facing document organized by build / chat / visualization / UX sections, with an updated Docker networking note and parameter table including `LLM_MAX_TOKENS`. Created `docs/ARCHITECTURE.md` covering data flow (ASCII diagram), module responsibilities, and the key architectural decisions (hybrid pipeline, extraction fallback, three-layer dedup, provenance, incremental + auto-cleanup, streaming protocol, citation enforcement, wiki articles). README links to the architecture doc. (`README.md`, `docs/ARCHITECTURE.md` [new])

### Feat: Auto-cleanup of orphaned nodes when source files are removed
**Purpose:** Incremental builds previously only tracked additions and modifications. If a user removed a document from `raw/<topic>/`, its extracted nodes, edges, and `sources` references silently stayed in the graph — the graph drifted out of sync with the corpus. Forced users into full rebuilds for any corrective removal.
**Technical implementation:** `GraphRAGStore.remove_source_references(removed_filenames)` strips the given filenames from every node's `sources` list; nodes whose sources become empty are deleted along with their incident edges. Nodes with no sources property (legacy) are preserved. `build_topic_graph` now computes `removed_files = stored_mtimes.keys() - current_mtimes.keys()` at the start of an incremental build and invokes the cleanup before extraction. Removal-only builds (no new/changed files, only deletions) still run dedup, community detection and save, but skip the LLM entity resolver since no new entities exist to resolve. (`app/graph_store.py`, `app/pipeline.py`)

### Feat: Interactive citations with post-hoc filter in graph-only mode
**Purpose:** "Graph only" mode previously relied on a soft prompt instruction with no enforcement — the LLM could still leak training knowledge silently. Also, entity mentions in answers were plain text with no way to jump to them on the graph.
**Technical implementation:** (1) Aggregation prompt now instructs the LLM to wrap every entity reference in `[[Entity Name]]` and tightens graph-only mode with an explicit "Not in the graph" fallback and "do not guess, speculate, or fill gaps" rule. (2) `_enforce_citations()` runs in graph-only mode and drops claim sentences (≥50 chars, non-structural) that contain no `[[...]]` citation. (3) Streaming path buffers tokens and emits a `replace` event if the cleaned text differs. (4) Frontend `renderMarkdown` parses `[[...]]` into `.cite-chip` spans; a delegated click handler calls `window.graphSelectByLabel(name)` exposed by `graph.js`, which selects/pans/shows the node detail. Misses flash red briefly. (`app/query_engine.py`, `app/static/js/app.js`, `app/static/js/graph.js`, `app/static/css/style.css`)

---

## 2026-04-18

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

## 2026-04-18

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

### Fix + Feat: Max tokens configurable; wiki Recreate button
**Purpose:** Wiki articles were truncated because `max_tokens` was not set reliably. Users also needed a way to regenerate a cached (truncated) article without deleting `entity_wikis.json` manually.
**Technical implementation:**
- `LLM_MAX_TOKENS` added to `config.py` (default 4096) and `.env.example`
- `max_tokens: Optional[int]` added to `LLMConfig` — users can override per-session from the settings modal
- `make_llm()` resolves max_tokens: per-request config → server `.env` → 4096. Passed to `AnthropicLLM`, `OpenAILike`, and `OpenAI` constructors
- `generate_entity_wiki()` accepts `force: bool` to skip cache and overwrite
- `NodeRequest` gains `force: bool`; endpoint regenerates even if cache exists when `force=True`
- `↺ Recreate` button in wiki modal meta row (only when `has_wiki=True`); re-fetches with `force: true` and re-renders in place
- Settings modal gets "Max output tokens" field; saved/loaded from sessionStorage
(`app/config.py`, `app/models.py`, `app/task_manager.py`, `app/graph_store.py`, `app/main.py`, `app/templates/index.html`, `app/static/js/app.js`, `app/static/js/graph.js`, `app/static/css/style.css`, `.env.example`)


### Feat: Extended mode separates graph vs AI knowledge in answer
**Purpose:** When "+ AI knowledge" toggle is on, the answer blended graph and AI content with no way to tell which was which.
**Technical implementation:** Updated `_aggregate()` prompt in extended mode to instruct the LLM to structure the answer in two labelled sections: "**From the knowledge graph:**" (always present) and "**From AI knowledge:**" (only included if Claude adds something beyond the graph). The second section is skipped entirely when the graph fully covers the question. Both labels render as bold via `renderMarkdown()`. (`app/query_engine.py`)

### Fix: Mode toggle redesign, Recreate button style, chat markdown rendering
**Purpose:** Knowledge mode buttons had unclear active state; Recreate button didn't match app style; chat output rendered raw markdown syntax instead of formatted HTML.
**Technical implementation:**
- Mode buttons replaced with an iOS-style toggle switch (`<input type=checkbox>` + CSS track/thumb). Left label = "Graph only", right label = "+ AI knowledge" turns yellow (`.mode-label-active`) when toggled on. JS reads `modeToggle.checked` instead of `querySelector(".mode-btn.active")`
- Recreate button restyled as underlined text link — no border/background, uses `var(--text-muted)` → `var(--accent)` on hover, matching secondary action pattern in the app
- `renderMarkdown()` function added to `app.js`: processes text line-by-line, emits `<h2>`, `<h3>`, `<ul>/<li>`, `<ol>/<li>`, `<p>`, `<strong>`, `<em>` — replaces the old single-pass regex approach that only handled bold and newlines. CSS added for `.chat-h2`, `.chat-h3`, `.chat-ul`, `.chat-ol` inside `.chat-bubble`
(`app/templates/index.html`, `app/static/js/app.js`, `app/static/css/style.css`)

### Feat: Chat sources panel + knowledge mode toggle
**Purpose:** Users couldn't see which community summaries contributed to an answer, and wanted an option to let the LLM supplement graph knowledge with its own training data when the graph has gaps.
**Technical implementation:**
- `custom_query()` now returns `sources: list[(cid, summary)]` alongside the answer — tracks which community futures produced non-empty answers via `futures dict → (cid, summary)` mapping
- `QueryResponse` gains `sources: list[SourceCommunity]`; `QueryRequest` gains `mode: str` ("graph" | "extended")
- `_aggregate()` receives `mode` param: "graph" constrains answer to graph evidence only; "extended" allows LLM to supplement with training knowledge
- `_aggregate_extended()` added for the edge case where graph has zero relevant communities but mode=extended
- Chat UI: "Knowledge source" toggle row above input — "Graph only" / "Graph + AI knowledge" pill buttons; active mode sent with each query
- Sources collapsible below each assistant message: "Sources (N) ▸" expands to list of cluster IDs, each individually expandable to show full community summary
(`app/models.py`, `app/query_engine.py`, `app/main.py`, `app/templates/index.html`, `app/static/js/app.js`, `app/static/css/style.css`)

### Fix: Wiki articles prompt bounded to one-pager
**Purpose:** With high max_tokens, articles could sprawl indefinitely. Constrained the prompt to exactly 3 paragraphs of 3–5 sentences each so output is always a tight one-pager regardless of token budget.
**Technical implementation:** Prompt in `generate_entity_wiki()` now specifies "exactly 3 tight paragraphs — no more, no less" with explicit per-paragraph instructions and "Stop after the third paragraph." (`app/graph_store.py`)

### Feat: Search with dropdown and graph pan
**Purpose:** The existing search only found the first matching node with no visual feedback. Users wanted to search by name or description and navigate to the result on the graph.
**Technical implementation:** Replaced the single-match `nodes.find()` with a scored list of up to 10 results searching both `label` and `description`. Exact/prefix matches rank first. Results render in a `#search-dropdown` div with type badge, name, and description snippet. Keyboard navigation: ↑/↓ to move, Enter to select, Escape to close. On selection: highlights the node, opens the detail panel, and smoothly pans/zooms the graph to centre on the node (`panToNode()` via `d3.zoomIdentity`). (`app/static/js/graph.js`, `app/templates/index.html`, `app/static/css/style.css`)

### Fix: Wiki article generation ignoring session LLM config
**Purpose:** Double-click wiki generation always used the server `.env` LLM even when the user had switched to a different provider (e.g. Claude API) in the UI settings modal.
**Technical implementation:** Changed `GET /api/topics/{topic}/nodes/{node_id}` to `POST`, accepting an optional `NodeRequest` body with `generate: bool` and `llm: Optional[LLMConfig]`. `make_llm()` now receives the per-request config, falling back to server settings when absent. JS `showNodeModal()` sends a POST with `{ generate: true, llm: getLLMConfig() }` so the session's provider/key is forwarded. (`app/main.py`, `app/static/js/graph.js`)

### Feat: Markdown table rendering in chat
**Purpose:** LLM responses containing pipe-table syntax (`| col | col |`) rendered as raw text with no formatting.
**Technical implementation:** `renderMarkdown()` in `app.js` now buffers consecutive `|`-prefixed lines into a `tableLines` array, identifies the separator row (`|---|---|`), and emits `<table class="chat-table">` with `<thead>` and `<tbody>`. Fallback to plain `<p>` if no valid separator found. CSS `.chat-table` added: collapsed borders, header background, row hover accent. (`app/static/js/app.js`, `app/static/css/style.css`)

### Fix: Regenerate article button — renamed, moved, and resized
**Purpose:** The "↺ Recreate" button in the node modal meta row was confusingly named (sounded like the node would be recreated), too small, and visually detached from the article it regenerates.
**Technical implementation:** Button renamed to "↺ Regenerate article", moved from `.nm-meta` row to immediately after `.nm-wiki-article` div. Font-size increased 11px → 13px, `display: block` with `margin-top: 8px` so it flows naturally below the article text. (`app/static/js/graph.js`, `app/static/css/style.css`)

---

## 2026-04-20

### Chore: Full project audit
**Purpose:** Systematic review of the codebase to surface bugs, code smells, and opportunities — with the project's stated goal (a personal / company wiki that grows as the user adds files) and Karpathy's LLM Wiki pattern as the lens.
**Technical implementation:** `AUDIT.md` added at repo root. Findings grouped into P0 (correctness bugs — fix now), P1 (latent bugs / code smells), and P2 (directional improvements, many Karpathy-inspired). The P0 and P2-1 items are fixed in this session; the rest are documented for follow-up. (`AUDIT.md`)

### Fix: Shared mutable state across GraphRAGStore instances
**Purpose:** `community_summaries`, `entity_wikis`, and `node_community` were declared as class-level mutable defaults. Because `SimplePropertyGraphStore` is an ABC (not a Pydantic model), every `GraphRAGStore()` shared the same three dicts — so topic A's summaries could leak into topic B, particularly once per-request rebuilds became common.
**Technical implementation:** Added a real `__init__` that calls `super().__init__()` and then rebinds each of the four dicts (including the new `entity_index`) to a fresh per-instance dict. Verified the fix in isolation: two instances now hold independent state. (`app/graph_store.py`)

### Fix: `/no_think` prefix removed from extraction prompt
**Purpose:** `log.md` (2026-04-18) documented that `/no_think` confused LM Studio and was dropped from community prompts, but the same prefix was still being prepended to extraction prompts in `build_extraction_prompt()`.
**Technical implementation:** Non-thinking branch now returns `base` unchanged. Comment left in place explaining the decision. (`app/pipeline.py`)

### Fix: Domain-specific rules removed from `_normalize_name`
**Purpose:** The deduplication normaliser hard-coded rules that were written for the MMM corpus — `\bmodel\b → modeling`, `odels → odeling`. On any other topic these would silently merge distinct entities (e.g. "Pricing Model" with "Pricing Modeling"). For a system meant to handle arbitrary domains, that's data corruption.
**Technical implementation:** Replaced the ad-hoc rules with a small, documented `_SPELLING_NORMALISATIONS` map covering only safe British→American mappings (odelling→odeling, rganisation→rganization, ptimisation→ptimization, nalyse→nalyze, ehaviour→ehavior). Whitespace and parenthetical stripping retained. Any domain-specific synonyms now belong in `ontology.aliases`. (`app/graph_store.py`)

### Fix: UI `max_tokens` setting now actually sent to the server
**Purpose:** The settings modal collects a `max_tokens` value, `saveLLMConfig()` writes it to `sessionStorage`, but `llmPayload()` never forwarded it. The server always fell back to `.env`, so users' UI setting was a no-op.
**Technical implementation:** `llmPayload()` now includes `max_tokens` when set. (`app/static/js/app.js`)

### Fix: Consistent string-keyed community IDs end-to-end
**Purpose:** `build_communities()` stored `community_summaries[int]`, but `communities.json` round-trips keys as strings, and `node_community.get(node_id)` returned `int` — so downstream lookups only worked by accident (via try-both fallbacks). Moving to one consistent key type removes a whole class of subtle misses.
**Technical implementation:** `self.node_community` now stores `str(cluster)`; `community_summaries` is written with `str(community_id)` keys; the JSON-patch path in `load()` normalises existing files to str keys; old pickles with int values are coerced on load. Lookup sites in `main.py` and `generate_entity_wiki()` simplified to single `get(str(cid), "")`. (`app/graph_store.py`, `app/main.py`)

### Fix: `build_context` safely escaped before prompt templating
**Purpose:** User-supplied build context was f-string-interpolated into an extraction prompt that was then fed to LlamaIndex `PromptTemplate`. If the user's context contained a `{` or `}` (e.g. a JSON example), `.format()` would crash at extraction time — sometimes days after the bad context was entered.
**Technical implementation:** Double every brace in `build_context` via `.replace("{", "{{").replace("}", "}}")` before embedding it into the prompt. (`app/pipeline.py`)

### Fix: Deterministic Leiden clustering
**Purpose:** `hierarchical_leiden` was called with default RNG, so the same graph could produce a different community partition on each rebuild. Made "why did this answer change?" unnecessarily hard.
**Technical implementation:** Passed `random_seed=42`. Partition is now stable across identical rebuilds. (`app/graph_store.py`)

### Feat: Provenance tracking on entity nodes
**Purpose:** When multiple documents mention the same entity, the old upsert appended descriptions but threw away the source filename — so users couldn't tell which of their files contributed to a given wiki article. A core requirement for treating this as a trusted company/personal wiki.
**Technical implementation:** `upsert_nodes_merge()` now maintains a `sources: list[str]` property on each `EntityNode`, seeded on first insert and extended (without duplicates) on every subsequent merge. Source is derived from the node's `filename` or `source` metadata. Consumed by the new graph index and available to future UI surfaces. (`app/graph_store.py`)

### Feat: Graph index — catalog for fast LLM + human navigation
**Purpose:** User request: "I want it to have an index in each graph to help the LLM quickly navigate in the content." Inspired by Karpathy's `index.md` pattern — a catalog layer that lets the LLM (and the user) see the shape of the graph at a glance without having to re-read every community summary.
**Technical implementation:**
- `GraphRAGStore.build_index()` derives a compact structure from the in-memory graph (no extra LLM calls): `{entities: {id → {name, type, description, degree, community, sources}}, by_type, by_community, top_hubs, type_counts}`. Stored on `self.entity_index`.
- `render_index_markdown()` returns a human-friendly `index.md` — title, counts, top hubs, then entities grouped by type with one-line summaries. Works directly in Obsidian / grep.
- `index_digest()` returns a short, prompt-ready digest (names by type, capped per type) for injection into the LLM context.
- `save()` now writes `graph_index.json` and `index.md` alongside existing artifacts.
- `load()` reads `graph_index.json` when present, and falls back to building the index on the fly so pre-existing graphs get an index without a rebuild.
- `build_topic_graph()` calls `build_index()` after community detection.
- `GraphRAGQueryEngine._aggregate()` injects the `index_digest` into the final synthesis prompt when available — so the LLM sees a list of entities it can cite alongside the community answers.
- `_select_candidates()` boosts communities whose entities match query keywords (using `entity_index`), not just communities whose summary text matches — fixing the "relevant entity buried in a community whose summary doesn't mention it by name" case.
- New endpoint `GET /api/topics/{topic}/index` returns the JSON index (lazy-regenerates for older graphs).
(`app/graph_store.py`, `app/pipeline.py`, `app/query_engine.py`, `app/main.py`)

### Feat: Shared balanced-brace JSON extractor
**Purpose:** Both `GraphRAGExtractor._parse_json_result` and `resolve_entities` relied on the greedy regex `re.search(r"\{.*\}"|r"\[.*\]")`, which fails on LLM output that includes code fences, multiple JSON blocks, or trailing chatter. One good parser in one place replaces two brittle ones.
**Technical implementation:** Module-level helpers `_strip_code_fences`, `_extract_balanced`, `extract_json_object`, and `extract_json_array` added to `app/graph_store.py`. The balanced-brace scanner honours string literals so a `}` inside a quoted description doesn't close a block prematurely. `pipeline._parse_json_result` and `resolve_entities` now call these helpers. (`app/graph_store.py`, `app/pipeline.py`)

### Feat: Character-budgeted batching in `resolve_entities`
**Purpose:** A fixed `batch_size=60` caused context overflows on graphs with long descriptions and missed opportunities to batch more aggressively on short ones. Batching should respect the actual prompt size, not just entity count.
**Technical implementation:** `resolve_entities` now builds batches honouring both `max_entities_per_batch` (60) and a `char_budget` (6000) — whichever limit is hit first closes the current batch. (`app/graph_store.py`)

### Fix: Dedupe redundant relations after node merge
**Purpose:** Merging nodes often produced multiple `(source, label, target)` relations with identical endpoints — the graph carried the same edge many times with slightly different descriptions, bloating the visualisation and the community summaries.
**Technical implementation:** `deduplicate_nodes` now collapses duplicates by `(source, label, target)`, concatenating non-duplicate description text onto the surviving relation so no evidence is lost. Log line reports both node and relation counts. (`app/graph_store.py`)

### Fix: `base_url` honoured for the OpenAI provider
**Purpose:** Setting `base_url` while leaving provider on `openai` (e.g. pointing at LiteLLM or an Azure OpenAI-compatible gateway) silently fell through to `api.openai.com`. The UI field was misleadingly non-functional in that combination.
**Technical implementation:** `make_llm` in `task_manager.py` now forwards `api_base` to the `OpenAI` client when the user supplies a base URL, in addition to the existing `OpenAILike` path for non-OpenAI providers. (`app/task_manager.py`)

### Feat: Fenced code block rendering in chat
**Purpose:** When answers contained ```code blocks```, they rendered as raw text with the backticks visible. Common for technical queries that quote config or commands.
**Technical implementation:** `renderMarkdown` in `app.js` tracks an `inCode` state on triple-backtick fences, captures content verbatim, and emits `<pre class="chat-pre"><code class="lang-*">…</code></pre>`. Unclosed fences still render (no silent content loss). Styles added for `.chat-pre`. (`app/static/js/app.js`, `app/static/css/style.css`)

### Feat: `serverConfig` refreshed on topic change
**Purpose:** The server's `/api/config` was only fetched at page load. If the backend was restarted with a new `.env` while the tab stayed open, the client kept gating build/query on the stale "no server config" signal and nagged the user to open settings.
**Technical implementation:** `onTopicChange` in `app.js` re-fetches `/api/config` in the background; failure is silent and falls back to the cached value. (`app/static/js/app.js`)

### Feat: `build_context` persisted per topic and prefilled in UI
**Purpose:** The build-context textarea asked the user to describe their topic on *every* build. For a wiki that accumulates files over time, retyping the same paragraph is friction that discourages incremental builds.
**Technical implementation:** `build_topic_graph` writes `build_context.txt` in the topic directory when a context is supplied. New endpoint `GET /api/topics/{topic}/build_context` returns it. `openContextModal` now accepts a topic argument and prefills the textarea from that endpoint. (`app/pipeline.py`, `app/main.py`, `app/static/js/app.js`)

### Feat: Provenance shown in the node modal
**Purpose:** With `sources` now tracked on every node, users should be able to see at a glance which files contributed to an entity — the trust signal that makes the graph actually usable as a wiki.
**Technical implementation:** `POST /api/topics/{topic}/nodes/{node_id}` now returns `sources`. The node modal renders them as a row of pill-style chips after the cluster context section. Styles added for `.nm-sources` and `.nm-source-chip`. (`app/main.py`, `app/static/js/graph.js`, `app/static/css/style.css`)

### Feat: `/api/topics/{topic}/health` structural check
**Purpose:** A "is this graph healthy?" view without running the LLM — useful for spotting orphan entities, dangling relations, or a flood of `OTHER`-typed nodes that signal the ontology needs tightening.
**Technical implementation:** New endpoint computes node/edge/community counts, orphan nodes (no relations), dangling relations (endpoints removed), typed ratio (entities with a non-`OTHER` label), plus a small preview of orphan IDs. All derived from the in-memory store, zero LLM calls. (`app/main.py`)

---

### Chore: CLAUDE.md, log.md, karpathy gist.md added
**Purpose:** Establish session memory, change tracking, and reference material for the Karpathy LLM Wiki pattern that inspired the wiki article feature.
**Technical implementation:** `CLAUDE.md` documents run commands, architecture, key constraints. `log.md` tracks changes per session. `karpathy gist.md` is the source reference. All committed to repo.
