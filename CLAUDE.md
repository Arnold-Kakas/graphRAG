# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Always read `log.md` at the start of each session** to understand what was recently changed before making further modifications.
>
> **When adding entries to `log.md`**, always use this structured format:
> ```
> ### [Type]: [Short name]
> **Purpose:** Why this change was made — the problem it solves or goal it achieves.
> **Technical implementation:** What was changed and how — files, methods, key decisions.
> ```

---

## Running the App

**Docker (recommended):**
```bash
docker-compose up --build
# App available at http://localhost:8000
```

**Local (no Docker):**
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Environment:** Copy `.env.example` → `.env` and set at minimum:
- `OPENAI_API_KEY=sk-...` for OpenAI, **or**
- `LLM_BASE_URL=http://localhost:1234/v1` for LM Studio / `http://localhost:11434/v1` for Ollama (leave key blank)

For Docker with local LLM, use `host.docker.internal` instead of `localhost`.

No automated tests or lint configuration exist in this repo.

---

## Architecture Overview

### Data Flow

```
raw/<topic>/*.pdf|docx|html|txt|md|csv
    ↓  DocumentParser  (app/parser.py)
    ↓  _summarise_document()  — 1 LLM call, compresses doc to rich summary
    ↓  GraphRAGExtractor.extract()  — 1 LLM call, entities + relationships from summary
         (2 calls total per doc; NUM_WORKERS parallel)
    ↓  GraphRAGStore.upsert_nodes_merge() — description-merging upsert
    ↓  GraphRAGStore.resolve_entities() + deduplicate_nodes()  — LLM synonym merge
    ↓  GraphRAGStore.build_communities()  — Leiden clustering + LLM summaries + node_community map
    ↓  save() → graphs/<topic>/{store.pkl, graph_data.json, communities.json, entity_wikis.json, ...}
    ↓  GraphRAGQueryEngine.custom_query()
         Phase 1: keyword pre-filter → top 15 community summaries → parallel LLM relevance check
         Phase 2: llm synthesises relevant summaries into final answer
    ↓  GET /api/topics/{topic}/nodes/{node_id}?generate=true
         On-demand wiki article via generate_entity_wiki() — cached in entity_wikis.json
```

### Module Responsibilities

| File | Role |
|---|---|
| `app/main.py` | FastAPI routes, topic discovery, query engine cache (`_query_engines` dict), lazy `graph_data.json` regeneration |
| `app/config.py` | Pydantic Settings from `.env`; all tunable knobs live here |
| `app/models.py` | Pydantic schemas for API request/response, `OntologyConfig` (entity/relation types + aliases), `LLMConfig` (per-request, never persisted) |
| `app/pipeline.py` | `build_topic_graph()` orchestrator; hybrid 2-call-per-doc pipeline (`_summarise_document` → `GraphRAGExtractor.extract`); incremental build via `manifest.json` mtime tracking |
| `app/graph_store.py` | `GraphRAGStore(SimplePropertyGraphStore)`; `upsert_nodes_merge()`; community detection + `node_community` map; `generate_entity_wiki()` async on-demand article generation; save/load (pickle + JSON); D3 export |
| `app/query_engine.py` | `GraphRAGQueryEngine`; keyword pre-filter (`_select_candidates`) caps at 15 communities; two-phase fan-out/aggregate with 120s timeout |
| `app/task_manager.py` | `TaskManager` runs builds in background threads; `make_llm()` factory for OpenAI vs OpenAILike |
| `app/parser.py` | Per-format text extraction (PyMuPDF, python-docx, Trafilatura) |
| `app/static/js/app.js` | Topic list, build trigger, chat UI, LLM settings modal (sessionStorage only — keys never sent outside request body) |
| `app/static/js/graph.js` | D3.js v7 force-directed graph; color by entity type; node size by degree |

### Persisted Files per Topic (`graphs/<topic>/`)

| File | Contents |
|---|---|
| `store.pkl` | Full `GraphRAGStore` pickle (fast reload, includes all nodes/edges/community_summaries/node_community) |
| `communities.json` | `{"0": "summary...", "1": "summary...", ...}` — one LLM-generated paragraph per Leiden cluster |
| `entity_wikis.json` | `{node_id: "article text..."}` — cached on-demand wiki articles; written after first double-click generation |
| `graph_data.json` | D3-ready `{nodes:[{id,label,type,description}], links:[{source,target,label}], communities:N}` |
| `build_meta.json` | Build stats (node_count, edge_count, community_count, built_at) — source for the status bar |
| `manifest.json` | Per-file mtime snapshot — drives incremental build skip logic |
| `ontology.json` | Entity/relation type lists used during the build |

### Key Architectural Constraints

**Stale `graph_data.json`:** The pickle and `communities.json` are ground truth. `graph_data.json` can be stale if a prior build saved it before communities were built. The `/api/topics/{topic}/graph` endpoint lazily regenerates it when `communities == 0` but `communities.json` exists.

**LLM client selection:** `make_llm()` in `task_manager.py` returns `OpenAI` for the OpenAI provider and `OpenAILike` (bypasses model name validation) for all others. The `community_llm` is the extraction model; `llm` is the query model.

**Thinking models:** `GraphRAGExtractor` detects `</think>` output and falls back from `astructured_predict()` to plain-text extraction + regex JSON parse. Do NOT add `/no_think` prefix to community prompts — LM Studio ignores it and it causes longer/confused responses (reverted after testing).

**Per-request LLM config:** The frontend stores user API keys in `sessionStorage` and sends them in the request body only. `_get_query_engine()` in `main.py` always creates a fresh engine (bypasses cache) when a per-request key is present.

**Incremental builds:** `build_topic_graph()` compares current file mtimes against `manifest.json`. Unchanged files are skipped entirely. Force-rebuild flag bypasses this.

---

## Important Config Knobs

| Env Var | Default | Effect |
|---|---|---|
| `NUM_WORKERS` | 4 | Extraction parallelism — set to 1 for slow/local models |
| `MAX_CLUSTER_SIZE` | 10 | Leiden cluster cap; larger = fewer, broader communities |
| `MAX_DOCUMENTS` | 50 | Hard cap per full build |
| `LLM_CONTEXT_WINDOW` | 8192 | Must match local model's actual context size |
| `LLM_REQUEST_TIMEOUT` | 300 | Seconds; increase for large local models |
