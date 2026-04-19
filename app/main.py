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
from fastapi.responses import HTMLResponse
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


@app.get("/api/config")
async def get_config():
    """Return server-side LLM config status (no secrets exposed)."""
    return {
        "has_server_config": bool(settings.openai_api_key or settings.llm_base_url),
        "extraction_model": settings.extraction_model,
        "query_model": settings.query_model,
        "has_base_url": bool(settings.llm_base_url),
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
        community_summary = store.community_summaries.get(cid) or store.community_summaries.get(str(cid), "")

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
        "outgoing": outgoing,
        "incoming": incoming,
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
