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
import re
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
from pydantic import Field, PrivateAttr, field_validator

from .config import Settings as AppSettings
from .graph_store import GraphRAGStore
from .models import ExtractionResult, OntologyConfig

logger = logging.getLogger(__name__)


# ── Extraction prompt ──────────────────────────────────────────────────────────

_DEFAULT_CONTEXT = (
    "Build a comprehensive knowledge graph. Extract all significant entities, key concepts, "
    "relationships, and how they interconnect. Prioritize coverage and accuracy to support "
    "general exploration and question answering across the full content."
)


def build_extraction_prompt(ontology: OntologyConfig, thinking: bool = False, build_context: Optional[str] = None) -> str:
    entity_types_str = ", ".join(ontology.entity_types)
    relation_types_str = ", ".join(ontology.relation_types)

    context_text = ((build_context.strip() + " ") if build_context and build_context.strip() else "") + _DEFAULT_CONTEXT

    base = f"""Given a document, identify all entities mentioned and their relationships.

-Build Context & Focus-
{context_text}



Extract up to {{max_knowledge_triplets}} entity-relation triplets.

-Allowed Entity Types-
{entity_types_str}

-Allowed Relationship Types-
{relation_types_str}

-Naming Rules (critical — prevents duplicates across chunks)-
- Use the FULL name for every entity, not an acronym or abbreviation alone.
  Good: "Marketing Mix Modeling", Bad: "MMM"
- If the text uses an abbreviation (e.g. "MMM"), expand it to the full name.
  Exception: the abbreviation IS the commonly known name (e.g. "MCMC" is acceptable
  alongside "Markov Chain Monte Carlo (MCMC)").
- Use American English spelling consistently (e.g. "Modeling", not "Modelling").
- Use title case for proper nouns and concepts (e.g. "Bayesian Model", "Prior Distribution").
- Do NOT append acronyms in parentheses to an entity name — use the clean full name
  (e.g. "Marketing Mix Modeling", not "Marketing Mix Modeling (MMM)").
- Two names that refer to the same concept must be written identically every time.

-Steps-
1. Identify ALL entities. For each entity extract:
   - name: Name of the entity (follow Naming Rules above)
   - type: One of the allowed entity types above (use the closest match; default to the most general type if unsure)
   - description: A brief description of the entity and its significance in this document

2. Identify relationships between entities. For each pair extract:
   - source: name of the source entity (must match the entity name exactly)
   - target: name of the target entity (must match the entity name exactly)
   - relation: one of the allowed relationship types above
   - description: a sentence explaining why and how these entities are related

-Real Data-
######################
text: {{text}}
######################
"""

    if thinking:
        return base  # JSON hint is appended by _acomplete_extract at call time
    else:
        return "/no_think\n" + base


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
    thinking: bool = False
    valid_entity_types: list[str] = Field(default_factory=list)
    valid_relation_types: list[str] = Field(default_factory=list)
    total_nodes: int = Field(default=0)

    _processed: int = PrivateAttr(default=0)
    _nodes_extracted: int = PrivateAttr(default=0)
    _edges_extracted: int = PrivateAttr(default=0)
    _stats_callback: Optional[Callable] = PrivateAttr(default=None)

    @field_validator("extract_prompt", mode="before")
    @classmethod
    def coerce_to_prompt_template(cls, v):
        return PromptTemplate(v) if isinstance(v, str) else v

    def __call__(self, nodes, show_progress=False, **kwargs):
        return asyncio.run(self.acall(nodes, show_progress=show_progress, **kwargs))

    _JSON_OUTPUT_HINT = (
        "\nOutput ONLY a raw JSON object — no markdown, no code fences, no extra text:\n"
        '{"entities": [{"name": "...", "type": "...", "description": "..."}], '
        '"relationships": [{"source": "...", "target": "...", "relation": "...", "description": "..."}]}'
    )

    def _parse_json_result(self, text: str) -> Optional[ExtractionResult]:
        """Parse ExtractionResult from raw text, handling markdown fences and partial JSON."""
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
        """
        Plain-text completion path for thinking models (Gemma 4, Qwen3 with thinking ON,
        DeepSeek-R1, etc.) that output JSON as regular text instead of via tool calls.
        """
        try:
            prompt_text = self.extract_prompt.format(
                text=text,
                max_knowledge_triplets=self.max_paths_per_chunk,
            ) + self._JSON_OUTPUT_HINT
            response = await self.llm.acomplete(prompt_text)
            raw = response.text.strip()
            result = self._parse_json_result(raw) if raw else None
            if result:
                return result.entities, result.relationships
            logger.warning("Plain-text extraction returned no parseable JSON")
        except Exception as exc:
            logger.error("Plain-text extraction error: %s", exc)
        return [], []

    async def _aextract(self, node: BaseNode) -> BaseNode:
        text = node.get_content(metadata_mode="llm")

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
                # Thinking models (Gemma 4, Qwen3, DeepSeek-R1) that put output in
                # reasoning_content instead of tool_calls trigger this error. Fall back
                # to plain-text completion rather than letting LlamaIndex retry in a loop.
                if "0 tool calls" in err or "could not be parsed" in err.lower():
                    logger.warning("Function calling unsupported for node %s (%s) — falling back to plain-text", node.node_id, exc)
                    entities, relationships = await self._acomplete_extract(text)
                else:
                    logger.error("Extraction error on node %s: %s", node.node_id, exc)
                    entities, relationships = [], []

        self._processed += 1
        self._nodes_extracted += len(entities)
        self._edges_extracted += len(relationships)
        if self._stats_callback and self.total_nodes:
            self._stats_callback(self._processed, self.total_nodes, self._nodes_extracted, self._edges_extracted)

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
    stats_callback: Optional[Callable[[int, int, int, int], None]] = None,
    force: bool = False,
    thinking: bool = False,
    build_context: Optional[str] = None,
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
    prompt_str = build_extraction_prompt(ontology, thinking=thinking, build_context=build_context)

    kg_extractor = GraphRAGExtractor(
        llm=extraction_llm,
        extract_prompt=prompt_str,
        max_paths_per_chunk=config.max_paths_per_chunk,
        num_workers=config.num_workers,
        thinking=thinking,
        valid_entity_types=ontology.entity_types,
        valid_relation_types=ontology.relation_types,
        total_nodes=len(nodes),
    )
    kg_extractor._stats_callback = stats_callback

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

    _p("Resolving duplicate entities...")
    llm_merge_map = graph_store.resolve_entities(llm=community_llm, topic_name=topic)
    merged_aliases = {**(ontology.aliases or {}), **llm_merge_map}

    _p("Deduplicating nodes...")
    removed = graph_store.deduplicate_nodes(aliases=merged_aliases or None)
    if removed:
        _p(f"Merged {removed} duplicate node(s)")

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
