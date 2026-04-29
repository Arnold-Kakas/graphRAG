"""
GraphRAGStore — extends LlamaIndex's SimplePropertyGraphStore with:
  - Leiden community detection
  - LLM-generated community summaries
  - save() / load() for persistence between sessions
  - export_graph_data() for D3.js visualization
"""

from __future__ import annotations

import asyncio
import json
import logging
import pickle
import re
from collections import defaultdict
from pathlib import Path
from typing import Callable, Optional

import hashlib
import networkx as nx
from graspologic.partition import hierarchical_leiden
from llama_index.core.graph_stores import SimplePropertyGraphStore
from llama_index.core.graph_stores.types import EntityNode, Relation

logger = logging.getLogger(__name__)


# ── JSON extraction helpers ───────────────────────────────────────────────────
# LLMs routinely wrap JSON in prose, code fences, or multiple blocks. A greedy
# `\{.*\}` regex fails on any of those. Balanced-brace scanning is robust and
# a handful of lines; worth the tiny duplication over a separate module.

def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_balanced(text: str, open_ch: str, close_ch: str) -> Optional[str]:
    """Return the first balanced {...} or [...] block, honouring string literals."""
    start = text.find(open_ch)
    if start < 0:
        return None
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if in_str:
            if c == "\\":
                escape = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def extract_json_object(text: str) -> Optional[dict]:
    text = _strip_code_fences(text)
    blob = _extract_balanced(text, "{", "}")
    if not blob:
        return None
    try:
        return json.loads(blob)
    except Exception:
        return None


