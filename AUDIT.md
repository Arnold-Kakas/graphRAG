# GraphRAG Audit — 2026-04-20

A walk-through of the project as it stands at `main@fabf78c`, with the aim of (a) surfacing correctness bugs, (b) finding room for improvement, and (c) pointing the project toward its stated goal: **a personal / company wiki that grows as the user adds more files** — partly inspired by Karpathy's LLM Wiki gist.

Findings are grouped by tier:

- **P0** — correctness or data-integrity bugs; fix now.
- **P1** — latent bugs, UX gaps, or code smells that will bite soon.
- **P2** — opportunities and larger directional improvements (many Karpathy-inspired).

Items marked ✅ are fixed in the same session as this audit; see `log.md` for the diffs.

---

## P0 — Correctness bugs

### ✅ P0-1 · Shared mutable state across `GraphRAGStore` instances
**Where:** `app/graph_store.py:40-42`
```python
class GraphRAGStore(SimplePropertyGraphStore):
    community_summaries: dict = {}
    entity_wikis: dict = {}
    node_community: dict = {}
```
These are **class attributes**, not instance attributes. Every `GraphRAGStore()` shares the same three dicts unless the instance explicitly rebinds them. When two topics are loaded in the same process (e.g. the cached `_query_engines` dict + a per-request rebuild with session LLM config), one topic's summaries can appear inside another's. This is almost certainly already causing subtle bleed on long-running servers.
**Fix:** instance-level init (`__init__`) so each store has its own dicts.

### ✅ P0-2 · `/no_think` prefix still injected after it was rejected
**Where:** `app/pipeline.py:118-119`
```python
if thinking: return base
else: return "/no_think\n" + base
```
`log.md` (2026-04-18 session 1) documents: *"`/no_think` prefix was attempted but reverted — LM Studio didn't recognise it and caused longer/confused responses."* The code still adds it on the default path. Community-summary prompts were cleaned up; extraction prompts were not.
**Fix:** drop the prefix.

### ✅ P0-3 · Domain-specific rules hard-coded in `_normalize_name`
**Where:** `app/graph_store.py:264-271`
```python
n = n.replace("odelling", "odeling")
n = n.replace("odels", "odeling")         # ← merges plural with activity
n = re.sub(r"\bmodel\b", "modeling", n, ...) # ← merges "Climate Model" with "Climate Modeling"
```
These rules were written for the `marketing mix modeling` corpus. They will merge unrelated concepts in every other topic ("Pricing Model" ≠ "Pricing Modeling"; "Transformer Models" ≠ "Transformer Modeling"). For a system that's meant to grow across arbitrary domains, this is a silent data-corruption bug.
**Fix:** keep only safe, domain-neutral normalisation (whitespace/case, parentheticals, British→American for a small curated set). Move corpus-specific aliases into `ontology.aliases`.

### ✅ P0-4 · UI `max_tokens` setting is ignored
**Where:** `app/static/js/app.js:239-249` (`llmPayload`)
The settings modal collects `max_tokens`, `saveLLMConfig()` stores it in `sessionStorage`, but `llmPayload()` never copies it into the outgoing request body. Users think the slider works; server-side `make_llm()` falls back to `.env` every time.
**Fix:** include `max_tokens` in `llmPayload()`.

### ✅ P0-5 · `community_summaries` / `node_community` key-type mismatch
**Where:** `app/graph_store.py:188` (writes int keys), `app/graph_store.py:487-490` (reads string keys from JSON)
`build_communities()` stores `community_summaries[cluster_id: int]`, but `communities.json` serialises keys as strings, and `load()` patches them back verbatim. Then `node_community.get(node_id)` returns an `int`, while `community_summaries` now has `str` keys — lookup misses. The query engine and wiki generator each paper over this with try-both fallbacks, but they aren't consistent and future callers will break.
**Fix:** standardise on `str` keys at the boundary — cast on insert, cast on lookup. Do it in one place: the store.

---

## P1 — Latent bugs / code smells

