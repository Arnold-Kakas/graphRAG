"""
GraphRAGStore — extends LlamaIndex's SimplePropertyGraphStore with:
  - Leiden community detection
  - LLM-generated community summaries
  - save() / load() for persistence between sessions
  - export_graph_data() for D3.js visualization
"""

from __future__ import annotations

import json
import logging
import pickle
import re
from collections import defaultdict
from pathlib import Path
from typing import Callable, Optional

import networkx as nx
from graspologic.partition import hierarchical_leiden
from llama_index.core.graph_stores import SimplePropertyGraphStore
from llama_index.core.graph_stores.types import EntityNode, Relation

logger = logging.getLogger(__name__)


class GraphRAGStore(SimplePropertyGraphStore):
    """
    Property graph store with community detection and LLM summarization.

    Usage:
        store = GraphRAGStore()
        store.build_communities(llm=extraction_llm, topic_name="climate_change")
        store.save(Path("graphs/climate_change"))

        # Later:
        store = GraphRAGStore.load(Path("graphs/climate_change"))
    """

    community_summaries: dict = {}
    entity_wikis: dict = {}
    node_community: dict = {}  # node_id → community_id (int)

    # ── Node upsert ────────────────────────────────────────────────────────────

    def upsert_nodes_merge(self, nodes: list) -> None:
        """Upsert nodes, merging entity_description if a node already exists."""
        for node in nodes:
            existing = self.graph.nodes.get(node.id)
            if existing and isinstance(existing, EntityNode):
                new_desc = node.properties.get("entity_description", "")
                existing_desc = existing.properties.get("entity_description", "")
                if new_desc and new_desc not in existing_desc:
                    existing.properties["entity_description"] = (
                        existing_desc + " " + new_desc if existing_desc else new_desc
                    ).strip()
            else:
                self.graph.nodes[node.id] = node

    # ── Community detection ────────────────────────────────────────────────────

    def build_communities(
        self,
        llm,
        topic_name: str = "",
        max_cluster_size: int = 10,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        def _progress(msg: str) -> None:
            logger.info(msg)
            if progress_callback:
                progress_callback(msg)

        _progress("Converting graph to NetworkX...")
        nx_graph = self._to_networkx()

        if not nx_graph.nodes:
            _progress("Graph is empty — no communities to detect")
            return

        _progress(
            f"Graph has {nx_graph.number_of_nodes()} nodes, "
            f"{nx_graph.number_of_edges()} edges — running Leiden clustering..."
        )

        clusters = hierarchical_leiden(nx_graph, max_cluster_size=max_cluster_size)
        num_communities = len(set(c.cluster for c in clusters))
        _progress(f"Found {num_communities} communities — generating summaries...")

        # Build node→community mapping for wiki generation
        self.node_community = {item.node: item.cluster for item in clusters}

        community_info = self._collect_community_info(nx_graph, clusters)
        self._generate_summaries(community_info, llm, topic_name, progress_callback)

        _progress(f"Done — {len(self.community_summaries)} community summaries generated")

    def _to_networkx(self) -> nx.Graph:
        nx_graph = nx.Graph()
        for node in self.graph.nodes.values():
            if isinstance(node, EntityNode):
                nx_graph.add_node(node.id)
        for relation in self.graph.relations.values():
            if relation.source_id in nx_graph and relation.target_id in nx_graph:
                nx_graph.add_edge(
                    relation.source_id,
                    relation.target_id,
                    relationship=relation.label,
                    description=relation.properties.get("relationship_description", ""),
                )
        return nx_graph

    def _collect_community_info(self, nx_graph: nx.Graph, clusters) -> dict:
        community_mapping = {item.node: item.cluster for item in clusters}

        node_details: dict[str, dict] = {}
        for node in self.graph.nodes.values():
            if not isinstance(node, EntityNode):
                continue
            node_details[node.id] = {
                "name": node.name,
                "type": node.label,
                "description": node.properties.get("entity_description", ""),
            }

        community_info: dict[int, dict] = {}
        for item in clusters:
            cid, nid = item.cluster, item.node
            community_info.setdefault(cid, {"entities": [], "relationships": []})

            if nid in node_details:
                community_info[cid]["entities"].append(node_details[nid])

            for neighbor in nx_graph.neighbors(nid):
                if community_mapping.get(neighbor) != cid:
                    continue
                edge = nx_graph.get_edge_data(nid, neighbor) or {}
                rel = edge.get("relationship", "RELATED")
                desc = edge.get("description", "")
                src_name = node_details.get(nid, {}).get("name", nid)
                tgt_name = node_details.get(neighbor, {}).get("name", neighbor)
                entry = f"{src_name} --[{rel}]--> {tgt_name}"
                if desc:
                    entry += f" ({desc})"
                community_info[cid]["relationships"].append(entry)

        return community_info

    def _generate_summaries(
        self,
        community_info: dict,
        llm,
        topic_name: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        topic_label = topic_name.replace("_", " ") if topic_name else "the given topic"
        total = len(community_info)

        for idx, (community_id, data) in enumerate(community_info.items(), 1):
            if not data["relationships"] and not data["entities"]:
                continue

            entities_text = "\n".join(
                f"- {e['name']} ({e['type']}): {e['description']}"
                for e in data["entities"]
                if e.get("name")
            )
            relationships_text = "\n".join(sorted(set(data["relationships"])))

            prompt = f"""You are analysing a cluster of related entities extracted from documents about "{topic_label}".

Entities in this cluster:
{entities_text}

Relationships:
{relationships_text}

Write a concise briefing (3-5 sentences) that:
1. Identifies the main entities (people, organizations, concepts, events) in this cluster
2. Explains how they are connected and why
3. Highlights any disputes, collaborations, dependencies, or tensions
4. Notes anything particularly significant for understanding {topic_label}

Briefing:"""

            try:
                response = llm.complete(prompt)
                self.community_summaries[community_id] = response.text
                if progress_callback:
                    progress_callback(f"Summarized community {idx}/{total}")
            except Exception as exc:
                logger.error("Failed to summarize community %s: %s", community_id, exc)

    def get_community_summaries(self) -> dict:
        return self.community_summaries

    # ── Wiki article generation ────────────────────────────────────────────────

    async def generate_entity_wiki(self, node_id: str, llm, topic_name: str = "", force: bool = False) -> str:
        """Generate a Wikipedia-style article for a node and cache it."""
        if not force and node_id in self.entity_wikis:
            return self.entity_wikis[node_id]

        node = self.graph.nodes.get(node_id)
        if not node or not isinstance(node, EntityNode):
            return ""

        outgoing_lines, incoming_lines = [], []
        for rel in self.graph.relations.values():
            desc = rel.properties.get("relationship_description", "")
            if rel.source_id == node_id:
                tgt = self.graph.nodes.get(rel.target_id)
                tgt_name = tgt.name if tgt and isinstance(tgt, EntityNode) else rel.target_id
                outgoing_lines.append(f"- [{rel.label}] → {tgt_name}: {desc}")
            elif rel.target_id == node_id:
                src = self.graph.nodes.get(rel.source_id)
                src_name = src.name if src and isinstance(src, EntityNode) else rel.source_id
                incoming_lines.append(f"- {src_name} → [{rel.label}]: {desc}")

        community_ctx = ""
        cid = self.node_community.get(node_id)
        if cid is not None:
            summary = self.community_summaries.get(cid) or self.community_summaries.get(str(cid), "")
            if summary:
                community_ctx = f"\nCluster context:\n{summary}\n"

        rel_block = ""
        if outgoing_lines:
            rel_block += "Outgoing relationships:\n" + "\n".join(outgoing_lines[:25]) + "\n"
        if incoming_lines:
            rel_block += "Incoming relationships:\n" + "\n".join(incoming_lines[:25]) + "\n"

        prompt = (
            f'Write a concise Wikipedia-style encyclopedic article about "{node.name}" '
            f"in the context of {topic_name or 'the given domain'}.\n\n"
            f"Entity type: {node.label}\n"
            f"Description: {node.properties.get('entity_description', 'No description available')}\n"
            f"{community_ctx}\n"
            f"{rel_block}\n"
            "Write exactly 3 tight paragraphs — no more, no less. No markdown headers, no bullet lists.\n"
            "Paragraph 1: What this entity is and why it matters.\n"
            "Paragraph 2: Its key relationships and how they connect to other entities.\n"
            "Paragraph 3: Its role and significance in the broader domain.\n"
            "Each paragraph should be 3–5 sentences. Stop after the third paragraph.\n\n"
            "Article:"
        )

        try:
            response = await llm.acomplete(prompt)
            article = response.text.strip()
            if "</think>" in article:
                article = article.split("</think>")[-1].strip()
            self.entity_wikis[node_id] = article
            return article
        except Exception as exc:
            logger.error("Wiki generation failed for %s: %s", node.name, exc)
            return ""

    # ── Export for D3.js ───────────────────────────────────────────────────────

    # ── Deduplication ──────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Canonical key used to detect duplicate entity names."""
        n = re.sub(r"\s*\(.*?\)", "", name)        # strip "(MMM)", "(MCMC)" etc.
        n = n.replace("odelling", "odeling")        # British → American spelling
        n = n.replace("odels", "odeling")           # "Models" → treat as "Modeling" group? No.
        # Trailing 'Model' vs 'Modeling': treat both as same root
        n = re.sub(r"\bmodel\b", "modeling", n, flags=re.IGNORECASE)
        return n.strip().lower()

    def resolve_entities(self, llm, topic_name: str = "", batch_size: int = 60) -> dict[str, str]:
        """
        Ask the LLM to identify synonymous entity groups and return a merge map.
        Processes entities in batches to stay within context limits.
        Returns {alias: canonical} for every pair the LLM wants to merge.
        """
        graph = self.graph
        entities = [
            node for node in graph.nodes.values()
            if isinstance(node, EntityNode)
        ]
        if not entities:
            return {}

        edge_count: dict[str, int] = defaultdict(int)
        for rel in graph.relations.values():
            edge_count[rel.source_id] += 1
            edge_count[rel.target_id] += 1

        # Sort by type then name for stable batching
        entities.sort(key=lambda n: (n.label or "", n.name))

        merge_map: dict[str, str] = {}

        for i in range(0, len(entities), batch_size):
            batch = entities[i: i + batch_size]
            entity_lines = "\n".join(
                f"- \"{e.name}\" ({e.label}): {e.properties.get('entity_description', '')[:120]}"
                for e in batch
            )
            prompt = f"""You are reviewing a knowledge graph about "{topic_name or 'the given topic'}".
Below is a list of extracted entities. Identify any groups of entities that refer to the SAME real-world thing (same concept, company, technology, or person), but have been extracted with slightly different names — for example due to abbreviations, singular/plural, British/American spelling, acronyms, or company rebrands.

Rules:
- Only merge entities that are truly the same thing in this domain.
- Do NOT merge entities that are related but distinct (e.g. "Saturation" and "Saturation Curve" are different).
- Do NOT merge a general concept with a specific subtype (e.g. "Bayesian Methods" and "Bayesian Model" are different levels).
- Pick the most complete, descriptive name as the canonical name.
- If nothing should be merged, return an empty list.

Entities:
{entity_lines}

Return ONLY a raw JSON array of merge groups. Each group is a list of names where the FIRST element is the canonical name to keep:
[["canonical name", "alias 1", "alias 2"], ...]

If no merges are needed return: []"""

            try:
                response = llm.complete(prompt)
                raw = response.text.strip()
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
                match = re.search(r"\[.*\]", raw, re.DOTALL)
                if not match:
                    continue
                groups = json.loads(match.group())
                for group in groups:
                    if len(group) < 2:
                        continue
                    canonical = group[0]
                    for alias in group[1:]:
                        if alias != canonical and alias in graph.nodes:
                            merge_map[alias] = canonical
            except Exception as exc:
                logger.warning("Entity resolution batch %d failed: %s", i // batch_size, exc)

        logger.info("resolve_entities: %d merges identified by LLM", len(merge_map))
        return merge_map

    def deduplicate_nodes(self, aliases: dict[str, str] | None = None) -> int:
        """
        Merge entity nodes whose names normalize to the same string, plus any
        explicit alias mappings (e.g. {"Facebook": "Meta"}).
        Returns number of nodes removed. Modifies self.graph in place.
        """
        graph = self.graph

        edge_count: dict[str, int] = defaultdict(int)
        for rel in graph.relations.values():
            edge_count[rel.source_id] += 1
            edge_count[rel.target_id] += 1

        # Normalisation-based duplicates
        norm_groups: dict[str, list[str]] = defaultdict(list)
        for node_id, node in graph.nodes.items():
            if not isinstance(node, EntityNode):
                continue
            norm_groups[self._normalize_name(node.name)].append(node_id)

        merge_map: dict[str, str] = {}
        for ids in norm_groups.values():
            if len(ids) < 2:
                continue
            canonical = max(
                ids,
                key=lambda nid: (
                    edge_count[nid],
                    len(graph.nodes[nid].name),
                    graph.nodes[nid].name,
                ),
            )
            for nid in ids:
                if nid != canonical:
                    merge_map[nid] = canonical

        # Explicit alias overrides (rebrands, known synonyms)
        if aliases:
            for alias, canonical in aliases.items():
                if alias in graph.nodes and alias not in merge_map:
                    merge_map[alias] = canonical

        if not merge_map:
            return 0

        for rel_key, rel in list(graph.relations.items()):
            new_src = merge_map.get(rel.source_id, rel.source_id)
            new_tgt = merge_map.get(rel.target_id, rel.target_id)
            if new_src == new_tgt:
                del graph.relations[rel_key]
                continue
            rel.source_id = new_src
            rel.target_id = new_tgt

        for old_id in merge_map:
            graph.nodes.pop(old_id, None)

        logger.info("deduplicate_nodes: removed %d duplicate entity nodes", len(merge_map))
        return len(merge_map)

    def export_graph_data(self) -> dict:
        """
        Return a dict matching the JSON schema expected by the D3.js visualization:
          {nodes: [{id, label, type, description}], links: [{source, target, label, description}], communities: N}
        """
        nx_graph = self._to_networkx()

        node_meta: dict[str, dict] = {}
        for node in self.graph.nodes.values():
            if isinstance(node, EntityNode):
                node_meta[node.id] = {
                    "id": node.id,
                    "label": node.name,
                    "type": node.label or "OTHER",
                    "description": node.properties.get("entity_description", ""),
                }

        nodes_data = [node_meta[n] for n in nx_graph.nodes() if n in node_meta]

        links_data = [
            {
                "source": src,
                "target": tgt,
                "label": data.get("relationship", ""),
                "description": data.get("description", ""),
            }
            for src, tgt, data in nx_graph.edges(data=True)
        ]

        return {
            "nodes": nodes_data,
            "links": links_data,
            "communities": len(self.community_summaries),
        }

    # ── Persistence ────────────────────────────────────────────────────────────

    def save(self, directory: Path) -> None:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        # D3.js visualization data
        graph_data = self.export_graph_data()
        (directory / "graph_data.json").write_text(
            json.dumps(graph_data, indent=2), encoding="utf-8"
        )

        # Community summaries (human-readable, JSON)
        (directory / "communities.json").write_text(
            json.dumps(self.community_summaries, indent=2), encoding="utf-8"
        )

        # Cached wiki articles
        if self.entity_wikis:
            (directory / "entity_wikis.json").write_text(
                json.dumps(self.entity_wikis, indent=2), encoding="utf-8"
            )

        # Full store pickle (for fast query engine reload)
        with open(directory / "store.pkl", "wb") as fh:
            pickle.dump(self, fh)

        logger.info(
            "Saved graph to %s  (nodes=%d, edges=%d, communities=%d)",
            directory,
            len(graph_data["nodes"]),
            len(graph_data["links"]),
            graph_data["communities"],
        )

    @classmethod
    def load(cls, directory: Path) -> "GraphRAGStore":
        directory = Path(directory)
        pkl_path = directory / "store.pkl"

        communities_path = directory / "communities.json"

        # Fast path: pickle
        if pkl_path.exists():
            try:
                with open(pkl_path, "rb") as fh:
                    store = pickle.load(fh)
                logger.info("Loaded graph store from pickle: %s", pkl_path)
                # Patch: pickle may have been saved before communities were built
                if not store.community_summaries and communities_path.exists():
                    store.community_summaries = json.loads(
                        communities_path.read_text(encoding="utf-8")
                    )
                    logger.info("Patched community summaries from JSON: %s", communities_path)
                    # Regenerate graph_data.json so the UI stats are consistent
                    graph_data_path = directory / "graph_data.json"
                    try:
                        graph_data_path.write_text(
                            json.dumps(store.export_graph_data(), indent=2), encoding="utf-8"
                        )
                        logger.info("Regenerated graph_data.json with corrected community count")
                    except Exception as exc:
                        logger.warning("Could not regenerate graph_data.json: %s", exc)
                # Load cached wiki articles (may not exist for older graphs)
                wikis_path = directory / "entity_wikis.json"
                if not store.entity_wikis and wikis_path.exists():
                    try:
                        store.entity_wikis = json.loads(wikis_path.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                return store
            except Exception as exc:
                logger.warning("Pickle load failed (%s) — falling back to JSON", exc)

        # Fallback: rebuild from communities.json (no re-extraction needed)
        if communities_path.exists():
            store = cls()
            store.community_summaries = json.loads(
                communities_path.read_text(encoding="utf-8")
            )
            logger.info("Loaded community summaries from JSON: %s", communities_path)
            return store

        raise FileNotFoundError(
            f"No saved graph found in {directory}. Build it first via POST /api/topics/{{topic}}/build"
        )
