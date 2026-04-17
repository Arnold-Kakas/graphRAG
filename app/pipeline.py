"""
GraphRAG extraction pipeline.

- GraphRAGExtractor: TransformComponent that calls the LLM to extract
  entities + relationships (with descriptions) from each document.
- build_topic_graph(): orchestrates the full pipeline for one topic.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from llama_index.core import Document, PropertyGraphIndex, Settings
from llama_index.core.async_utils import run_jobs
from llama_index.core.graph_stores.types import (
    KG_NODES_KEY,
    KG_RELATIONS_KEY,
    EntityNode,
    Relation,
)
from llama_index.core.llms.llm import LLM
from llama_index.core.prompts import PromptTemplate
from llama_index.core.schema import BaseNode, TransformComponent
from pydantic import Field, field_validator

from .config import Settings as AppSettings
from .graph_store import GraphRAGStore
from .models import ExtractionResult, OntologyConfig

logger = logging.getLogger(__name__)


# ── Extraction prompt ──────────────────────────────────────────────────────────

def build_extraction_prompt(ontology: OntologyConfig, thinking: bool = False) -> str:
    entity_types_str = ", ".join(ontology.entity_types)
    relation_types_str = ", ".join(ontology.relation_types)
    prefix = "" if thinking else "/no_think\n"

    return f"""{prefix}Given a document, identify all entities mentioned and their relationships.

Extract up to {{max_knowledge_triplets}} entity-relation triplets.

-Allowed Entity Types-
{entity_types_str}

-Allowed Relationship Types-
{relation_types_str}

-Steps-
1. Identify ALL entities. For each entity extract:
   - name: Name of the entity, capitalized
   - type: One of the allowed entity types above (use the closest match; default to the most general type if unsure)
   - description: A brief description of the entity and its significance in this document

2. Identify relationships between entities. For each pair extract:
   - source: name of the source entity
   - target: name of the target entity
   - relation: one of the allowed relationship types above
   - description: a sentence explaining why and how these entities are related

