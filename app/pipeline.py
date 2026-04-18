"""
GraphRAG extraction pipeline — hybrid mode.

Each document is processed in two LLM calls:
  1. Summarise the full document (preserving all entities, facts, relationships)
  2. Extract entities + relationships from the summary

This replaces the old chunk-per-call approach (N_chunks × 1 call → 2 calls per document),
cutting ingestion time by 4-6× for typical document lengths.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from llama_index.core.async_utils import run_jobs
from llama_index.core.graph_stores.types import EntityNode, Relation
from llama_index.core.llms.llm import LLM
from llama_index.core.prompts import PromptTemplate
from pydantic import Field, PrivateAttr, field_validator

from .config import Settings as AppSettings
from .graph_store import GraphRAGStore
from .models import ExtractionResult, OntologyConfig

logger = logging.getLogger(__name__)


# ── Summarisation ──────────────────────────────────────────────────────────────

_SUMMARISE_PROMPT = (
    "Summarise the following document for knowledge graph construction. "
    "Preserve every named entity (people, organisations, technologies, concepts, events, products), "
    "all relationships between them, key facts, metrics, arguments, and domain-specific details. "
    "Completeness matters more than brevity — include enough detail for accurate graph extraction.\n\n"
    "Document:\n{text}\n\n"
    "Comprehensive Summary:"
)

async def _summarise_document(text: str, llm: LLM, max_chars: int = 12000) -> str:
    """Compress a document into a rich summary for entity extraction."""
    prompt = _SUMMARISE_PROMPT.format(text=text[:max_chars])
    response = await llm.acomplete(prompt)
    return response.text.strip()


# ── Extraction prompt ──────────────────────────────────────────────────────────

_DEFAULT_CONTEXT = (
    "Build a comprehensive knowledge graph. Extract all significant entities, key concepts, "
    "relationships, and how they interconnect. Prioritize coverage and accuracy to support "
    "general exploration and question answering across the full content."
)


def build_extraction_prompt(
    ontology: OntologyConfig,
    thinking: bool = False,
    build_context: Optional[str] = None,
) -> str:
    entity_types_str = ", ".join(ontology.entity_types)
    relation_types_str = ", ".join(ontology.relation_types)
    context_text = (
        ((build_context.strip() + " ") if build_context and build_context.strip() else "")
        + _DEFAULT_CONTEXT
    )

    base = f"""Given a document summary, identify all entities mentioned and their relationships.

-Build Context & Focus-
{context_text}

Extract up to {{max_knowledge_triplets}} entity-relation triplets.

-Allowed Entity Types-
{entity_types_str}

-Allowed Relationship Types-
{relation_types_str}

-Naming Rules (critical — prevents duplicates)-
- Use the FULL name for every entity, not an acronym or abbreviation alone.
  Good: "Marketing Mix Modeling", Bad: "MMM"
- If the text uses an abbreviation, expand it to the full name.
  Exception: the abbreviation IS the commonly known name (e.g. "MCMC").
- Use American English spelling consistently (e.g. "Modeling", not "Modelling").
- Use title case for proper nouns and concepts.
- Do NOT append acronyms in parentheses — use the clean full name.
- Two names that refer to the same concept must be written identically every time.

-Steps-
1. Identify ALL entities. For each entity extract:
   - name: Name of the entity (follow Naming Rules above)
   - type: One of the allowed entity types above
   - description: 2-3 sentences describing what this entity is, its key characteristics,
     and its significance in this context

2. Identify relationships between entities. For each pair extract:
   - source: name of the source entity (must match exactly)
   - target: name of the target entity (must match exactly)
   - relation: one of the allowed relationship types above
   - description: a sentence explaining why and how these entities are related

