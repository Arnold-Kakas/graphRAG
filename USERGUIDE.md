# GraphRAG Explorer — User Guide

GraphRAG Explorer turns a folder of documents into a queryable knowledge graph. You drop in PDFs, Word files, web pages, spreadsheets, or plain text, choose a language model, and the app extracts the entities and relationships it finds, clusters them into thematic communities, and lets you explore everything through a chat interface, an interactive force-directed graph, and a set of export tools. This guide covers everything from first-time setup to advanced workflows.

---

## Table of Contents

1. [How it works — a plain-language overview](#how-it-works)
2. [Getting started](#getting-started)
3. [Configuring your LLM](#configuring-your-llm)
4. [Adding documents](#adding-documents)
5. [Building a graph](#building-a-graph)
6. [Merging entities](#merging-entities)
7. [Exploring the graph](#exploring-the-graph)
8. [Querying with chat](#querying-with-chat)
9. [Blog post generation](#blog-post-generation)
10. [Obsidian vault export](#obsidian-vault-export)
11. [Pinned answers](#pinned-answers)
12. [LLM settings (in-app)](#llm-settings-in-app)
13. [Tuning and troubleshooting](#tuning-and-troubleshooting)
14. [Use cases](#use-cases)

---

## How it works

When you build a graph, the app reads every document in your chosen topic folder and makes two LLM calls per document: one to compress the document into a rich summary, and a second to extract named entities (people, organisations, concepts, methods, events, and so on) and the relationships between them. Those entities and relationships are merged into a property graph.

Once the graph is built, a community detection algorithm (Leiden clustering) groups closely connected entities into clusters. The LLM then writes a short summary for each cluster, describing the theme it represents. These community summaries become the primary source material for answering questions — when you ask something in chat, the app finds the most relevant clusters, passes their summaries to the LLM, and the model synthesises a grounded answer.

Everything is persisted to disk so you never have to rebuild from scratch unless you want to. Adding new documents only processes the files that changed.

---

## Getting started

### Docker (recommended)

Docker is the easiest way to run GraphRAG Explorer because it handles all Python dependencies for you.

```bash
git clone <repo-url>
cd graphRAG
cp .env.example .env
# Edit .env — see "Configuring your LLM" below
docker compose up --build
```

The app starts at `http://localhost:8000`. The first `--build` takes a few minutes; subsequent starts are much faster.

Two folders on your host machine are mounted into the container:

- `./raw` maps to `/app/raw` inside the container — this is where your documents go.
- `./graphs` maps to `/app/graphs` inside the container — this is where the app writes graph artifacts. Both folders persist across container restarts.

You do not need to restart the container after adding documents. The Docker volume mount means any file you drop into `raw/` is immediately visible to the running app.

### Local (no Docker)

If you prefer to run without Docker:

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env
uvicorn app.main:app --reload
```

---

## Configuring your LLM

The app works with OpenAI, Anthropic (Claude), Google Gemini, LM Studio, Ollama, or any endpoint that speaks the OpenAI API format. Configuration goes in your `.env` file before starting the app. You can also override these settings per-session from inside the browser — see [LLM settings (in-app)](#llm-settings-in-app).

### OpenAI

```env
OPENAI_API_KEY=sk-...
EXTRACTION_MODEL=gpt-4o-mini
QUERY_MODEL=gpt-4o
```

`EXTRACTION_MODEL` is used during graph building (the heavier workload, many parallel calls). `QUERY_MODEL` is used for chat queries and blog generation. Using a cheaper model for extraction and a smarter one for queries is a sensible cost-saving split.

### Anthropic (Claude)

```env
OPENAI_API_KEY=not-needed
LLM_PROVIDER=anthropic
EXTRACTION_MODEL=claude-haiku-4-5-20251001
QUERY_MODEL=claude-sonnet-4-6
```

### LM Studio (fully local, no data leaves your machine)

Start LM Studio, load a model, enable "Serve on local network," and click the green Start button. Then:

```env
OPENAI_API_KEY=not-needed
LLM_BASE_URL=http://host.docker.internal:1234/v1
EXTRACTION_MODEL=your-model-name
QUERY_MODEL=your-model-name
LLM_CONTEXT_WINDOW=8192
LLM_MAX_TOKENS=8192
```

The hostname `host.docker.internal` routes from inside the Docker container to your host machine where LM Studio is running. On Linux, Docker does not resolve this automatically — see the note below.

### Ollama (fully local)

```env
OPENAI_API_KEY=not-needed
LLM_BASE_URL=http://host.docker.internal:11434/v1
EXTRACTION_MODEL=llama3.2
QUERY_MODEL=llama3.2
```

> **Linux Docker networking note:** `host.docker.internal` does not resolve automatically on Linux. Add the following to your service in `docker-compose.yml`, or use your machine's LAN IP address instead:
> ```yaml
> extra_hosts:
>   - "host.docker.internal:host-gateway"
> ```

---

## Adding documents

GraphRAG Explorer organises documents into topics. Each topic is a subfolder of `raw/` on your host machine, and the folder name becomes the topic name shown in the app's dropdown. Use underscores or hyphens instead of spaces — for example, `raw/marketing_mix_modeling/` or `raw/q1-earnings-calls/`.

Supported file formats are `.pdf`, `.docx`, `.html`, `.htm`, `.txt`, `.md`, and `.csv`.

To add documents, simply copy or move files into the appropriate `raw/<topic>/` folder. Because the folder is a live Docker volume mount, the app sees the files immediately — no container restart needed. Select the topic in the UI dropdown and click Build Graph.

A few tips on organising topics well: keep each topic focused on one coherent subject area. A topic mixing climate policy papers with product marketing briefs will produce confused communities and weaker answers. It is better to maintain separate topics (`raw/climate_policy/`, `raw/product_marketing/`) and query each independently.

---

## Building a graph

Select a topic from the dropdown in the app header, then click **Build Graph**. The build panel offers a few options:

**Focus and Purpose.** An optional free-text field that biases the LLM during extraction. If you are building a graph of economics papers and you primarily care about policy implications, describe that here. Leave it blank for a general-purpose extraction.

**Reasoning model.** Tick this checkbox if you are using a thinking/reasoning model such as DeepSeek R1, QwQ, Phi-4-reasoning, or similar. These models produce extended chain-of-thought output wrapped in `<think>` tags before their final answer. The checkbox switches the extraction pipeline to handle that output correctly and also reduces batch sizes to prevent the model from looping indefinitely through large entity lists.

**Full rebuild.** By default the app performs an incremental build: it compares each file's modification timestamp against a saved manifest and skips any file that has not changed. This makes adding a handful of new documents to a large topic fast. Ticking Full rebuild discards the existing graph entirely and re-extracts everything from scratch. Use this after making significant changes to the ontology or after editing the Focus and Purpose.

Progress is shown in the status bar at the bottom of the screen. Build time scales with the number of documents and the speed of your LLM — a 50-document topic on a fast API model typically takes a few minutes; a slow local model on the same corpus may take much longer.

### Ontology customisation

Each topic's graph comes with an `ontology.json` file stored in `graphs/<topic>/`. This file defines the entity types and relationship types the LLM should use, and lets you pin hard-coded aliases (`"Facebook": "Meta"`, `"MMM": "Marketing Mix Modeling"`). The first build creates a sensible default. You can edit `ontology.json` and run a full rebuild to apply your changes.

---

## Merging entities

After a build, the graph often contains near-duplicate nodes — "Marketing Mix Modeling" alongside "Marketing Mix Model", or "ROAS" alongside "Return on Ads Spend". The **Merge entities** button in the header runs a separate LLM-based synonym resolution step to collapse these duplicates.

Merge is intentionally separate from the build step. Builds are already the expensive part, and synonym resolution adds another layer of LLM calls. Keeping them separate lets you inspect the raw graph first, then decide to merge when you are happy with the underlying extraction.

When you click Merge entities, the app loads the existing graph, runs rule-based normalisation (catching spelling variants, gerund/noun swaps, and acronym expansions automatically), then runs one or two LLM passes to find semantic synonyms the rules missed. Merged pairs are saved to `graphs/<topic>/learned_aliases.json`. On every subsequent incremental build, those saved aliases are reapplied for free — the LLM only pays the resolution cost once per synonym pair.

When two nodes are merged, their descriptions are combined and then re-summarised by the LLM to produce a clean, non-redundant description for the winning node.

---

## Exploring the graph

The main panel of the app shows an interactive D3 force-directed graph of all entities and relationships.

**Navigation.** Pan by clicking and dragging the background. Zoom with the scroll wheel. Drag individual nodes to reposition them. The graph stabilises through a physics simulation — if it feels too crowded, give it a moment to settle, or use the sidebar sliders to adjust link distance and node repulsion.

**Visual encoding.** Node colour represents entity type (the legend in the sidebar lists all types; click any type to hide or show that group). Node size represents degree — the more connections a node has, the larger it appears. This makes it easy to spot the most central concepts at a glance.

**Sidebar controls.** The sidebar contains sliders for link distance, node spacing, and edge-label density (how many relationship labels are shown before they become too cluttered). The Reset zoom button returns the view to the default framing, and Show all makes all hidden nodes visible again.

**Search.** The search bar in the sidebar lets you find entities by name, type, or description. Results are ranked by match quality — exact label matches come first, then prefix matches, then partial matches, then type and description hits — with ties broken by degree so well-connected hubs surface before obscure nodes. Each result shows the node's degree (number of connections) and its cluster ID.

**Node detail panel.** Click any node to open a detail panel on the right side of the screen. This shows the entity's description, the source documents it was extracted from, its community (cluster) membership, and all of its incoming and outgoing relationships.

**Wiki article generation.** Double-click any node to generate a 3-to-5-paragraph Wikipedia-style article for that entity. The article is synthesised from the node's description, its relationships, and the community summary for its cluster. Generation takes a few seconds. Once generated, the article is cached in `graphs/<topic>/entity_wikis.json` so subsequent double-clicks load it instantly.

---

## Querying with chat

The chat panel on the left lets you ask natural language questions about the topic. The app searches the community summaries for the most relevant clusters, then passes those summaries to the LLM to synthesise an answer.

**Graph only mode** (the default) keeps the LLM strictly grounded in the graph. If the graph does not contain enough information to answer your question confidently, the model says so rather than guessing. Sentences in the answer that are not supported by the graph evidence are filtered out automatically.

**Graph + AI knowledge mode** allows the LLM to draw on its own training knowledge to fill gaps the graph does not cover. In this mode, the answer is visually split into two sections: "From the knowledge graph" and "From AI knowledge," so you can see at a glance which claims are grounded in your documents and which are not.

Responses stream token by token as they are generated. Entity names mentioned in an answer are rendered as clickable chips — click one to pan the graph to that node and highlight it. Below each answer you can see which community clusters contributed to it; expand any cluster to read its full summary.

**Pinning answers.** If an answer is useful, click the pin icon to save it. Pinned items appear in the sidebar and persist in `graphs/<topic>/pinned_answers.json` across sessions. Click any pinned item to replay the question and answer into the chat.

---

## Blog post generation

In the sidebar, under the Export section, click **Write Blog Post** to open the blog generator.

You are prompted for your angle and ideas (what aspect of the topic do you want to write about, who is the audience, what argument do you want to make), an optional structural outline, and a target length: Short (around 500 words), Medium (around 1000 words), or Long (around 1800 words).

The generator pulls the top 20 community summaries by relevance, the top 30 entities by centrality, and the top 40 relationships from the graph, along with a numbered list of source documents as provenance. These become the grounding material for the LLM.

The post streams live in a full-screen overlay. If the model generates `chartjs` code blocks, those are rendered as interactive Chart.js charts (bar, line, pie, and other types) directly inside the blog preview. Source citations appear as footnote superscripts traced back to the original documents.

When generation is complete, two export buttons appear:

**Export MD** downloads the raw markdown so you can edit it in any text editor or paste it into a CMS.

**Export HTML** produces a standalone HTML file with Chart.js loaded from a CDN, all chart scripts inlined, and clean readable CSS. This file can be opened in any browser, pasted into WordPress, Ghost, Substack, or any other platform that accepts raw HTML.

---

## Obsidian vault export

In the sidebar under Export, click **Obsidian vault (.zip)** to download a zip archive structured for Obsidian.

The archive contains one Markdown file per entity. Each file has YAML frontmatter with the entity type, cluster ID, and degree; `[[wiki links]]` to all neighbouring entities; a section showing the community summary for the entity's cluster; and the cached wiki article if one has been generated for that node.

Unzip the archive into any Obsidian vault folder. Obsidian's graph view will immediately show the network of backlinks, and the local graph for any note will show its immediate neighbours.

---

## Pinned answers

Any answer in chat can be pinned using the pin button that appears below the response. Pinned answers appear as a list in the sidebar and are written to `graphs/<topic>/pinned_answers.json`, so they survive page refreshes and browser restarts. Click any pinned item to re-load that question and answer into the chat view. This is useful for keeping a curated set of key findings accessible without having to re-query the graph each session.

---

## LLM settings (in-app)

Click the gear icon in the top-right corner of the app to open the LLM settings modal. Here you can override the provider, API key, base URL, and model names for the current session. These settings are stored in the browser's `sessionStorage` only — they are never written to disk and are cleared automatically when you close the tab. The navbar displays the active provider and model name so you always know which configuration is in use.

Per-session settings are useful for temporarily switching between a fast cheap model and a slower, smarter one without editing `.env` and restarting the app.

---

## Tuning and troubleshooting

### Performance settings

The most important tuning parameters live in `.env`:

| Variable | Default | When to change |
|---|---|---|
| `NUM_WORKERS` | 4 | Lower to 1 or 2 for slow local models that cannot handle parallel requests |
| `MAX_DOCUMENTS` | 50 | Raise if your topic has more than 50 source files |
| `MAX_CLUSTER_SIZE` | 10 | Higher values produce fewer, broader communities |
| `LLM_CONTEXT_WINDOW` | 8192 | Must match your model's actual context window |
| `LLM_MAX_TOKENS` | 4096 | Raise to 8192–16384 for reasoning models that need more output space |
| `LLM_REQUEST_TIMEOUT` | 300 | Raise for slow local models; the default is 5 minutes per call |
| `EMBEDDINGS_ENABLED` | false | Set to `true` to enable semantic community pre-filtering (requires `sentence-transformers`) |

### Common issues

**The graph seems incomplete or sparse.** The most common cause is LLM timeouts during extraction. Lower `NUM_WORKERS` to 1 so requests are sent one at a time, and raise `LLM_REQUEST_TIMEOUT` to give each call more time to finish. Check the build log (visible in the status bar and in the container logs) for timeout warnings.

**There are many redundant or near-duplicate entity names.** Run Merge entities after the build. The rule-based normalisation handles the most common patterns automatically, and the LLM passes catch semantic synonyms. For synonyms the LLM keeps missing, add them directly to `ontology.json` under the `"aliases"` key and run a full rebuild.

**The build hangs indefinitely.** If you are using a reasoning model (DeepSeek R1, QwQ, Phi-4-reasoning, or similar), make sure the Reasoning model checkbox is ticked before building. Without it, the model's extended chain-of-thought output can loop for hours without producing a usable result. Also confirm that `LLM_MAX_TOKENS` is set high enough for the model to complete its thinking before outputting the answer.

**Chat returns "Not in the graph" for everything.** Either the topic graph has not been built yet, or a previous build failed partway through. Try clicking Build Graph again. If the status bar shows zero nodes and zero communities, the extraction likely failed — check the container logs for error details.

**You want to reset a topic completely.** Delete the `graphs/<topic>/` folder and run a full rebuild. This removes the pickle, all community summaries, the manifest, learned aliases, and any cached wiki articles.

**Blog post citation numbers look wrong.** If footnote numbers in a generated post fall outside the range of your source documents, the LLM confused community cluster IDs with source reference numbers. This is a known issue resolved in recent versions. Make sure you are running the latest code.

---

## Use cases

### Researchers

Load a corpus of papers, reports, or books on a topic and let the graph reveal connections that are hard to spot when reading documents one by one. Which entities appear across multiple papers? Which concepts sit at the centre of the network (highest degree)? Which clusters describe sub-fields you had not considered? Use chat to ask synthesis questions ("What are the main critiques of approach X across the literature?") and export wiki articles for any concept you want to understand more deeply. Pin the most useful Q&A pairs so you build up a curated research summary over time.

### Journalists and investigators

Ingest interview transcripts, government documents, financial filings, or other primary sources. The graph maps relationships between people, organisations, events, and documents automatically. Query the graph to trace connections ("What is the documented relationship between entity X and entity Y?") or to surface which sources mention a particular topic. Community summaries give you a quick thematic map of the material. Export the Obsidian vault to build a living investigation database with full backlink navigation.

### Content creators and bloggers

Ingest your research notes, saved articles, and reference material for a topic you want to write about. Use the blog post generator to produce a structured, grounded draft from the knowledge graph — the generator cites your own source documents as footnotes, so the output is traceable. Export as standalone HTML to paste directly into your CMS. For recurring content topics, maintain a topic folder and add new sources incrementally; the graph grows with your research.

### Companies with internal knowledge bases

Ingest product documentation, support articles, internal reports, and technical specifications. Build topic graphs per product line or department. Use the chat interface to let team members query the knowledge base in plain language. Use the blog post generator to draft marketing content or technical articles grounded in the company's own documentation. Export Obsidian vaults to maintain internal wikis that update as the source documents change.