-Real Data-
######################
text: {{text}}
######################
"""


# ── GraphRAGExtractor ──────────────────────────────────────────────────────────

class GraphRAGExtractor(TransformComponent):
    """
    Extracts entities and relationships WITH descriptions from each text chunk.
    Runs asynchronously with num_workers parallel LLM calls.
    """

    llm: LLM = Field(default_factory=lambda: Settings.llm)
    extract_prompt: PromptTemplate = Field(
        default_factory=lambda: PromptTemplate("")
    )
    num_workers: int = 4
    max_paths_per_chunk: int = 20
    valid_entity_types: list[str] = Field(default_factory=list)
    valid_relation_types: list[str] = Field(default_factory=list)

    @field_validator("extract_prompt", mode="before")
    @classmethod
    def coerce_to_prompt_template(cls, v):
        return PromptTemplate(v) if isinstance(v, str) else v

    def __call__(self, nodes, show_progress=False, **kwargs):
        return asyncio.run(self.acall(nodes, show_progress=show_progress, **kwargs))

    async def _aextract(self, node: BaseNode) -> BaseNode:
        text = node.get_content(metadata_mode="llm")

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
            logger.error("Extraction error on node %s: %s", node.node_id, exc)
            entities, relationships = [], []

        # Post-validate types against the ontology; unknown → "OTHER" / "RELATED_TO"
        for e in entities:
            if self.valid_entity_types and e.type not in self.valid_entity_types:
                e.type = "OTHER"
        for r in relationships:
            if self.valid_relation_types and r.relation not in self.valid_relation_types:
                r.relation = "RELATED_TO"

        existing_nodes = node.metadata.pop(KG_NODES_KEY, [])
        existing_relations = node.metadata.pop(KG_RELATIONS_KEY, [])
        base_metadata = node.metadata.copy()

        existing_nodes += [
            EntityNode(
                name=entity.name,
                label=entity.type,
                properties={**base_metadata, "entity_description": entity.description},
            )
            for entity in entities
        ]

        entity_lookup = {e.name: e.type for e in entities}
        for rel in relationships:
            source_node = EntityNode(
                name=rel.source,
                label=entity_lookup.get(rel.source, "ENTITY"),
                properties=base_metadata,
            )
            target_node = EntityNode(
                name=rel.target,
                label=entity_lookup.get(rel.target, "ENTITY"),
                properties=base_metadata,
            )
            if rel.source not in entity_lookup:
                existing_nodes.append(source_node)
            if rel.target not in entity_lookup:
                existing_nodes.append(target_node)
            existing_relations.append(
                Relation(
                    label=rel.relation,
                    source_id=source_node.id,
                    target_id=target_node.id,
                    properties={
                        **base_metadata,
                        "relationship_description": rel.description,
                    },
                )
            )

        node.metadata[KG_NODES_KEY] = existing_nodes
        node.metadata[KG_RELATIONS_KEY] = existing_relations
        return node

    async def acall(self, nodes, show_progress=False, **kwargs):
        jobs = [self._aextract(node) for node in nodes]
        return await run_jobs(
            jobs,
            workers=self.num_workers,
            show_progress=show_progress,
            desc="Extracting triplets",
        )


# ── Full pipeline orchestration ────────────────────────────────────────────────

async def build_topic_graph(
    topic: str,
    documents: list[dict],
    ontology: OntologyConfig,
    config: AppSettings,
    extraction_llm: LLM,
    community_llm: LLM,
    progress_callback: Optional[Callable[[str], None]] = None,
    force: bool = False,
    thinking: bool = False,
) -> GraphRAGStore:
    """
    Full or incremental pipeline for one topic.

    Incremental mode (default when a prior build exists):
      - Compares each file's mtime against the stored manifest.
      - Only re-extracts new or modified files; unchanged files are skipped.
      - Deleted files' nodes remain in the graph until a full rebuild is forced.

    Force a full rebuild by passing force=True (or ticking "Full rebuild" in the UI),
    which ignores the manifest and re-processes every file from scratch.

    Steps:
      1. Determine which documents need (re-)processing.
      2. Extract entities/relationships (LLM) for those documents.
      3. Run Leiden community detection on the full graph.
      4. Generate LLM community summaries.
      5. Save all artifacts to graphs/<topic>/
    """

    def _p(msg: str) -> None:
        logger.info("[%s] %s", topic, msg)
        if progress_callback:
            progress_callback(msg)

    graphs_dir = Path(config.graphs_dir)
    topic_dir = graphs_dir / topic
    manifest_path = topic_dir / "manifest.json"

    # ── Load existing manifest (mtimes from last build) ────────────────────────
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

        _p(f"Incremental build: {len(docs_to_process)} new/modified file(s), {skipped} unchanged (skipped)")
        graph_store = GraphRAGStore.load(topic_dir)
    else:
        docs_to_process = documents[: config.max_documents]
        if force and pkl_exists:
            _p(f"Forced full rebuild: processing all {len(docs_to_process)} file(s)")
        else:
            _p(f"Full build: processing {len(docs_to_process)} file(s)")
        graph_store = GraphRAGStore()

    # ── Build LlamaIndex nodes (strip mtime from metadata — it's build infra) ──
    nodes = [
        Document(
            text=doc["text"],
            metadata={k: v for k, v in doc.get("metadata", {}).items() if k != "mtime"},
        )
        for doc in docs_to_process
    ]

    _p("Building extraction prompt...")
    prompt_str = build_extraction_prompt(ontology, thinking=thinking)

    kg_extractor = GraphRAGExtractor(
        llm=extraction_llm,
        extract_prompt=prompt_str,
        max_paths_per_chunk=config.max_paths_per_chunk,
        num_workers=config.num_workers,
        valid_entity_types=ontology.entity_types,
        valid_relation_types=ontology.relation_types,
    )

    _p("Extracting entities and relationships (this may take several minutes)...")
    Settings.llm = extraction_llm

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: PropertyGraphIndex(
            nodes=nodes,
            kg_extractors=[kg_extractor],
            property_graph_store=graph_store,
            embed_kg_nodes=False,
            show_progress=True,
        ),
    )

    _p("Running community detection and generating summaries...")
    graph_store.build_communities(
        llm=community_llm,
        topic_name=topic,
        max_cluster_size=config.max_cluster_size,
        progress_callback=progress_callback,
    )

    _p("Saving graph artifacts...")
    graph_store.save(topic_dir)

    # Save ontology used for this build
    (topic_dir / "ontology.json").write_text(
        json.dumps(ontology.model_dump(), indent=2), encoding="utf-8"
    )

    # Save build metadata
    graph_data = graph_store.export_graph_data()
    meta = {
        "topic": topic,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "document_count": len(documents),
        "node_count": len(graph_data["nodes"]),
        "edge_count": len(graph_data["links"]),
        "community_count": graph_data["communities"],
    }
    (topic_dir / "build_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    # Save manifest — records mtime of every file so incremental builds can
    # detect changes on the next run.
    manifest = {
        "files": current_mtimes,
        "built_at": meta["built_at"],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    _p(
        f"Build complete — {meta['node_count']} nodes, "
        f"{meta['edge_count']} edges, {meta['community_count']} communities"
    )
    return graph_store