def extract_json_array(text: str) -> Optional[list]:
    text = _strip_code_fences(text)
    blob = _extract_balanced(text, "[", "]")
    if not blob:
        return None
    try:
        return json.loads(blob)
    except Exception:
        return None


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

    # Declared here for type hints only. The parent class (SimplePropertyGraphStore)
    # is Pydantic-based, so these must be initialised per-instance in __init__
    # rather than as class-level defaults — otherwise every GraphRAGStore() would
    # share the same dicts across topics.
    community_summaries: dict = {}
    entity_wikis: dict = {}
    node_community: dict = {}  # node_id → community_id (str)
    entity_index: dict = {}    # node_id → {name, type, community, degree, sources}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rebind each attribute to a fresh dict on this instance so class-level
        # dicts aren't accidentally shared.
        self.community_summaries = {}
        self.entity_wikis = {}
        self.node_community = {}
        self.entity_index = {}

    # ── Node upsert ────────────────────────────────────────────────────────────

    def upsert_nodes_merge(self, nodes: list) -> None:
        """Upsert nodes, merging entity_description and source provenance if a node already exists."""
        for node in nodes:
            existing = self.graph.nodes.get(node.id)
            if existing and isinstance(existing, EntityNode):
                new_desc = node.properties.get("entity_description", "")
                existing_desc = existing.properties.get("entity_description", "")
                if new_desc and new_desc not in existing_desc:
                    existing.properties["entity_description"] = (
                        existing_desc + " " + new_desc if existing_desc else new_desc
                    ).strip()
                # Track every source file that contributed to this entity
                new_source = node.properties.get("filename") or node.properties.get("source")
                if new_source:
                    sources = existing.properties.setdefault("sources", [])
                    if new_source not in sources:
                        sources.append(new_source)
            else:
                # Seed sources list from the incoming node's filename/source
                source = node.properties.get("filename") or node.properties.get("source")
                if source:
                    node.properties.setdefault("sources", [source])
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

        clusters = hierarchical_leiden(nx_graph, max_cluster_size=max_cluster_size, random_seed=42)
        num_communities = len(set(c.cluster for c in clusters))
        _progress(f"Found {num_communities} communities — generating summaries...")

        # Build node→community mapping for wiki generation.
        # Store cluster IDs as strings throughout to match the JSON round-trip.
        self.node_community = {item.node: str(item.cluster) for item in clusters}

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
                # Always store cluster IDs as strings — matches the JSON round-trip,
                # and every lookup site already calls str(cid) or uses string keys.
                self.community_summaries[str(community_id)] = response.text
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
            summary = self.community_summaries.get(str(cid), "")
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

    # ── Graph index ────────────────────────────────────────────────────────────

    def build_index(self) -> dict:
        """
        Build a compact, navigation-friendly index of the graph.

        The index is a second layer on top of community summaries, inspired by
        Karpathy's index.md pattern: it catalogs every entity with just enough
        metadata (type, degree, cluster, one-line description) that the LLM can
        see the shape of the whole graph at a glance, pick relevant entities,
        and then drill into community summaries / wiki articles for detail.

        Returns the same dict that is stored in self.entity_index and later
        serialised to graph_index.json.
        """
        # Degree
        degree: dict[str, int] = defaultdict(int)
        for rel in self.graph.relations.values():
            degree[rel.source_id] += 1
            degree[rel.target_id] += 1

        entities: dict[str, dict] = {}
        by_type: dict[str, list[str]] = defaultdict(list)
        for node in self.graph.nodes.values():
            if not isinstance(node, EntityNode):
                continue
            desc = node.properties.get("entity_description", "")
            # Keep the first sentence or ~180 chars as a one-liner
            first_sent = re.split(r"(?<=[.!?])\s+", desc.strip(), maxsplit=1)[0]
            one_liner = first_sent[:180].strip()
            entry = {
                "id": node.id,
                "name": node.name,
                "type": node.label or "OTHER",
                "description": one_liner,
                "degree": degree.get(node.id, 0),
                "community": self.node_community.get(node.id),
                "sources": node.properties.get("sources", []),
            }
            entities[node.id] = entry
            by_type[entry["type"]].append(node.id)

        # Top hubs — highest-degree entities overall
        top_hubs = sorted(
            entities.values(),
            key=lambda e: e["degree"],
            reverse=True,
        )[:15]
        top_hubs = [{"id": e["id"], "name": e["name"], "type": e["type"], "degree": e["degree"]} for e in top_hubs]

        # Community → member IDs (for rapid lookup when rendering)
        by_community: dict[str, list[str]] = defaultdict(list)
        for nid, cid in self.node_community.items():
            if nid in entities:
                by_community[str(cid)].append(nid)

        # Sort type buckets by descending degree for readability
        for t, ids in by_type.items():
            ids.sort(key=lambda nid: -entities[nid]["degree"])
        for cid, ids in by_community.items():
            ids.sort(key=lambda nid: -entities[nid]["degree"])

        self.entity_index = {
            "entities": entities,
            "by_type": dict(by_type),
            "by_community": dict(by_community),
            "top_hubs": top_hubs,
            "type_counts": {t: len(ids) for t, ids in by_type.items()},
        }
        return self.entity_index

    def render_index_markdown(self, topic: str = "") -> str:
        """Human-readable markdown catalog — useful outside the app (Obsidian, grep, etc.)."""
        if not self.entity_index:
            self.build_index()
        idx = self.entity_index
        ents = idx["entities"]
        lines: list[str] = []
        lines.append(f"# Graph index — {topic}" if topic else "# Graph index")
        lines.append("")
        lines.append(
            f"_{len(ents)} entities · {len(idx['by_type'])} types · "
            f"{len(idx['by_community'])} communities_"
        )
        lines.append("")

        if idx["top_hubs"]:
            lines.append("## Top hubs")
            lines.append("")
            for h in idx["top_hubs"]:
                lines.append(f"- **{h['name']}** ({h['type']}) — {h['degree']} connections")
            lines.append("")

        lines.append("## By type")
        for t in sorted(idx["by_type"].keys()):
            ids = idx["by_type"][t]
            lines.append("")
            lines.append(f"### {t} ({len(ids)})")
            for nid in ids:
                e = ents[nid]
                tail = f" — {e['description']}" if e["description"] else ""
                lines.append(f"- **{e['name']}**{tail}")

        return "\n".join(lines) + "\n"

    # ── Obsidian export ────────────────────────────────────────────────────────

    @staticmethod
    def _obsidian_safe_filename(name: str) -> str:
        """
        Map an entity name to a filename that is safe on Windows/macOS/Linux
        and that Obsidian's `[[wiki link]]` resolver will pick up.
        Strips `\\ / : * ? " < > |`, collapses whitespace, caps length.
        """
        cleaned = re.sub(r'[\\/:*?"<>|]+', " ", name)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            cleaned = "untitled"
        return cleaned[:120]

    def export_obsidian(self, target_dir: Path, topic: str = "") -> dict:
        """
        Write one markdown file per entity in `target_dir`, suitable for
        importing into an Obsidian vault.

        Each file has YAML frontmatter (id, type, sources, community, degree)
        and a body with the description, the cluster context, and inline
        `[[Other Entity]]` links to every connected node — Obsidian resolves
        those by filename, which is why filenames mirror entity names.

        A top-level `_index.md` summarises the export. Returns a stats dict.
        """
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Make sure the index is populated for degree info — cheap, no LLM.
        if not self.entity_index:
            self.build_index()
        index_entities = self.entity_index.get("entities", {})

        # Resolve entity_id → filename stem (without .md). Uses safe filename
        # disambiguated by id suffix if two entities collapse to the same name.
        stems: dict[str, str] = {}
        used: dict[str, int] = {}
        for node_id, node in self.graph.nodes.items():
            if not isinstance(node, EntityNode):
                continue
            base = self._obsidian_safe_filename(node.name)
            count = used.get(base, 0)
            stem = base if count == 0 else f"{base} ({count + 1})"
            used[base] = count + 1
            stems[node_id] = stem

        # Pre-compute neighbours per node from the relation list
        outgoing: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
        incoming: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
        for rel in self.graph.relations.values():
            desc = rel.properties.get("relationship_description", "")
            outgoing[rel.source_id].append((rel.target_id, rel.label, desc))
            incoming[rel.target_id].append((rel.source_id, rel.label, desc))

        files_written = 0
        for node_id, node in self.graph.nodes.items():
            if not isinstance(node, EntityNode):
                continue
            stem = stems[node_id]
            entry = index_entities.get(node_id, {})
            cid = self.node_community.get(node_id)
            sources = node.properties.get("sources", []) or []
            description = node.properties.get("entity_description", "").strip()
            wiki = self.entity_wikis.get(node_id, "").strip()

            front_lines = [
                "---",
                f"id: {node_id}",
                f"type: {node.label or 'OTHER'}",
                f"degree: {entry.get('degree', 0)}",
            ]
            if cid is not None:
                front_lines.append(f"community: {cid}")
            if sources:
                front_lines.append("sources:")
                for s in sources:
                    front_lines.append(f"  - {s}")
            if topic:
                front_lines.append(f"topic: {topic}")
            front_lines.append("tags: [graphrag, " + (node.label or "OTHER").lower() + "]")
            front_lines.append("---")

            body: list[str] = [f"# {node.name}", ""]
            if description:
                body.append(description)
                body.append("")
            if wiki:
                body.append("## Article")
                body.append("")
                body.append(wiki)
                body.append("")

            if cid is not None:
                summary = self.community_summaries.get(str(cid), "").strip()
                if summary:
                    body.append(f"## Cluster context (community {cid})")
                    body.append("")
                    body.append(summary)
                    body.append("")

            def _format_neighbour(neighbour_id: str, label: str, desc: str) -> str:
                neighbour_node = self.graph.nodes.get(neighbour_id)
                if neighbour_node and isinstance(neighbour_node, EntityNode):
                    n_stem = stems.get(neighbour_id, neighbour_node.name)
                    link = f"[[{n_stem}|{neighbour_node.name}]]"
                else:
                    link = f"`{neighbour_id}`"
                line = f"- **{label}** → {link}"
                if desc:
                    line += f" — {desc}"
                return line

            if outgoing.get(node_id):
                body.append("## Outgoing relationships")
                body.append("")
                for tgt_id, label, desc in outgoing[node_id]:
                    body.append(_format_neighbour(tgt_id, label, desc))
                body.append("")
            if incoming.get(node_id):
                body.append("## Incoming relationships")
                body.append("")
                for src_id, label, desc in incoming[node_id]:
                    body.append(_format_neighbour(src_id, label, desc))
                body.append("")

            (target_dir / f"{stem}.md").write_text(
                "\n".join(front_lines) + "\n\n" + "\n".join(body),
                encoding="utf-8",
            )
            files_written += 1

        # Top-level overview file — links to top hubs and a per-type roll-up
        overview_lines = [
            f"# {topic or 'GraphRAG vault'}",
            "",
            f"_{files_written} entity notes · {len(self.community_summaries)} communities_",
            "",
        ]
        top_hubs = self.entity_index.get("top_hubs", [])
        if top_hubs:
            overview_lines.append("## Top hubs")
            overview_lines.append("")
            for h in top_hubs:
                stem = stems.get(h["id"], h["name"])
                overview_lines.append(f"- [[{stem}|{h['name']}]] ({h['type']}) — {h['degree']} connections")
            overview_lines.append("")
        by_type = self.entity_index.get("by_type", {})
        if by_type:
            overview_lines.append("## By type")
            overview_lines.append("")
            for t in sorted(by_type.keys()):
                overview_lines.append(f"- **{t}** — {len(by_type[t])} entities")
            overview_lines.append("")
        (target_dir / "_index.md").write_text("\n".join(overview_lines), encoding="utf-8")

        logger.info("Obsidian export: wrote %d entity notes to %s", files_written, target_dir)
        return {
            "files_written": files_written,
            "target_dir": str(target_dir),
        }

    def index_digest(self, max_entities: int = 120) -> str:
        """
        A short, token-efficient digest of the index for injection into prompts.
        Groups entities by type, caps per type to keep the prompt bounded.
        """
        if not self.entity_index:
            self.build_index()
        idx = self.entity_index
        ents = idx["entities"]
        if not ents:
            return ""

        # Per-type budget, proportional to type size but bounded
        total_budget = max_entities
        type_buckets = idx["by_type"]
        per_type_cap = max(5, total_budget // max(1, len(type_buckets)))

        lines: list[str] = []
        lines.append(f"Graph contains {len(ents)} entities across {len(type_buckets)} types.")
        if idx["top_hubs"]:
            hubs = ", ".join(f"{h['name']} ({h['type']})" for h in idx["top_hubs"][:8])
            lines.append(f"Most connected: {hubs}.")

        for t in sorted(type_buckets.keys()):
            ids = type_buckets[t][:per_type_cap]
            names = ", ".join(ents[nid]["name"] for nid in ids)
            if len(type_buckets[t]) > per_type_cap:
                names += f", … (+{len(type_buckets[t]) - per_type_cap} more)"
            lines.append(f"- **{t}**: {names}")
        return "\n".join(lines)

    # ── Export for D3.js ───────────────────────────────────────────────────────

    # ── Deduplication ──────────────────────────────────────────────────────────

    # Minimal, domain-neutral British→American spelling map. Keep this small and
    # unambiguous. Topic-specific synonyms belong in `ontology.aliases`.
    _SPELLING_NORMALISATIONS = {
        "odelling": "odeling",       # Modelling → Modeling
        "rganisation": "rganization",  # Organisation → Organization
        "ptimisation": "ptimization",  # Optimisation → Optimization
        "nalyse": "nalyze",           # Analyse → Analyze
        "ehaviour": "ehavior",        # Behaviour → Behavior
    }

    @staticmethod
    def _normalize_name(name: str) -> str:
        """
        Canonical key used to detect duplicate entity names.
        Only applies safe transforms: whitespace, case, parentheticals,
        and a small British→American spelling normalisation. Anything
        domain-specific (plural/singular, activity vs. artefact) must be
        handled via `ontology.aliases`, not hard-coded here.
        """
        n = re.sub(r"\s*\(.*?\)", "", name)  # strip "(MMM)", "(MCMC)" etc.
        for uk, us in GraphRAGStore._SPELLING_NORMALISATIONS.items():
            n = n.replace(uk, us)
        return re.sub(r"\s+", " ", n).strip().lower()

    # Token suffixes safe to strip without conflating distinct words.
    # "ROAS"/"Status"/"Bayes" must survive — exclusions cover -ss/-us/-is/-os/-as/-es endings
    # except where the rule explicitly handles them (-ies → -y).
    @staticmethod
    def _stem_token(tok: str) -> str:
        if len(tok) > 5 and tok.endswith("ing"):
            return tok[:-3]                       # modeling → model
        if len(tok) > 4 and tok.endswith("ies"):
            return tok[:-3] + "y"                 # methodologies → methodology
        if (
            len(tok) > 3
            and tok.endswith("s")
            and not tok.endswith(("ss", "us", "is", "os", "as"))
        ):
            return tok[:-1]                       # channels → channel, sales → sale
        return tok

    @staticmethod
    def _token_signature(name: str) -> str:
        """
        Stem-aware signature for synonym detection. Catches surface variants
        the mild `_normalize_name` misses — "Marketing Mix Modeling" and
        "Marketing Mix Model" both reduce to "marketing mix model".

        Token order is preserved so "Mix Modeling" and "Modeling Mix" do NOT
        collapse — that would over-merge.
        """
        n = re.sub(r"\s*\(.*?\)", "", name)
        for uk, us in GraphRAGStore._SPELLING_NORMALISATIONS.items():
            n = n.replace(uk, us)
        n = n.lower()
        tokens = re.findall(r"[a-z0-9]+", n)
        return " ".join(GraphRAGStore._stem_token(t) for t in tokens)

    @staticmethod
    def _acronym_pairs(names: list[str]) -> dict[str, str]:
        """
        Detect acronym ↔ expansion pairs that coexist in the graph.
        E.g. "ROAS" alongside "Return on Ads Spend" (initials match → merge).
        Returns {acronym_name: expansion_name}. Caller decides which side wins.
        """
        # Build initials → longest-expansion lookup. Skips small connector tokens
        # ("on", "of", "the") so "Return on Ads Spend" still produces "ras"…
        # but we want "roas", so we DON'T skip — initials use every token.
        # Trade-off: misses some real acronyms whose expansions drop stopwords,
        # but avoids false positives. Acceptable.
        by_initials: dict[str, str] = {}
        for name in names:
            tokens = re.findall(r"[A-Za-z][A-Za-z0-9]*", name)
            if len(tokens) < 2:
                continue
            initials = "".join(t[0] for t in tokens).lower()
            if 2 <= len(initials) <= 8:
                # Prefer the longest expansion when several names share initials
                if initials not in by_initials or len(name) > len(by_initials[initials]):
                    by_initials[initials] = name

        pairs: dict[str, str] = {}
        for name in names:
            # Acronym criteria: short, no spaces, ≥ 2 uppercase letters.
            if " " in name or not 2 <= len(name) <= 8:
                continue
            if sum(1 for c in name if c.isupper()) < 2:
                continue
            expansion = by_initials.get(name.lower())
            if expansion and expansion != name:
                pairs[name] = expansion
        return pairs

    async def resolve_entities(
        self,
        llm,
        topic_name: str = "",
        max_entities_per_batch: int = 25,
        char_budget: int = 6000,
        timeout: float = 120.0,
    ) -> dict[str, str]:
        """
        Ask the LLM to identify synonymous entity groups and return a merge map.

        Runs two passes with different orderings so likely-synonymous entities
        end up in the same batch at least once:
          - Pass 1 sorts by token signature, which clusters surface variants
            ("Marketing Mix Model", "Marketing Mix Modeling", "MMM").
          - Pass 2 sorts by type → name, the original alphabetical order.

        Each pass batches by both an entity count cap and a character budget
        so a single batch never overflows the context window. Pass 2 skips any
        node already merged in pass 1. Each LLM call is capped at `timeout`
        seconds — timed-out batches are skipped rather than blocking forever.

        Returns {alias: canonical} for every pair the LLM wants to merge.
        """
        graph = self.graph
        entities = [
            node for node in graph.nodes.values()
            if isinstance(node, EntityNode)
        ]
        if not entities:
            return {}

        merge_map: dict[str, str] = {}

        # Pass 1: stem-signature ordering pulls surface variants together
        pass1 = sorted(entities, key=lambda n: (self._token_signature(n.name), n.name))
        merge_map.update(
            await self._resolve_one_pass(pass1, llm, topic_name, max_entities_per_batch, char_budget, pass_label="signature", timeout=timeout)
        )

        # Pass 2: type → name ordering catches type-level synonyms missed in pass 1
        already_merged = set(merge_map.keys())
        pass2 = [n for n in entities if n.id not in already_merged]
        pass2.sort(key=lambda n: (n.label or "", n.name))
        if pass2:
            second = await self._resolve_one_pass(
                pass2, llm, topic_name, max_entities_per_batch, char_budget, pass_label="type", timeout=timeout
            )
            for alias, canonical in second.items():
                # Don't override an earlier merge — first decision wins
                if alias not in merge_map:
                    merge_map[alias] = canonical

        logger.info("resolve_entities: %d merges identified by LLM across 2 passes", len(merge_map))
        return merge_map

    async def _resolve_one_pass(
        self,
        entities: list[EntityNode],
        llm,
        topic_name: str,
        max_entities_per_batch: int,
        char_budget: int,
        pass_label: str,
        timeout: float = 120.0,
    ) -> dict[str, str]:
        graph = self.graph

        def _entity_line(e: EntityNode) -> str:
            return f"- \"{e.name}\" ({e.label}): {e.properties.get('entity_description', '')[:120]}"

        batches: list[list[EntityNode]] = []
        current: list[EntityNode] = []
        current_chars = 0
        for e in entities:
            line_len = len(_entity_line(e)) + 1
            over_count = len(current) >= max_entities_per_batch
            over_budget = current and (current_chars + line_len) > char_budget
            if over_count or over_budget:
                batches.append(current)
                current = []
                current_chars = 0
            current.append(e)
            current_chars += line_len
        if current:
            batches.append(current)

        merge_map: dict[str, str] = {}

        for batch_idx, batch in enumerate(batches):
            entity_lines = "\n".join(_entity_line(e) for e in batch)
            prompt = f"""Output ONLY a raw JSON array as instructed below. No commentary, no explanation, no step-by-step reasoning.

You are reviewing a knowledge graph about "{topic_name or 'the given topic'}".
Below is a list of extracted entities. Group entities that refer to the SAME real-world thing — same concept, company, technology, person, or method — even if they were extracted with slightly different names.

When in doubt, MERGE. The graph was built from many documents and the same concept routinely shows up with these surface variations:
- singular/plural ("Channel" vs "Channels")
- gerund/noun ("Modeling" vs "Model" — when both clearly refer to the same activity/method)
- spelling variants ("Modelling" vs "Modeling", "Optimisation" vs "Optimization")
- acronyms vs expansions ("MMM" / "Marketing Mix Modeling", "ROAS" / "Return on Ads Spend")
- noun-order swaps that mean the same thing ("Marketing Mix Model" / "Media Mix Model" — same family/method)
- minor word substitutions for the same field ("Marketing Mix Modeling" / "Media Mix Modeling")
- company rebrands ("Facebook" / "Meta", "Twitter" / "X")

Do NOT merge:
- a general concept with a specific subtype ("Bayesian Methods" vs "Bayesian Model" — different levels of abstraction)
- two distinct artefacts that share a word ("Saturation" the property vs "Saturation Curve" the chart)
- entities of clearly different types (a person vs a method)

Pick the most complete, descriptive name as the canonical (FIRST element of each group).

Entities:
{entity_lines}

Return ONLY a raw JSON array of merge groups. Each group is a list of names where the FIRST element is the canonical name to keep:
[["canonical name", "alias 1", "alias 2"], ...]

If nothing should be merged, return: []"""

            try:
                response = await asyncio.wait_for(llm.acomplete(prompt), timeout=timeout)
                raw = response.text
                if "</think>" in raw:
                    raw = raw.split("</think>")[-1]
                groups = extract_json_array(raw)
                if not groups:
                    continue
                for group in groups:
                    if not isinstance(group, list) or len(group) < 2:
                        continue
                    canonical = group[0]
                    if canonical not in graph.nodes:
                        # LLM may rewrite the canonical — fall back to the longest in-graph name
                        in_graph = [a for a in group if a in graph.nodes]
                        if not in_graph:
                            continue
                        canonical = max(in_graph, key=len)
                    for alias in group:
                        if alias != canonical and alias in graph.nodes:
                            merge_map[alias] = canonical
            except asyncio.TimeoutError:
                logger.warning("Entity resolution (%s) batch %d timed out after %.0fs — skipping", pass_label, batch_idx, timeout)
            except Exception as exc:
                logger.warning("Entity resolution (%s) batch %d failed: %s", pass_label, batch_idx, exc)

        logger.info(
            "resolve_entities[%s]: %d merges from %d batches",
            pass_label, len(merge_map), len(batches),
        )
        return merge_map

    def remove_source_references(self, removed_filenames: set[str]) -> dict:
        """
        Remove references to deleted source files from the graph.

        For each node: strip `removed_filenames` from its `sources` list.
        Nodes whose `sources` becomes empty are deleted along with incident edges.
        Nodes with no tracked sources at all (legacy, pre-provenance) are preserved.

        Returns {"nodes_removed": int, "edges_removed": int, "nodes_trimmed": int}.
        """
        if not removed_filenames:
            return {"nodes_removed": 0, "edges_removed": 0, "nodes_trimmed": 0}

        graph = self.graph
        to_delete: set[str] = set()
        trimmed = 0

        for node_id, node in list(graph.nodes.items()):
            if not isinstance(node, EntityNode):
                continue
            sources = node.properties.get("sources")
            if not sources:
                # Legacy node with no provenance tracking — leave it alone.
                continue
            new_sources = [s for s in sources if s not in removed_filenames]
            if len(new_sources) == len(sources):
                continue
            if not new_sources:
                to_delete.add(node_id)
            else:
                node.properties["sources"] = new_sources
                trimmed += 1

        edges_removed = 0
        if to_delete:
            for rel_key, rel in list(graph.relations.items()):
                if rel.source_id in to_delete or rel.target_id in to_delete:
                    del graph.relations[rel_key]
                    edges_removed += 1
            for nid in to_delete:
                graph.nodes.pop(nid, None)

        logger.info(
            "remove_source_references: %d node(s) dropped, %d edge(s) dropped, "
            "%d node(s) trimmed (kept with fewer sources)",
            len(to_delete), edges_removed, trimmed,
        )
        return {
            "nodes_removed": len(to_delete),
            "edges_removed": edges_removed,
            "nodes_trimmed": trimmed,
        }

    def deduplicate_nodes(self, aliases: dict[str, str] | None = None) -> tuple[int, set[str]]:
        """
        Merge entity nodes that look like the same thing under three signals:
          1. `_normalize_name`  — light: case + spelling + parentheticals.
          2. `_token_signature` — stem-aware: catches "Modeling"/"Model",
             plurals, "ies"→"y" — surface variants the LLM resolver misses.
          3. `_acronym_pairs`   — pairs an acronym ("ROAS") with its expansion
             ("Return on Ads Spend") when both are present in the graph.
          4. Explicit aliases from ontology + learned-aliases (rebrands).

        Merge chains are resolved transitively (A→B and B→C collapse to A→C).
        Returns number of nodes removed. Modifies self.graph in place.
        """
        graph = self.graph

        edge_count: dict[str, int] = defaultdict(int)
        for rel in graph.relations.values():
            edge_count[rel.source_id] += 1
            edge_count[rel.target_id] += 1

        entity_nodes = [
            (nid, node) for nid, node in graph.nodes.items()
            if isinstance(node, EntityNode)
        ]

        def _pick_canonical(ids: list[str]) -> str:
            return max(
                ids,
                key=lambda nid: (
                    edge_count[nid],
                    len(graph.nodes[nid].name),
                    graph.nodes[nid].name,
                ),
            )

        merge_map: dict[str, str] = {}

        def _record_merge(loser: str, winner: str) -> None:
            """Record loser→winner so chains stay consistent."""
            if loser == winner or loser not in graph.nodes:
                return
            # If the winner itself is being merged elsewhere, follow the chain
            seen = {loser}
            while winner in merge_map and merge_map[winner] != winner:
                if winner in seen:
                    return
                seen.add(winner)
                winner = merge_map[winner]
            if loser == winner:
                return
            # If loser already maps somewhere, redirect that target too
            if loser in merge_map:
                old_target = merge_map[loser]
                if old_target != winner:
                    merge_map[old_target] = winner
            merge_map[loser] = winner

        # 1. Normalised-name groups
        norm_groups: dict[str, list[str]] = defaultdict(list)
        for nid, node in entity_nodes:
            norm_groups[self._normalize_name(node.name)].append(nid)
        for ids in norm_groups.values():
            if len(ids) < 2:
                continue
            canonical = _pick_canonical(ids)
            for nid in ids:
                _record_merge(nid, canonical)

        # 2. Token-signature groups (after step 1 so canonical IDs already win)
        sig_groups: dict[str, list[str]] = defaultdict(list)
        for nid, node in entity_nodes:
            sig_groups[self._token_signature(node.name)].append(nid)
        for ids in sig_groups.values():
            if len(ids) < 2:
                continue
            canonical = _pick_canonical(ids)
            for nid in ids:
                _record_merge(nid, canonical)

        # 3. Acronym ↔ expansion (e.g. "ROAS" → "Return on Ads Spend").
        # The expansion almost always wins because it has more edges and is
        # longer, but `_pick_canonical` decides per-pair via edge_count.
        names_to_ids: dict[str, str] = {}
        for nid, node in entity_nodes:
            names_to_ids.setdefault(node.name, nid)
        acronym_pairs = self._acronym_pairs(list(names_to_ids.keys()))
        for short_name, long_name in acronym_pairs.items():
            short_id = names_to_ids.get(short_name)
            long_id = names_to_ids.get(long_name)
            if not short_id or not long_id:
                continue
            canonical = _pick_canonical([short_id, long_id])
            loser = long_id if canonical == short_id else short_id
            _record_merge(loser, canonical)

        # 4. Explicit alias overrides (rebrands, known synonyms)
        if aliases:
            for alias, canonical in aliases.items():
                if alias in graph.nodes and canonical in graph.nodes:
                    _record_merge(alias, canonical)

        if not merge_map:
            return 0, set()

        # Final chain flattening so every loser maps directly to the terminal canonical
        for loser in list(merge_map.keys()):
            target = merge_map[loser]
            seen = {loser}
            while target in merge_map and merge_map[target] != target:
                if target in seen:
                    break
                seen.add(target)
                target = merge_map[target]
            merge_map[loser] = target

        # Carry descriptions and source provenance over to the canonical node.
        # Track winners whose description was actually extended — caller can
        # pass those IDs to resummmarize_merged_descriptions() for LLM cleanup.
        winners_with_merged_desc: set[str] = set()
        for loser_id, winner_id in merge_map.items():
            loser = graph.nodes.get(loser_id)
            winner = graph.nodes.get(winner_id)
            if not isinstance(loser, EntityNode) or not isinstance(winner, EntityNode):
                continue
            loser_desc = loser.properties.get("entity_description", "")
            winner_desc = winner.properties.get("entity_description", "")
            if loser_desc and loser_desc not in winner_desc:
                winner.properties["entity_description"] = (
                    (winner_desc + " " + loser_desc) if winner_desc else loser_desc
                ).strip()
                winners_with_merged_desc.add(winner_id)
            for src in loser.properties.get("sources", []) or []:
                winner_sources = winner.properties.setdefault("sources", [])
                if src not in winner_sources:
                    winner_sources.append(src)

        # Merge relations and drop self-loops created by the merge
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

        # Collapse duplicate relations created by the merge. Two relations with
        # the same (source, label, target) are kept as one; descriptions are
        # concatenated so no provenance text is lost.
        seen: dict[tuple[str, str, str], str] = {}
        dup_count = 0
        for rel_key, rel in list(graph.relations.items()):
            sig = (rel.source_id, rel.label, rel.target_id)
            if sig in seen:
                keeper_key = seen[sig]
                keeper = graph.relations[keeper_key]
                new_desc = rel.properties.get("relationship_description", "")
                keep_desc = keeper.properties.get("relationship_description", "")
                if new_desc and new_desc not in keep_desc:
                    keeper.properties["relationship_description"] = (
                        (keep_desc + " " + new_desc) if keep_desc else new_desc
                    ).strip()
                del graph.relations[rel_key]
                dup_count += 1
            else:
                seen[sig] = rel_key

        logger.info(
            "deduplicate_nodes: removed %d duplicate entity nodes, %d redundant relations",
            len(merge_map), dup_count,
        )
        return len(merge_map), winners_with_merged_desc

    async def resummmarize_merged_descriptions(
        self,
        node_ids: set[str],
        llm,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> int:
        """
        For each node in node_ids, ask the LLM to rewrite its entity_description
        as a single coherent paragraph, removing the redundancy left by concatenation.
        Returns the number of descriptions successfully rewritten.
        """
        total = len(node_ids)
        count = 0
        for i, node_id in enumerate(node_ids, 1):
            node = self.graph.nodes.get(node_id)
            if not isinstance(node, EntityNode):
                continue
            desc = node.properties.get("entity_description", "").strip()
            if not desc:
                continue

            prompt = (
                f'The following description for the entity "{node.name}" ({node.label}) was assembled '
                f"by merging text from multiple sources. Rewrite it as a single concise description "
                f"(2–4 sentences), removing redundancy while preserving every unique fact.\n\n"
                f"Combined text:\n{desc}\n\n"
                f"Unified description:"
            )
            try:
                response = await llm.acomplete(prompt)
                text = response.text.strip()
                if "</think>" in text:
                    text = text.split("</think>")[-1].strip()
                if text:
                    node.properties["entity_description"] = text
                    count += 1
            except Exception as exc:
                logger.warning("Failed to re-summarize description for %s: %s", node.name, exc)

            if progress_callback:
                progress_callback(f"Re-summarizing descriptions {i}/{total}")

        logger.info("resummmarize_merged_descriptions: rewrote %d/%d descriptions", count, total)
        return count

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

        # Navigation index — machine-readable JSON + human-readable markdown.
        # Built lazily if the caller didn't already populate it.
        if not self.entity_index:
            self.build_index()
        (directory / "graph_index.json").write_text(
            json.dumps(self.entity_index, indent=2), encoding="utf-8"
        )
        topic_label = directory.name.replace("_", " ")
        (directory / "index.md").write_text(
            self.render_index_markdown(topic=topic_label), encoding="utf-8"
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
                    raw_summaries = json.loads(
                        communities_path.read_text(encoding="utf-8")
                    )
                    # Normalise keys to str — downstream code assumes str keys
                    store.community_summaries = {str(k): v for k, v in raw_summaries.items()}
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
                # Older pickles may have stored cluster IDs as ints in node_community.
                # Coerce to strings so lookups match the JSON-sourced summaries.
                if store.node_community and any(
                    not isinstance(v, str) for v in store.node_community.values()
                ):
                    store.node_community = {k: str(v) for k, v in store.node_community.items()}
                # Load graph index if present, otherwise build it on the fly
                # from the already-loaded nodes/relations. Costs no LLM calls —
                # the index is derived entirely from the in-memory graph.
                index_path = directory / "graph_index.json"
                if not store.entity_index and index_path.exists():
                    try:
                        store.entity_index = json.loads(index_path.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                if not store.entity_index and store.graph.nodes:
                    try:
                        store.build_index()
                    except Exception as exc:
                        logger.warning("Index build on load failed: %s", exc)
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