-Document Summary-
######################
text: {{text}}
######################
"""

    if thinking:
        return base
    else:
        return "/no_think\n" + base


# ── Extractor ──────────────────────────────────────────────────────────────────

class GraphRAGExtractor:
    """
    Extracts entities and relationships from text using an LLM.
    Works directly on strings (no LlamaIndex node wrapping).
    """

    def __init__(
        self,
        llm: LLM,
        extract_prompt: str,
        max_paths_per_chunk: int = 20,
        num_workers: int = 4,
        thinking: bool = False,
        valid_entity_types: list[str] = None,
        valid_relation_types: list[str] = None,
    ):
        self.llm = llm
        self.extract_prompt = PromptTemplate(extract_prompt)
        self.max_paths_per_chunk = max_paths_per_chunk
        self.num_workers = num_workers
        self.thinking = thinking
        self.valid_entity_types = valid_entity_types or []
        self.valid_relation_types = valid_relation_types or []
        self._processed = 0
        self._nodes_extracted = 0
        self._edges_extracted = 0
        self._stats_callback: Optional[Callable] = None

    _JSON_OUTPUT_HINT = (
        "\nOutput ONLY a raw JSON object — no markdown, no code fences, no extra text:\n"
        '{"entities": [{"name": "...", "type": "...", "description": "..."}], '
        '"relationships": [{"source": "...", "target": "...", "relation": "...", "description": "..."}]}'
    )

    def _parse_json_result(self, text: str) -> Optional[ExtractionResult]:
        text = text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group())
            return ExtractionResult.model_validate(data)
        except Exception as exc:
            logger.error("JSON parse error: %s", exc)
            return None

    async def _acomplete_extract(self, text: str) -> tuple[list, list]:
        try:
            prompt_text = self.extract_prompt.format(
                text=text,
                max_knowledge_triplets=self.max_paths_per_chunk,
            ) + self._JSON_OUTPUT_HINT
            response = await self.llm.acomplete(prompt_text)
            raw = response.text.strip()
            if "</think>" in raw:
                raw = raw.split("</think>")[-1].strip()
            result = self._parse_json_result(raw) if raw else None
            if result:
                return result.entities, result.relationships
            logger.warning("Plain-text extraction returned no parseable JSON")
        except Exception as exc:
            logger.error("Plain-text extraction error: %s", exc)
        return [], []

    async def extract(
        self, text: str, source_metadata: dict
    ) -> tuple[list[EntityNode], list[Relation]]:
        """
        Extract entities and relationships from text.
        Returns (entity_nodes, relations) ready for direct graph store upsert.
        """
        if self.thinking:
            entities, relationships = await self._acomplete_extract(text)
        else:
            try:
                result: ExtractionResult = await self.llm.astructured_predict(
                    ExtractionResult,
                    self.extract_prompt,
                    text=text,
                    max_knowledge_triplets=self.max_paths_per_chunk,
                )
                entities = result.entities
                relationships = result.relationships
            except Exception as exc:
                err = str(exc)
                if "0 tool calls" in err or "could not be parsed" in err.lower():
                    logger.warning("Function calling unsupported — falling back to plain-text")
                    entities, relationships = await self._acomplete_extract(text)
                else:
                    logger.error("Extraction error: %s", exc)
                    entities, relationships = [], []

        # Validate against ontology
        for e in entities:
            if self.valid_entity_types and e.type not in self.valid_entity_types:
                e.type = "OTHER"
        for r in relationships:
            if self.valid_relation_types and r.relation not in self.valid_relation_types:
                r.relation = "RELATED_TO"

        # Build EntityNodes
        entity_nodes = [
            EntityNode(
                name=e.name,
                label=e.type,
                properties={**source_metadata, "entity_description": e.description},
            )
            for e in entities
        ]
        name_to_type = {e.name: e.type for e in entities}
        name_to_id = {n.name: n.id for n in entity_nodes}

        # Build Relations (also registers any source/target nodes not yet in entity list)
        extra_nodes: list[EntityNode] = []
        relation_objs: list[Relation] = []
        for rel in relationships:
            if rel.source not in name_to_id:
                n = EntityNode(name=rel.source, label=name_to_type.get(rel.source, "ENTITY"), properties=source_metadata)
                extra_nodes.append(n)
                name_to_id[rel.source] = n.id
            if rel.target not in name_to_id:
                n = EntityNode(name=rel.target, label=name_to_type.get(rel.target, "ENTITY"), properties=source_metadata)
                extra_nodes.append(n)
                name_to_id[rel.target] = n.id
            relation_objs.append(
                Relation(
                    label=rel.relation,
                    source_id=name_to_id[rel.source],
                    target_id=name_to_id[rel.target],
                    properties={**source_metadata, "relationship_description": rel.description},
                )
            )

        all_nodes = entity_nodes + extra_nodes
        self._nodes_extracted += len(all_nodes)
        self._edges_extracted += len(relation_objs)
        return all_nodes, relation_objs


# ── Full pipeline orchestration ────────────────────────────────────────────────

async def build_topic_graph(
    topic: str,
    documents: list[dict],
    ontology: OntologyConfig,
    config: AppSettings,
    extraction_llm: LLM,
    community_llm: LLM,
    progress_callback: Optional[Callable[[str], None]] = None,
    stats_callback: Optional[Callable[[int, int, int, int], None]] = None,
    force: bool = False,
    thinking: bool = False,
    build_context: Optional[str] = None,
) -> GraphRAGStore:
    """
    Hybrid pipeline: summarise each document then extract entities/relationships.
    2 LLM calls per document instead of N_chunks calls — typically 4-6× faster.
    """

    def _p(msg: str) -> None:
        logger.info("[%s] %s", topic, msg)
        if progress_callback:
            progress_callback(msg)

    graphs_dir = Path(config.graphs_dir)
    topic_dir = graphs_dir / topic
    manifest_path = topic_dir / "manifest.json"

    # ── Load existing manifest ─────────────────────────────────────────────────
    existing_manifest: dict = {}
    if not force and manifest_path.exists():
        try:
            existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    stored_mtimes: dict[str, float] = existing_manifest.get("files", {})
    current_mtimes: dict[str, float] = {
        doc["filename"]: doc["metadata"].get("mtime", 0.0)
        for doc in documents
    }

    # ── Decide full vs incremental ─────────────────────────────────────────────
    pkl_exists = (topic_dir / "store.pkl").exists()
    is_incremental = bool(stored_mtimes) and pkl_exists and not force

    if is_incremental:
        docs_to_process = [
            doc for doc in documents
            if current_mtimes[doc["filename"]] > stored_mtimes.get(doc["filename"], 0.0)
        ]
        skipped = len(documents) - len(docs_to_process)

        if not docs_to_process:
            _p(f"Graph is already up to date — all {len(documents)} file(s) unchanged")
            return GraphRAGStore.load(topic_dir)

        _p(f"Incremental build: {len(docs_to_process)} new/modified, {skipped} unchanged")
        graph_store = GraphRAGStore.load(topic_dir)
    else:
        docs_to_process = documents[: config.max_documents]
        _p(f"{'Forced full' if force and pkl_exists else 'Full'} build: {len(docs_to_process)} file(s)")
        graph_store = GraphRAGStore()

    # ── Build extractor ────────────────────────────────────────────────────────
    prompt_str = build_extraction_prompt(ontology, thinking=thinking, build_context=build_context)
    extractor = GraphRAGExtractor(
        llm=extraction_llm,
        extract_prompt=prompt_str,
        max_paths_per_chunk=config.max_paths_per_chunk,
        num_workers=config.num_workers,
        thinking=thinking,
        valid_entity_types=ontology.entity_types,
        valid_relation_types=ontology.relation_types,
    )

    # ── Hybrid extraction: summarise → extract per document ───────────────────
    _p(f"Extracting entities and relationships (hybrid mode: 2 calls × {len(docs_to_process)} docs)...")
    total_docs = len(docs_to_process)

    async def _process_doc(doc: dict) -> None:
        filename = doc.get("filename", "unknown")
        text = doc["text"]
        metadata = {k: v for k, v in doc.get("metadata", {}).items() if k != "mtime"}

        # Step 1: summarise (skip for very short documents)
        if len(text) > 1500:
            try:
                summary = await _summarise_document(text, extraction_llm, max_chars=config.llm_context_window * 3)
            except Exception as exc:
                logger.warning("Summarisation failed for %s (%s) — extracting from raw text", filename, exc)
                summary = text[: config.llm_context_window * 3]
        else:
            summary = text

        # Step 2: extract entities + relationships
        entity_nodes, relations = await extractor.extract(summary, metadata)

        # Merge into graph store (description-aware upsert)
        graph_store.upsert_nodes_merge(entity_nodes)
        graph_store.upsert_relations(relations)

        extractor._processed += 1
        if stats_callback:
            stats_callback(
                extractor._processed,
                total_docs,
                extractor._nodes_extracted,
                extractor._edges_extracted,
            )
        logger.info("[%s] %d/%d — %s (%d nodes, %d edges extracted so far)",
                    topic, extractor._processed, total_docs, filename,
                    extractor._nodes_extracted, extractor._edges_extracted)

    jobs = [_process_doc(doc) for doc in docs_to_process]
    await run_jobs(jobs, workers=config.num_workers, desc="Processing documents")

    _p(f"Extraction done — {extractor._nodes_extracted} raw nodes, {extractor._edges_extracted} raw edges")

    # ── Deduplication ──────────────────────────────────────────────────────────
    _p("Resolving duplicate entities...")
    llm_merge_map = graph_store.resolve_entities(llm=community_llm, topic_name=topic)
    merged_aliases = {**(ontology.aliases or {}), **llm_merge_map}

    _p("Deduplicating nodes...")
    removed = graph_store.deduplicate_nodes(aliases=merged_aliases or None)
    if removed:
        _p(f"Merged {removed} duplicate node(s)")

    # ── Community detection ────────────────────────────────────────────────────
    _p("Running community detection and generating summaries...")
    graph_store.build_communities(
        llm=community_llm,
        topic_name=topic,
        max_cluster_size=config.max_cluster_size,
        progress_callback=progress_callback,
    )

    # ── Save ───────────────────────────────────────────────────────────────────
    _p("Saving graph artifacts...")
    graph_store.save(topic_dir)

    (topic_dir / "ontology.json").write_text(
        json.dumps(ontology.model_dump(), indent=2), encoding="utf-8"
    )

    graph_data = graph_store.export_graph_data()
    meta = {
        "topic": topic,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "document_count": len(documents),
        "node_count": len(graph_data["nodes"]),
        "edge_count": len(graph_data["links"]),
        "community_count": graph_data["communities"],
    }
    (topic_dir / "build_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    manifest = {"files": current_mtimes, "built_at": meta["built_at"]}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    _p(f"Build complete — {meta['node_count']} nodes, {meta['edge_count']} edges, {meta['community_count']} communities")
    return graph_store
