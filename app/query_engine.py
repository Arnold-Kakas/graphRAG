"""
GraphRAGQueryEngine — two-phase community-based query answering.

Phase 1: Ask the cheaper LLM whether each community summary is relevant.
Phase 2: Aggregate relevant partial answers with the stronger LLM.
"""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed

from llama_index.core.llms.llm import LLM
from llama_index.core.query_engine import CustomQueryEngine

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

        # Pre-filter by keyword overlap, then cap to max_communities
        candidates = self._select_candidates(summaries, query_str)
        communities_checked = len(candidates)
        logger.info("Query '%s': %d/%d communities selected for LLM check",
                    query_str[:60], communities_checked, len(summaries))

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(self._answer_from_community, summary, query_str): (cid, summary)
                for cid, summary in candidates.items()
            }
            community_answers = []  # list of (cid, summary, answer_text)
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

        relevant = [(cid, s, a) for cid, s, a in community_answers if a.strip()]
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
        If no keywords can be extracted (very short query), return all summaries
        up to the cap ordered by original key.
        """
        keywords = self._extract_keywords(query)

        if keywords:
            scored = [
                (cid, summary, self._score_summary(summary, keywords))
                for cid, summary in summaries.items()
            ]
            # Keep only summaries with at least one keyword match
            scored = [(cid, s, sc) for cid, s, sc in scored if sc > 0]
            if not scored:
                # No keyword overlap at all — fall back to top-N by original order
                scored = [(cid, s, 0) for cid, s in list(summaries.items())[:self.max_communities]]
            # Sort by score descending, take top N
            scored.sort(key=lambda x: x[2], reverse=True)
            scored = scored[:self.max_communities]
        else:
            scored = [(cid, s, 0) for cid, s in list(summaries.items())[:self.max_communities]]

        return {cid: summary for cid, summary, _ in scored}

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

    def _aggregate(self, answers: list[str], query: str, mode: str = "graph") -> str:
        combined = "\n\n---\n\n".join(answers)
        if mode == "extended":
            grounding = (
                "You may also draw on your own knowledge to fill gaps, add context, "
                "or clarify concepts — but clearly prioritise the graph evidence above."
            )
        else:
            grounding = (
                "Base your answer strictly on the community evidence provided. "
                "Do not add information from outside these summaries."
            )
        prompt = (
            f"You have received answers from multiple knowledge graph communities about this question:\n\n"
            f"Question: {query}\n\n"
            f"Community answers:\n{combined}\n\n"
            f"Synthesise these into a single, clear, well-structured final answer. "
            f"Remove redundancy, keep all important details, and ensure the answer "
            f"directly addresses the question. {grounding}\n\n"
            f"Final Answer:"
        )
        try:
            return self.llm.complete(prompt).text
        except Exception as exc:
            logger.error("Aggregation error: %s", exc)
            return "\n\n".join(answers)

    def _aggregate_extended(self, answers: list[str], query: str) -> str:
        """Used when graph has no relevant communities but mode=extended."""
        prompt = (
            f"The knowledge graph does not contain relevant information for this question.\n\n"
            f"Question: {query}\n\n"
            f"Answer using your own knowledge. Be clear and concise.\n\nAnswer:"
        )
        try:
            return self.llm.complete(prompt).text
        except Exception as exc:
            logger.error("Extended aggregation error: %s", exc)
            return "I could not find relevant information to answer this question."