### ✅ P1-1 · `build_context` can inject unescaped `{` / `}` into `PromptTemplate`
**Where:** `app/pipeline.py:62-114`. The extraction prompt is built with an f-string that produces literal `{text}` and `{max_knowledge_triplets}` placeholders for LlamaIndex's `PromptTemplate`. A `build_context` containing a curly brace (e.g. a JSON example) will crash `.format()` at extraction time.
**Fix:** `build_context.replace("{", "{{").replace("}", "}}")` before embedding.

### ✅ P1-2 · Leiden clustering has no seed → non-reproducible communities
**Where:** `app/graph_store.py:86`. `hierarchical_leiden(nx_graph, max_cluster_size=...)` uses default RNG. The same graph can produce a different community partition on each rebuild, which makes debugging "why did this answer change?" nearly impossible.
**Fix:** pass a fixed `random_seed` (e.g. 42). Let it be a config knob.

### P1-3 · Incremental build discards existing community structure unnecessarily
**Where:** `app/pipeline.py:310-402`. When `is_incremental` is true, the store is loaded from pickle but `build_communities()` is re-run from scratch, and **every** community summary is re-generated by the LLM — even for clusters that only changed by one node (or didn't change at all).
**Fix:** opportunistic caching — hash the member-ID set of each cluster and reuse the cached summary when unchanged. Medium-size change; big win for incremental ingest speed.

### ✅ P1-4 · `_parse_json_result` uses greedy regex and silently fails on multiple blocks
**Where:** `app/pipeline.py:158-170`. `re.search(r"\{.*\}", text, re.DOTALL)` is greedy, so if a model outputs `{...} \n\n Explanation: {...}` it will swallow both and `json.loads` will throw. Caught by the broad `except`, so you just lose that chunk silently.
**Fix:** try balanced-brace scan first, fall back to greedy.

### ✅ P1-5 · `upsert_nodes_merge` doesn't carry over source metadata
**Where:** `app/graph_store.py:46-58`. When a node exists, the new node's `source`, `filename`, etc. are thrown away — only the description is merged. The wiki has **no provenance**: you cannot see which source files contributed to a given entity's description.
**Fix:** maintain a `sources: list[str]` property on each node, de-duplicated.

### ✅ P1-6 · Duplicate relations are not merged
**Where:** `app/graph_store.py:343-401` (`deduplicate_nodes`). After node merge, two edges between the same pair with the same label survive as distinct relations. Edge counts are inflated and the D3 view draws overlapping lines.
**Fix:** after re-targeting, key relations by `(src, rel, tgt)` and drop duplicates (merge descriptions).

### P1-7 · Pickle-based store load is fragile & a mild security risk
**Where:** `app/graph_store.py:480-510`. `pickle.load` will execute arbitrary code if `store.pkl` is ever swapped out (e.g. if the `graphs/` dir is shared). Also, any change to the `GraphRAGStore` class signature breaks every old pickle. Already biting: you had to add the `load()` patch for missing `community_summaries`.
**Fix (longer-term):** switch to a fully JSON-serialised store. Parent's `SimplePropertyGraphStore` supports this.

### ✅ P1-8 · `llm_base_url` forwarded only to non-OpenAI providers
**Where:** `app/task_manager.py:40-107`. If user picks provider `openai` and sets a custom base URL (Azure, proxy, vLLM with OpenAI shim), the `base_url` is ignored.
**Fix:** respect `llm_config.base_url` for the OpenAI provider too, by passing `api_base=` to `OpenAI()`.

### P1-9 · `DocumentParser.parse_topic` raises `FileNotFoundError` → surfaces as 500
**Where:** `app/parser.py:28` then propagated from `task_manager._run_build`. Should be a graceful build-level error message.
**Fix:** catch + set `TaskState.error` cleanly (already the behaviour via the outer `except`; verify the user-facing message is helpful).

### ✅ P1-10 · `renderMarkdown()` doesn't handle fenced code blocks
**Where:** `app/static/js/app.js:531-609`. LLM answers containing ```python``` fences render as raw text. Not urgent for a marketing-modeling corpus but will matter for technical topics.

### ✅ P1-11 · `serverConfig` fetched only on page load
**Where:** `app/static/js/app.js:14`. If the user edits `.env` and restarts the server, the page still reports the old state until the browser tab is reloaded.

### ✅ P1-12 · No seed / size limits on `resolve_entities` batch prompt
**Where:** `app/graph_store.py:297`. 60 entities × up to 120-char descriptions = ~7kB per prompt. Fine for OpenAI, but a local 8k-context model only has ~1k tokens headroom for the rest of the system/instruction tokens. Should cap by character budget, not by fixed count.

---

## P2 — Improvements and Karpathy-inspired directions

### ✅ P2-1 · Add a **graph index** to help the LLM navigate (feature requested)
Karpathy's `index.md` is a catalog the LLM reads before answering — it's what gives the pattern scale at ~100 sources. This project doesn't have one; community summaries alone lose track of individual entity names. Implemented in this session:
- `GraphRAGStore.build_index()` emits `graph_index.json` (machine-readable) and `index.md` (human-readable).
- Query engine injects a compact form of the index into the final aggregation prompt, so the LLM sees *what entities exist* before it stitches community answers together.
- New endpoint `GET /api/topics/{topic}/index` for the frontend / external tools.

### P2-2 · Per-topic `log.md` / activity ledger
Karpathy's `log.md` pattern: every ingest, every query, every lint pass gets one line. Would let the user see "22 ingests, 40 queries, last rebuild 2 days ago, drift detected in 3 entities". For this project, that's a small addition to `build_topic_graph()` — append an entry to `graphs/<topic>/log.md` each time. Not yet done.

### ✅ P2-3 · **Provenance tracking** on entities and relations
Today, `entity_description` is concatenated across sources with no attribution. For a wiki that's meant to be trusted (especially in a business context), each sentence needs to point back to a source file. Track `sources: [filename, ...]` per node; render in the wiki modal; surface in chat citations. Implemented in this session: `sources` list maintained by `upsert_nodes_merge`, returned by the node endpoint, rendered as chips in the node modal.

### P2-4 · **Contradiction detection** at ingest
When merging descriptions via `upsert_nodes_merge`, the LLM could compare old vs new: if they disagree on a numeric claim, a date, or a categorical fact, flag it into a `contradictions.json` file. This is exactly the "the contradictions have already been flagged" promise from Karpathy. Implementation: one LLM call per merged node where the new description is non-trivially different.

### ✅ P2-5 · **Orphan / lint pass**
Karpathy's "lint" operation: find nodes with zero edges, communities with only one node, entities mentioned in relations but missing a description, entity types that appear only once. Expose as a "health report" in the UI. Implemented as `GET /api/topics/{topic}/health` (orphan count, dangling relations, typed ratio, orphans preview). UI surfacing of the report is still TODO.

### ✅ P2-6 · Richer retrieval — promote the index to a first-class retrieval signal
The current pre-filter is keyword overlap against **community summaries**. Better: also match keywords against individual **entity names and descriptions** (via the index), then rank communities by *how many matched entities they contain*. This sidesteps the "relevant entity is buried in a community whose summary doesn't mention it" failure mode.

### ✅ P2-7 · Embeddings fallback for large graphs
Keyword pre-filter is fine at 65 communities. At 500, it breaks down. Adding a local sentence-embedding model (`bge-small`, `e5-small`) and caching per-community embeddings gives sub-second top-K retrieval with no extra LLM cost. Implemented: `app/embeddings.py` wraps sentence-transformers behind `CommunityEmbeddingIndex`, caching per-summary vectors in `community_embeddings.json` (sha1-keyed for auto-invalidation). `_select_candidates` blends cosine similarity (×10) with keyword + index scores. Opt-in via `EMBEDDINGS_ENABLED=true`; `sentence-transformers` listed but commented out in `requirements.txt`.

### ✅ P2-8 · Chat-answers-become-wiki-pages
Karpathy's explicit recommendation: *"good answers can be filed back into the wiki as new pages."* Add a "📌 Pin as wiki page" button on each assistant answer that saves the Q/A into a `queries/` subdir or, better, attaches it to the relevant entities. This is the compounding-knowledge loop. Implemented as a lighter first cut: `pinned_answers.json` per topic via `GET/POST/DELETE /api/topics/{topic}/pinned`; pin button on each finalised answer; sidebar "Pinned answers" panel; click to replay a pinned Q&A back into the chat. Attaching to entities (deeper integration with `entity_wikis.json`) is still TODO.

### P2-9 · Git-versioned graphs
Each topic's `graphs/<topic>/` folder is already a natural git repo. Committing after each build gives free history, diff, and rollback. The frontend could show a "drift since last build" delta.

### ✅ P2-10 · Obsidian-compatible export
Export each entity as a markdown file with YAML frontmatter + `[[wiki links]]` to other entities. Dump into a folder the user can open in Obsidian. That instantly gives you a world-class navigation / graph-view / backlinks UI for free. Implemented: `GraphRAGStore.export_obsidian()` writes one `.md` per entity (frontmatter with `id`/`type`/`degree`/`community`/`sources`/`tags`, body with description + cached wiki + cluster context + neighbour wiki links), plus a top-level `_index.md`. `GET /api/topics/{topic}/export/obsidian` zips and serves it; sidebar has an "Obsidian vault (.zip)" button.

### P2-11 · Deterministic / reproducible builds
Beyond Leiden seed (P1-2): `temperature=0` is set in `make_llm`, but structured-predict still has model-side non-determinism. Cache prompts-by-hash keyed to model id so re-extraction of identical input is a no-op.

### P2-12 · Tests
The repo has no automated tests. At minimum: a unit test for `_normalize_name`, `_parse_json_result`, and `_select_candidates`. One fixture-based integration test for the build pipeline using a tiny fake LLM.

### ✅ P2-13 · UI polish
- ✅ Chat textarea auto-grows from 40px up to 200px on input; resets after send (`autosizeTextarea`).
- ✅ Fenced code block rendering (P1-10).
- ✅ Search reads the graph index — matches on label / type / description, ranks by match position then degree, surfaces cluster ID and link count per result.
- ✅ "Show provenance" on the wiki modal — always visible when sources exist.
- ✅ Build Context modal opens for incremental builds too (was previously gated to first builds and `force` rebuilds).

### ✅ P2-14 · CSV / structured-data ingestion beyond text columns
Current CSV handling flattens the whole table to a string, which is poor extraction material for analytical datasets. A better path: row-per-entity when a `type` column exists, or hand the CSV to the LLM with schema context. Implemented: `_parse_csv` picks one of three modes — `narrative` (text-column join), `entity_per_row` (markdown blocks when name + type columns exist), `table` (schema + capped key=value rows). The chosen mode is recorded in document metadata as `csv_mode`.

### ✅ P2-15 · Build context → persisted per topic
The user enters "focus & purpose" on every full rebuild; it's not stored. Implemented: pipeline now writes `graphs/<topic>/build_context.txt`, a `GET /api/topics/{topic}/build_context` endpoint returns it, and the context modal prefills the textarea on reopen.

---

## What's good about the project today

Worth noting so the improvements don't give the wrong impression:

- The **two-call-per-document pipeline** (summarise → extract) is a sensible trade — 4–6× the throughput of a naive chunk-per-call approach.
- **Incremental builds via `manifest.json` mtime tracking** are exactly right for a "keep adding files" workflow.
- Separating `community_llm` (cheap) from `llm` (strong) and running them in parallel with a timeout is the standard GraphRAG pattern and is implemented cleanly.
- The **node modal with on-demand wiki generation** is the thing that most resembles Karpathy's vision: a persistent, per-entity article that compiles what's known into a readable page. Caching in `entity_wikis.json` with a Regenerate button is the right UX.
- Separation of server settings vs. per-request `LLMConfig` (never persisted) is a good privacy decision and is respected throughout the code.
- `CLAUDE.md` and `log.md` already follow the Karpathy discipline — the schema-driven-LLM-behavior pattern is in place.

The project is closer to the pattern than it realises. The main gaps are (1) an index layer so the LLM can navigate without re-reading every community on every query, (2) provenance so the wiki can be trusted, and (3) turning the on-demand wiki articles + chat answers into first-class, inter-linked pages rather than per-entity modals.
