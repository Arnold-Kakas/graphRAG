"""
GraphRAGQueryEngine — two-phase community-based query answering.

Phase 1: Ask the cheaper LLM whether each community summary is relevant.
Phase 2: Aggregate relevant partial answers with the stronger LLM.
"""

from __future__ import annotations

import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from typing import Any, AsyncIterator, Optional

from llama_index.core.llms.llm import LLM
from llama_index.core.query_engine import CustomQueryEngine

from .config import settings
from .graph_store import GraphRAGStore

logger = logging.getLogger(__name__)

_NO_INFO_MARKER = "<<NO_RELEVANT_INFO>>"

_STOPWORDS = frozenset({
    "the","a","an","is","are","was","were","be","been","being","have","has","had",
    "do","does","did","will","would","could","should","may","might","shall","must",
    "of","in","on","at","to","for","with","by","from","up","about","into","than",
    "what","how","why","when","where","who","which","can","tell","me","you","i",
    "and","or","but","not","this","that","these","those","it","its","as","if","so",
    "my","your","we","our","they","them","their","he","she","his","her","any","all",
    "more","also","just","get","use","used","using","give","make","know","like",
})


class GraphRAGQueryEngine(CustomQueryEngine):
    """
    Queries all community summaries and synthesises a single answer.

    graph_store:    the loaded GraphRAGStore containing community_summaries
    llm:            stronger model (e.g. gpt-4o) used for final synthesis
    community_llm:  cheaper model (e.g. gpt-4o-mini) for per-community relevance check
    """

    graph_store: GraphRAGStore
    llm: LLM
    community_llm: LLM
    max_workers: int = 4
    community_timeout: float = 120.0
    max_communities: int = 15
    # Path used to cache community embeddings; main.py sets it when constructing
    # the engine for a topic. None means "no cache, embeddings disabled for this topic".
    embedding_cache_path: Optional[Any] = None

    def custom_query(self, query_str: str, mode: str = "graph") -> tuple[str, int, int, list]:
        """
        Returns (answer, communities_checked, relevant_communities, sources).
        sources is a list of (community_id, summary) for communities that contributed.
        mode: "graph" = strictly graph-grounded; "extended" = graph + LLM training knowledge.
        """
        summaries = self.graph_store.get_community_summaries()

        if not summaries:
            return (
                "No community summaries found. Please build the graph first.",
                0, 0, [],
            )

        candidates = self._select_candidates(summaries, query_str)
        communities_checked = len(candidates)
        logger.info("Query '%s': %d/%d communities selected for LLM check",
                    query_str[:60], communities_checked, len(summaries))

        relevant = self._run_community_phase(candidates, query_str)
        relevant_communities = len(relevant)

        if not relevant:
            if mode == "extended":
                answer = self._aggregate_extended([], query_str)
                return answer, communities_checked, 0, []
            return (
                "I don't have enough information in the knowledge graph to answer that question.",
                communities_checked, 0, [],
            )

        relevant_answers = [a for _, _, a in relevant]
        sources = [(cid, s) for cid, s, _ in relevant]
        answer = self._aggregate(relevant_answers, query_str, mode=mode)
        return answer, communities_checked, relevant_communities, sources

    def _run_community_phase(self, candidates: dict, query_str: str) -> list[tuple]:
        """
        Phase 1: fan out community-relevance checks in a thread pool.
        Returns the list of (community_id, summary, answer_text) for communities
        whose answer was non-empty (i.e. actually relevant).
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(self._answer_from_community, summary, query_str): (cid, summary)
                for cid, summary in candidates.items()
            }
            community_answers: list[tuple] = []
            try:
                for future in as_completed(futures, timeout=self.community_timeout):
                    cid, summary = futures[future]
                    try:
                        answer_text = future.result()
                        community_answers.append((cid, summary, answer_text))
                    except Exception as exc:
                        logger.error("Community future error: %s", exc)
            except TimeoutError:
                logger.warning("Community phase timed out after %.0fs — using %d answers so far",
                               self.community_timeout, len(community_answers))

        return [(cid, s, a) for cid, s, a in community_answers if a.strip()]

    async def astream_query(
        self, query_str: str, mode: str = "graph"
    ) -> AsyncIterator[dict]:
        """
        Async-stream variant of custom_query.
        Yields dicts with a 'type' field:
          - 'status'  : Phase 1 progress message (shown as placeholder)
          - 'meta'    : {communities_checked, relevant_communities, sources}
          - 'token'   : {text} — an answer delta
          - 'done'    : signals end-of-stream
          - 'error'   : {message}
        Meta is emitted *before* the first token so the UI can show sources early.
        """
        summaries = self.graph_store.get_community_summaries()
        if not summaries:
            yield {"type": "meta", "communities_checked": 0, "relevant_communities": 0, "sources": []}
            yield {"type": "token", "text": "No community summaries found. Please build the graph first."}
            yield {"type": "done"}
            return

        candidates = self._select_candidates(summaries, query_str)
        communities_checked = len(candidates)
        logger.info("Stream query '%s': %d/%d communities selected for LLM check",
                    query_str[:60], communities_checked, len(summaries))

        yield {"type": "status", "message": f"Checking {communities_checked} communities..."}

        # Phase 1 is sync + thread-pool-based; run it off the event loop.
        relevant = await asyncio.to_thread(self._run_community_phase, candidates, query_str)
        relevant_communities = len(relevant)
        sources = [{"id": str(cid), "summary": s} for cid, s, _ in relevant]

        yield {
            "type": "meta",
            "communities_checked": communities_checked,
            "relevant_communities": relevant_communities,
            "sources": sources,
        }

        if not relevant:
            if mode == "extended":
                async for delta in self._astream_from_prompt(
                    self._build_extended_prompt(query_str)
                ):
                    yield {"type": "token", "text": delta}
            else:
                yield {"type": "token",
                       "text": "I don't have enough information in the knowledge graph to answer that question."}
            yield {"type": "done"}
            return

        prompt = self._build_aggregate_prompt(
            [a for _, _, a in relevant], query_str, mode=mode
        )
        streamed_parts: list[str] = []
        async for delta in self._astream_from_prompt(prompt):
            streamed_parts.append(delta)
            yield {"type": "token", "text": delta}
        # In graph-only mode, run the citation post-filter and emit a replacement
        # if the cleaned text differs from what was streamed.
        if mode == "graph":
            raw = "".join(streamed_parts)
            cleaned = self._enforce_citations(raw, mode)
            if cleaned != raw.strip():
                yield {"type": "replace", "text": cleaned}
        yield {"type": "done"}

    def _extract_keywords(self, query: str) -> set[str]:
        words = re.findall(r"[a-zA-Z]{3,}", query.lower())
        return {w for w in words if w not in _STOPWORDS}

    def _score_summary(self, summary: str, keywords: set[str]) -> int:
        """Count how many query keywords appear in the summary."""
        low = summary.lower()
        return sum(1 for kw in keywords if kw in low)

    def _select_candidates(self, summaries: dict, query: str) -> dict:
        """
        Return at most max_communities summaries, ranked by keyword overlap.

        Scoring combines:
          - keyword hits against the community summary text
          - keyword hits against entity names / descriptions in communities
            that contain matching entities (from entity_index — makes sure a
            community is considered even if its summary doesn't mention the
            matched entity by name).
          - cosine similarity between query and community summary embeddings
            when EMBEDDINGS_ENABLED=true (most useful past ~200 communities,
            where keyword overlap alone misses semantic matches).
        """
        keywords = self._extract_keywords(query)

        # Embedding-based scoring (opt-in). Returns {cid: cosine_similarity}.
        embed_scores = self._embedding_scores(summaries, query)

        # Bonus scoring from the entity index: for every community, count how
        # many entities in it match a query keyword (on name or description).
        index_bonus: dict[str, int] = {}
        try:
            idx = getattr(self.graph_store, "entity_index", None) or {}
            entities = idx.get("entities", {})
            by_community = idx.get("by_community", {})
            if keywords and entities and by_community:
                for cid, node_ids in by_community.items():
                    score = 0
                    for nid in node_ids:
                        ent = entities.get(nid)
                        if not ent:
                            continue
                        hay = (ent.get("name", "") + " " + ent.get("description", "")).lower()
                        score += sum(1 for kw in keywords if kw in hay)
                    if score:
                        index_bonus[str(cid)] = score
        except Exception as exc:
            logger.debug("Index-based scoring skipped: %s", exc)

        if keywords or embed_scores:
            scored = []
            for cid, summary in summaries.items():
                summary_score = self._score_summary(summary, keywords) if keywords else 0
                index_score = index_bonus.get(str(cid), 0)
                # Cosine ∈ roughly [0, 1] for related text; scale up so it's on
                # the same order of magnitude as integer keyword counts.
                embed_score = embed_scores.get(str(cid), 0.0) * 10.0
                total = summary_score + index_score + embed_score
                scored.append((cid, summary, total))
            # Keep only communities with any match signal
            scored = [(cid, s, sc) for cid, s, sc in scored if sc > 0]
            if not scored:
                # No match anywhere — fall back to top-N by original order
                scored = [(cid, s, 0) for cid, s in list(summaries.items())[:self.max_communities]]
            scored.sort(key=lambda x: x[2], reverse=True)
            scored = scored[:self.max_communities]
        else:
            scored = [(cid, s, 0) for cid, s in list(summaries.items())[:self.max_communities]]

        return {cid: summary for cid, summary, _ in scored}

    # Lazily-instantiated per-engine; created on first query if embeddings
    # are enabled and a cache path was supplied.
    _embedding_index = None

    def _embedding_scores(self, summaries: dict, query: str) -> dict[str, float]:
        """
        Return {community_id_str: cosine_similarity}. Empty dict when embeddings
        are disabled, the model can't be loaded, or no cache path was set.
        """
        if not getattr(settings, "embeddings_enabled", False):
            return {}
        if not self.embedding_cache_path:
            return {}
        try:
            from .embeddings import CommunityEmbeddingIndex
            if self._embedding_index is None:
                self._embedding_index = CommunityEmbeddingIndex(
                    cache_path=self.embedding_cache_path,
                    model_id=settings.embedding_model,
                )
            self._embedding_index.sync(summaries)
            self._embedding_index.flush()
            ranked = self._embedding_index.rank(query)
            return {cid: sim for cid, sim in ranked}
        except Exception as exc:
            logger.warning("Embedding-based ranking skipped: %s", exc)
            return {}

    def _answer_from_community(self, summary: str, query: str) -> str:
        prompt = (
            f"Community summary:\n{summary}\n\n"
            f"Question: {query}\n\n"
            f"If this summary contains information relevant to the question, answer it based only on "
            f"the summary. If not relevant, reply exactly: '{_NO_INFO_MARKER}'\n\n"
            f"Answer:"
        )
        try:
            response = self.community_llm.complete(prompt)
            text = response.text.strip()
            if "</think>" in text:
                text = text.split("</think>")[-1].strip()
            return "" if _NO_INFO_MARKER in text else text
        except Exception as exc:
            logger.error("Community answer error: %s", exc)
            return ""

    def _build_aggregate_prompt(self, answers: list[str], query: str, mode: str = "graph") -> str:
        combined = "\n\n---\n\n".join(answers)
        citation_rule = (
            "Citation format: whenever you mention a specific entity from the Graph index, "
            "wrap its name in double brackets exactly as shown, e.g. [[Marketing Mix Modeling]]. "
            "Every factual claim should cite at least one entity this way."
        )
        if mode == "extended":
            grounding = (
                "You may also draw on your own knowledge to fill gaps or add context. "
                "Structure your answer in two clearly labelled sections:\n"
                "1. Start with '**From the knowledge graph:**' and write what the graph evidence covers. "
                "Cite entities in that section.\n"
                "2. Then add '**From AI knowledge:**' and write only what you are adding beyond the graph — "
                "skip this section entirely if the graph already covers the question fully."
            )
        else:
            grounding = (
                "Base your answer STRICTLY on the community evidence provided. "
                "Do NOT add information from your training data, prior knowledge, or general reasoning. "
                "If the evidence does not cover the question, reply with exactly: "
                "'Not in the graph.' followed by one short sentence describing what is missing. "
                "Do not guess, speculate, or fill gaps — the user prefers an honest 'not in the graph' "
                "over a plausible but unsupported answer."
            )

        # Inject a compact index so the LLM knows what entities are in scope.
        # Falls back to an empty string for graphs built before the index feature.
        index_block = ""
        try:
            digest = self.graph_store.index_digest(max_entities=120) if self.graph_store.entity_index else ""
            if digest:
                index_block = (
                    f"Graph index (for reference — entities you may cite):\n{digest}\n\n"
                )
        except Exception as exc:  # never let index issues break the query
            logger.warning("Index digest failed: %s", exc)

        return (
            f"You have received answers from multiple knowledge graph communities about this question:\n\n"
            f"Question: {query}\n\n"
            f"{index_block}"
            f"Community answers:\n{combined}\n\n"
            f"Synthesise these into a single, clear, well-structured final answer. "
            f"Remove redundancy, keep all important details, and ensure the answer "
            f"directly addresses the question.\n\n"
            f"{citation_rule}\n\n"
            f"{grounding}\n\n"
            f"Final Answer:"
        )

    def _build_extended_prompt(self, query: str) -> str:
        return (
            f"The knowledge graph does not contain relevant information for this question.\n\n"
            f"Question: {query}\n\n"
            f"Answer using your own knowledge. Be clear and concise.\n\nAnswer:"
        )

    def _aggregate(self, answers: list[str], query: str, mode: str = "graph") -> str:
        prompt = self._build_aggregate_prompt(answers, query, mode=mode)
        try:
            raw = self.llm.complete(prompt).text
        except Exception as exc:
            logger.error("Aggregation error: %s", exc)
            return "\n\n".join(answers)
        return self._enforce_citations(raw, mode)

    # Pattern matches [[Anything reasonable]] — entity names with spaces/dashes are fine.
    _CITE_PATTERN = re.compile(r"\[\[([^\[\]\n]{1,80})\]\]")

    def _enforce_citations(self, text: str, mode: str) -> str:
        """
        In graph-only mode, drop sentences that make claims without citing any graph
        entity. Structural lines (headers, bullets, short connectors) are preserved.
        Extended mode keeps everything — citation is a hint there, not a rule.
        """
        if mode != "graph" or not text:
            return text

        # Split into line-level units; process each line so markdown structure survives.
        out_lines: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()

            # Preserve structural / short / non-claim lines as-is.
            if (
                not stripped
                or stripped.startswith(("#", "-", "*", ">", "|", "```"))
                or stripped.endswith(":")
                or len(stripped) < 50
                or "not in the graph" in stripped.lower()
            ):
                out_lines.append(line)
                continue

            # For claim-looking lines, split into sentences and keep only cited ones.
            sentences = re.split(r"(?<=[.!?])\s+", stripped)
            kept = [s for s in sentences if self._CITE_PATTERN.search(s)]
            if kept:
                # Preserve leading indentation/bullet prefix from the original line.
                lead = line[: len(line) - len(line.lstrip())]
                out_lines.append(lead + " ".join(kept))

        cleaned = "\n".join(out_lines).strip()
        if not cleaned:
            return (
                "Not in the graph. The LLM could not produce a citation-backed answer "
                "from the community evidence."
            )
        return cleaned

    def _aggregate_extended(self, answers: list[str], query: str) -> str:
        """Used when graph has no relevant communities but mode=extended."""
        prompt = self._build_extended_prompt(query)
        try:
            return self.llm.complete(prompt).text
        except Exception as exc:
            logger.error("Extended aggregation error: %s", exc)
            return "I could not find relevant information to answer this question."

    async def _astream_from_prompt(self, prompt: str) -> AsyncIterator[str]:
        """
        Call astream_complete and yield token deltas.
        Handles both delta-style chunks and cumulative-text chunks (different
        LlamaIndex backends emit one or the other). Falls back to a single
        non-streaming complete call if astream_complete is unavailable.
        """
        try:
            response_gen = await self.llm.astream_complete(prompt)
        except AttributeError:
            try:
                response = await self.llm.acomplete(prompt)
                text = response.text or ""
                if "</think>" in text:
                    text = text.split("</think>")[-1].lstrip()
                yield text
            except Exception as exc:
                logger.error("Non-streaming fallback failed: %s", exc)
                yield "I couldn't synthesise an answer — the model call failed."
            return
        except Exception as exc:
            logger.error("Stream setup failed: %s", exc)
            yield "I couldn't synthesise an answer — the model call failed."
            return

        prev = ""           # cumulative text, for delta derivation
        pending = ""        # buffer while we're still inside a <think>…</think>
        thinking_done = False
        try:
            async for chunk in response_gen:
                # Chunks carry either .delta (incremental) or cumulative .text.
                delta = getattr(chunk, "delta", None)
                if not delta:
                    cur = getattr(chunk, "text", "") or ""
                    delta = cur[len(prev):] if cur.startswith(prev) else cur
                    prev = cur
                else:
                    prev += delta
                if not delta:
                    continue

                if thinking_done:
                    yield delta
                    continue

                # Still possibly inside a <think> block. Hold tokens until we
                # see </think>, then yield everything after it. If we don't
                # see <think> in the first ~200 chars, flush and stop buffering.
                pending += delta
                if "</think>" in pending:
                    tail = pending.split("</think>", 1)[1].lstrip()
                    thinking_done = True
                    pending = ""
                    if tail:
                        yield tail
                elif "<think>" not in pending and len(pending) > 200:
                    thinking_done = True
                    out, pending = pending, ""
                    yield out
        except Exception as exc:
            logger.error("Streaming aggregation error: %s", exc)
            yield "\n\n_[stream interrupted]_"

        # If we ended while still buffering (no think tags, short answer),
        # flush what we have.
        if not thinking_done and pending:
            yield pending
