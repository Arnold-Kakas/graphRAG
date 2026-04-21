"""
FastAPI application — multi-topic GraphRAG web service.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from llama_index.core.graph_stores.types import EntityNode

from .config import settings
from .graph_store import GraphRAGStore
from .models import BuildRequest, LLMConfig, QueryRequest, QueryResponse, TopicStatus
from .query_engine import GraphRAGQueryEngine
from .task_manager import TaskManager, make_llm

logger = logging.getLogger(__name__)

app = FastAPI(title="GraphRAG Multi-Topic Explorer", version="1.0.0")

# ── Static files & templates ───────────────────────────────────────────────────
_here = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(_here / "static")), name="static")
templates = Jinja2Templates(directory=str(_here / "templates"))

# ── Singletons ─────────────────────────────────────────────────────────────────
task_manager = TaskManager(settings)
_query_engines: dict[str, GraphRAGQueryEngine] = {}


# ── Helper: discover topics ────────────────────────────────────────────────────

def _discover_topics() -> list[TopicStatus]:
    raw_dir = Path(settings.raw_dir)
    graphs_dir = Path(settings.graphs_dir)
    topics: dict[str, TopicStatus] = {}

    if raw_dir.exists():
        for d in sorted(raw_dir.iterdir()):
            if d.is_dir():
                topics[d.name] = TopicStatus(
                    topic=d.name,
                    has_raw_files=any(d.iterdir()),
                    has_graph=False,
                )

    if graphs_dir.exists():
        for d in sorted(graphs_dir.iterdir()):
            if not d.is_dir():
                continue
            graph_data_path = d / "graph_data.json"
            if not graph_data_path.exists():
                continue

            meta_path = d / "build_meta.json"
            meta = {}
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    pass

            if d.name not in topics:
                topics[d.name] = TopicStatus(
                    topic=d.name, has_raw_files=False, has_graph=True,
                )
            else:
                topics[d.name].has_graph = True

            topics[d.name].node_count = meta.get("node_count")
            topics[d.name].edge_count = meta.get("edge_count")
            topics[d.name].community_count = meta.get("community_count")

    result = []
    for name, status in topics.items():
        task = task_manager.get_status(name)
        if task:
            status.build_status = task.status
            status.build_progress = task.progress
            status.build_error = task.error
            status.docs_processed = task.docs_processed
            status.docs_total = task.docs_total
            status.nodes_extracted = task.nodes_extracted
            status.edges_extracted = task.edges_extracted
        elif status.has_graph:
            status.build_status = "complete"
        result.append(status)

    return result


def _get_query_engine(topic: str, llm_config: Optional[LLMConfig] = None) -> GraphRAGQueryEngine:
    """
    Get or create a query engine for the topic.
    If llm_config is provided (from the user's session), use it instead of server defaults.
    """
    # When per-request LLM config is provided, always create a fresh engine
    # so the user's key is used (and never cached).
    if llm_config and llm_config.api_key:
        graphs_dir = Path(settings.graphs_dir)
        topic_dir = graphs_dir / topic
        if not topic_dir.exists():
            raise HTTPException(status_code=404, detail=f"Graph not found for topic '{topic}'")
        try:
            store = GraphRAGStore.load(topic_dir)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        query_model = llm_config.query_model or settings.query_model
        extraction_model = llm_config.extraction_model or settings.extraction_model
        return GraphRAGQueryEngine(
            graph_store=store,
            llm=make_llm(query_model, llm_config),
            community_llm=make_llm(extraction_model, llm_config),
            embedding_cache_path=topic_dir / "community_embeddings.json",
        )

    # Fallback to cached engine using server-level .env config
    if topic not in _query_engines:
        graphs_dir = Path(settings.graphs_dir)
        topic_dir = graphs_dir / topic
        if not topic_dir.exists():
            raise HTTPException(status_code=404, detail=f"Graph not found for topic '{topic}'")
        try:
            store = GraphRAGStore.load(topic_dir)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        _query_engines[topic] = GraphRAGQueryEngine(
            graph_store=store,
            llm=make_llm(settings.query_model, fallback=settings),
            community_llm=make_llm(settings.extraction_model, fallback=settings),
            embedding_cache_path=topic_dir / "community_embeddings.json",
        )
    return _query_engines[topic]


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    topics = _discover_topics()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"topics": topics},
    )


def _infer_provider(base_url: Optional[str]) -> str:
    if not base_url:
        return "openai"
    low = base_url.lower()
    if "1234" in low or "lmstudio" in low:
        return "lmstudio"
    if "11434" in low or "ollama" in low:
        return "ollama"
    if "googleapis.com" in low:
        return "gemini"
    if "anthropic" in low:
        return "anthropic"
    return "custom"


@app.get("/api/config")
async def get_config():
    """Return server-side LLM config status (no secrets exposed)."""
    base = settings.llm_base_url
    return {
        "has_server_config": bool(settings.openai_api_key or settings.llm_base_url),
        "provider": _infer_provider(base),
        "extraction_model": settings.extraction_model,
        "query_model": settings.query_model,
        "base_url": base or None,
        "has_base_url": bool(base),
    }


@app.get("/api/topics")
async def list_topics() -> list[TopicStatus]:
    return _discover_topics()


@app.post("/api/topics/{topic}/build", status_code=202)
async def build_topic(topic: str, body: Optional[BuildRequest] = None):
    raw_dir = Path(settings.raw_dir) / topic
    if not raw_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Raw directory not found: raw/{topic}/. Create it and add documents first.",
        )

    ontology = (body.ontology if body else None)
    llm_config = (body.llm if body else None)
    force = (body.force if body else False)
    thinking = (body.thinking if body else False)
    build_context = (body.build_context if body else None)
    try:
        await task_manager.start_build(topic, ontology, llm_config, _query_engines, force, thinking, build_context)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return {"status": "building", "topic": topic}


@app.get("/api/topics/{topic}/status")
async def topic_status(topic: str) -> TopicStatus:
    topics = {t.topic: t for t in _discover_topics()}
    if topic not in topics:
        raise HTTPException(status_code=404, detail=f"Topic '{topic}' not found")
    return topics[topic]


@app.get("/api/topics/{topic}/index")
async def get_graph_index(topic: str):
    """
    Return the navigation index for the topic's graph.
    Lazily regenerates it from the pickle if the graph was built before the
    index feature was added, so pre-existing graphs don't need a full rebuild.
    """
    topic_dir = Path(settings.graphs_dir) / topic
    index_path = topic_dir / "graph_index.json"
    if index_path.exists():
        return Response(
            content=index_path.read_text(encoding="utf-8"),
            media_type="application/json",
        )
    # Fallback: rebuild index on the fly from the loaded store.
    try:
        store = GraphRAGStore.load(topic_dir)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    index = store.build_index()
    try:
        index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
        topic_label = topic.replace("_", " ")
        (topic_dir / "index.md").write_text(
            store.render_index_markdown(topic=topic_label), encoding="utf-8"
        )
    except Exception as exc:
        logger.warning("Could not persist regenerated index: %s", exc)
    return index


@app.get("/api/topics/{topic}/graph")
async def get_graph(topic: str):
    topic_dir = Path(settings.graphs_dir) / topic
    graph_path = topic_dir / "graph_data.json"
    if not graph_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Graph not built for topic '{topic}'. POST /api/topics/{topic}/build first.",
        )
    # Lazily regenerate graph_data.json if it has stale community count (0) but communities.json exists
    try:
        raw = graph_path.read_text(encoding="utf-8")
        gd = json.loads(raw)
        communities_path = topic_dir / "communities.json"
        if gd.get("communities", 0) == 0 and communities_path.exists():
            store = GraphRAGStore.load(topic_dir)
            updated = store.export_graph_data()
            raw = json.dumps(updated, indent=2)
            graph_path.write_text(raw, encoding="utf-8")
            logger.info("Regenerated stale graph_data.json for topic '%s'", topic)
    except Exception as exc:
        logger.warning("Could not refresh graph_data.json: %s", exc)
    return Response(content=raw, media_type="application/json")


class NodeRequest(BaseModel):
    generate: bool = False
    force: bool = False
    llm: Optional[LLMConfig] = None


@app.post("/api/topics/{topic}/nodes/{node_id}")
async def get_node_detail(topic: str, node_id: str, body: Optional[NodeRequest] = None):
    """
    Return rich detail for a single node. If generate=true, creates and caches a
    Wikipedia-style wiki article on first call. Pass llm to use the session's
    provider instead of the server .env config.
    """
    generate = body.generate if body else False
    force = body.force if body else False
    llm_config = body.llm if body else None
    topic_dir = Path(settings.graphs_dir) / topic
    if not topic_dir.exists():
        raise HTTPException(status_code=404, detail=f"Topic '{topic}' not found")

    try:
        store = GraphRAGStore.load(topic_dir)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    node = store.graph.nodes.get(node_id)
    if not node or not isinstance(node, EntityNode):
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")

    outgoing, incoming = [], []
    for rel in store.graph.relations.values():
        if rel.source_id == node_id:
            tgt = store.graph.nodes.get(rel.target_id)
            outgoing.append({
                "relation": rel.label,
                "node_id": rel.target_id,
                "node_label": tgt.name if tgt and isinstance(tgt, EntityNode) else rel.target_id,
                "node_type": tgt.label if tgt and isinstance(tgt, EntityNode) else "ENTITY",
                "description": rel.properties.get("relationship_description", ""),
            })
        elif rel.target_id == node_id:
            src = store.graph.nodes.get(rel.source_id)
            incoming.append({
                "relation": rel.label,
                "node_id": rel.source_id,
                "node_label": src.name if src and isinstance(src, EntityNode) else rel.source_id,
                "node_type": src.label if src and isinstance(src, EntityNode) else "ENTITY",
                "description": rel.properties.get("relationship_description", ""),
            })

    cid = store.node_community.get(node_id)
    community_summary = ""
    if cid is not None:
        community_summary = store.community_summaries.get(str(cid), "")

    wiki_article = store.entity_wikis.get(node_id, "")
    if (generate and not wiki_article) or force:
        try:
            query_model = (llm_config.query_model if llm_config else None) or settings.query_model
            llm = make_llm(query_model, llm_config, settings)
            wiki_article = await store.generate_entity_wiki(node_id, llm, topic_name=topic, force=force)
            # Persist the newly generated wiki
            wikis_path = topic_dir / "entity_wikis.json"
            wikis_path.write_text(json.dumps(store.entity_wikis, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Wiki generation failed: %s", exc)

    return {
        "id": node_id,
        "label": node.name,
        "type": node.label or "ENTITY",
        "description": node.properties.get("entity_description", ""),
        "wiki_article": wiki_article,
        "has_wiki": bool(wiki_article),
        "community_id": str(cid) if cid is not None else None,
        "community_summary": community_summary,
        "sources": node.properties.get("sources", []),
        "outgoing": outgoing,
        "incoming": incoming,
    }


@app.get("/api/topics/{topic}/export/obsidian")
async def export_obsidian(topic: str):
    """
    Export the topic's graph as a zipped Obsidian vault.

    One markdown file per entity with YAML frontmatter and inline `[[wiki links]]`
    to neighbours. Drop the unzipped folder into an Obsidian vault and the graph
    view + backlinks light up automatically.
    """
    import io
    import tempfile
    import zipfile

    topic_dir = Path(settings.graphs_dir) / topic
    if not topic_dir.exists():
        raise HTTPException(status_code=404, detail=f"Topic '{topic}' not found")
    try:
        store = GraphRAGStore.load(topic_dir)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    with tempfile.TemporaryDirectory(prefix=f"graphrag_obsidian_{topic}_") as tmp:
        export_root = Path(tmp) / topic
        store.export_obsidian(export_root, topic=topic)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in export_root.rglob("*"):
                if path.is_file():
                    zf.write(path, arcname=path.relative_to(export_root.parent))
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{topic}_obsidian.zip"'},
        )


# ── Pinned answers ─────────────────────────────────────────────────────────────

class PinnedAnswerRequest(BaseModel):
    question: str
    answer: str
    mode: Optional[str] = None
    sources: Optional[list] = None


def _pinned_path(topic: str) -> Path:
    return Path(settings.graphs_dir) / topic / "pinned_answers.json"


def _read_pinned(topic: str) -> list[dict]:
    path = _pinned_path(topic)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _write_pinned(topic: str, items: list[dict]) -> None:
    path = _pinned_path(topic)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, indent=2), encoding="utf-8")


@app.get("/api/topics/{topic}/pinned")
async def list_pinned(topic: str):
    topic_dir = Path(settings.graphs_dir) / topic
    if not topic_dir.exists():
        raise HTTPException(status_code=404, detail=f"Topic '{topic}' not found")
    return _read_pinned(topic)


@app.post("/api/topics/{topic}/pinned", status_code=201)
async def add_pinned(topic: str, body: PinnedAnswerRequest):
    import time
    import uuid

    topic_dir = Path(settings.graphs_dir) / topic
    if not topic_dir.exists():
        raise HTTPException(status_code=404, detail=f"Topic '{topic}' not found")
    question = (body.question or "").strip()
    answer = (body.answer or "").strip()
    if not question or not answer:
        raise HTTPException(status_code=400, detail="question and answer are required")

    items = _read_pinned(topic)
    item = {
        "id": uuid.uuid4().hex[:12],
        "question": question,
        "answer": answer,
        "mode": body.mode or "graph",
        "sources": body.sources or [],
        "created_at": int(time.time()),
    }
    items.insert(0, item)
    _write_pinned(topic, items)
    return item


@app.delete("/api/topics/{topic}/pinned/{pin_id}", status_code=204)
async def delete_pinned(topic: str, pin_id: str):
    topic_dir = Path(settings.graphs_dir) / topic
    if not topic_dir.exists():
        raise HTTPException(status_code=404, detail=f"Topic '{topic}' not found")
    items = _read_pinned(topic)
    new_items = [i for i in items if i.get("id") != pin_id]
    if len(new_items) == len(items):
        raise HTTPException(status_code=404, detail="Pinned answer not found")
    _write_pinned(topic, new_items)
    return Response(status_code=204)


@app.get("/api/topics/{topic}/build_context")
async def get_build_context(topic: str):
    """Return the last build_context used for this topic so the UI can prefill it."""
    path = Path(settings.graphs_dir) / topic / "build_context.txt"
    if not path.exists():
        return {"build_context": ""}
    try:
        return {"build_context": path.read_text(encoding="utf-8")}
    except Exception:
        return {"build_context": ""}


@app.get("/api/topics/{topic}/health")
async def topic_health(topic: str):
    """
    Lightweight structural health check for a topic's graph.
    Reports orphan nodes, missing-endpoint relations, and type coverage — cheap
    to compute, no LLM calls, useful for spotting extraction drift over time.
    """
    topic_dir = Path(settings.graphs_dir) / topic
    try:
        store = GraphRAGStore.load(topic_dir)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    node_ids = set(store.graph.nodes.keys())
    connected: set[str] = set()
    dangling = 0
    for rel in store.graph.relations.values():
        if rel.source_id in node_ids and rel.target_id in node_ids:
            connected.add(rel.source_id)
            connected.add(rel.target_id)
        else:
            dangling += 1

    orphans = [
        nid for nid, node in store.graph.nodes.items()
        if isinstance(node, EntityNode) and nid not in connected
    ]
    typed = sum(
        1 for node in store.graph.nodes.values()
        if isinstance(node, EntityNode) and node.label and node.label != "OTHER"
    )
    total = sum(1 for n in store.graph.nodes.values() if isinstance(n, EntityNode))

    return {
        "topic": topic,
        "node_count": total,
        "edge_count": len(store.graph.relations),
        "community_count": len(store.community_summaries),
        "orphan_count": len(orphans),
        "orphans_preview": orphans[:20],
        "dangling_relations": dangling,
        "typed_ratio": round(typed / total, 3) if total else 0.0,
        "has_index": bool(store.entity_index),
        "has_wikis": bool(store.entity_wikis),
    }


@app.post("/api/topics/{topic}/query")
async def query_topic(topic: str, body: QueryRequest) -> QueryResponse:
    task = task_manager.get_status(topic)
    if task and task.status == "building":
        raise HTTPException(status_code=409, detail="Graph is still being built. Please wait.")

    from .models import SourceCommunity
    engine = _get_query_engine(topic, llm_config=body.llm)
    answer, communities_checked, relevant_communities, sources = engine.custom_query(
        body.query, mode=body.mode
    )

    return QueryResponse(
        answer=answer,
        communities_checked=communities_checked,
        relevant_communities=relevant_communities,
        sources=[SourceCommunity(id=str(cid), summary=s) for cid, s in sources],
    )


@app.post("/api/topics/{topic}/query/stream")
async def query_topic_stream(topic: str, body: QueryRequest):
    """
    NDJSON-streaming variant of /query. Each line is a JSON object with a
    'type' field: 'status' | 'meta' | 'token' | 'done' | 'error'.
    Phase 1 (community relevance fan-out) is still synchronous and blocks for a
    few seconds before the first 'meta' event; Phase 2 (synthesis) streams
    token-by-token.
    """
    task = task_manager.get_status(topic)
    if task and task.status == "building":
        raise HTTPException(status_code=409, detail="Graph is still being built. Please wait.")

    engine = _get_query_engine(topic, llm_config=body.llm)

    async def event_gen():
        try:
            async for event in engine.astream_query(body.query, mode=body.mode):
                yield json.dumps(event) + "\n"
        except Exception as exc:
            logger.exception("Stream query failed")
            yield json.dumps({"type": "error", "message": str(exc)}) + "\n"

    return StreamingResponse(
        event_gen(),
        media_type="application/x-ndjson",
        # Hint to any reverse proxy (e.g. nginx) not to buffer the response.
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
