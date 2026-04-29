"""
Async build task manager — tracks in-progress and completed graph builds.

Build tasks are expensive (minutes). This module launches each build as an
asyncio background task and exposes its status for the API polling endpoint.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from llama_index.llms.openai import OpenAI
from llama_index.llms.openai_like import OpenAILike

try:
    from llama_index.llms.anthropic import Anthropic as AnthropicLLM
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False

from .config import Settings
from .graph_store import GraphRAGStore
from .models import LLMConfig, OntologyConfig, TaskState
from .parser import DocumentParser
from .pipeline import build_topic_graph, merge_topic_entities

logger = logging.getLogger(__name__)

# Known provider base URLs (Gemini uses OpenAI-compatible endpoint)
_PROVIDER_URLS = {
    "lmstudio": "http://localhost:1234/v1",
    "ollama":   "http://localhost:11434/v1",
    "gemini":   "https://generativelanguage.googleapis.com/v1beta/openai/",
}


def make_llm(model: str, llm_config: Optional[LLMConfig] = None, fallback: Optional[Settings] = None):
    """
    Create an LLM client from a per-request LLMConfig (preferred) or server-level Settings (fallback).

    Uses OpenAILike for non-OpenAI providers (bypasses model name validation).
    Never persists the API key — it's only used for this single client instance.
    """
    # Resolve max_tokens: per-request config > server .env default
    max_tokens = (
        (llm_config.max_tokens if llm_config and llm_config.max_tokens else None)
        or (fallback.llm_max_tokens if fallback else 4096)
    )

    if llm_config:
        provider = llm_config.provider or "openai"

        # Anthropic (Claude)
        if provider == "anthropic":
            if not _ANTHROPIC_AVAILABLE:
                raise RuntimeError(
                    "llama-index-llms-anthropic is not installed. "
                    "Add it to requirements.txt and rebuild the Docker image."
                )
            kwargs: dict = {"model": model, "max_tokens": max_tokens}
            if llm_config.api_key:
                kwargs["api_key"] = llm_config.api_key
            return AnthropicLLM(**kwargs)

        base_url = llm_config.base_url or (fallback.llm_base_url if fallback else None) or _PROVIDER_URLS.get(provider)
        if provider != "openai" and base_url:
            return OpenAILike(
                model=model,
                api_base=base_url,
                api_key=llm_config.api_key or "not-needed",
                is_chat_model=True,
                is_function_calling_model=True,
                context_window=fallback.llm_context_window if fallback else 8192,
                temperature=0,
                timeout=fallback.llm_request_timeout if fallback else 300.0,
                max_tokens=max_tokens,
            )
        # OpenAI provider — honour api_base when the user points at a proxy
        # (e.g. LiteLLM, Azure OpenAI-compatible gateway). Without this,
        # setting base_url in the UI silently falls back to api.openai.com.
        kwargs: dict = {"model": model, "temperature": 0, "max_tokens": max_tokens}
        if llm_config.api_key:
            kwargs["api_key"] = llm_config.api_key
        if base_url:
            kwargs["api_base"] = base_url
        return OpenAI(**kwargs)

    elif fallback:
        if fallback.llm_base_url:
            logger.info("Using OpenAILike with base_url=%s model=%s", fallback.llm_base_url, model)
            return OpenAILike(
                model=model,
                api_base=fallback.llm_base_url,
                api_key=fallback.openai_api_key or "not-needed",
                is_chat_model=True,
                is_function_calling_model=True,
                context_window=fallback.llm_context_window,
                temperature=0,
                timeout=fallback.llm_request_timeout,
                max_tokens=max_tokens,
            )
        # Standard OpenAI via .env
        kwargs = {"model": model, "temperature": 0, "max_tokens": max_tokens}
        if fallback.openai_api_key:
            kwargs["api_key"] = fallback.openai_api_key
        return OpenAI(**kwargs)

    return OpenAI(model=model, temperature=0, max_tokens=max_tokens)


class TaskManager:
    def __init__(self, config: Settings):
        self.config = config
        self._tasks: dict[str, TaskState] = {}
        self._stores: dict[str, GraphRAGStore] = {}  # built store cache

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_status(self, topic: str) -> Optional[TaskState]:
        return self._tasks.get(topic)

    def get_store(self, topic: str) -> Optional[GraphRAGStore]:
        return self._stores.get(topic)

    def invalidate_store(self, topic: str) -> None:
        self._stores.pop(topic, None)

    async def start_build(
        self,
        topic: str,
        ontology: Optional[OntologyConfig],
        llm_config: Optional[LLMConfig],
        query_engines: dict,
        force: bool = False,
        thinking: bool = False,
        build_context: Optional[str] = None,
    ) -> None:
        """
        Launch a background build task for the given topic.
        If a build is already running, raises RuntimeError.
        Pass force=True to ignore the incremental manifest and rebuild from scratch.
        """
        existing = self._tasks.get(topic)
        if existing and existing.status == "building":
            raise RuntimeError(f"Build already in progress for topic '{topic}'")

        self._tasks[topic] = TaskState(topic=topic, status="building", progress="Starting...")
        self.invalidate_store(topic)
        query_engines.pop(topic, None)

        asyncio.create_task(
            self._run_build(topic, ontology or OntologyConfig(), llm_config, query_engines, force, thinking, build_context)
        )

    # ── Internal ───────────────────────────────────────────────────────────────

    async def _run_build(
        self,
        topic: str,
        ontology: OntologyConfig,
        llm_config: Optional[LLMConfig],
        query_engines: dict,
        force: bool = False,
        thinking: bool = False,
        build_context: Optional[str] = None,
    ) -> None:
        def _progress(msg: str) -> None:
            if topic in self._tasks:
                self._tasks[topic].progress = msg

        def _stats_update(docs: int, total: int, nodes: int, edges: int) -> None:
            if topic in self._tasks:
                task = self._tasks[topic]
                task.docs_processed = docs
                task.docs_total = total
                task.nodes_extracted = nodes
                task.edges_extracted = edges
                if docs >= total:
                    task.progress = "Extraction complete — building graph index..."
                else:
                    task.progress = f"Extracting · {docs}/{total} docs"

        try:
            config = self.config
            parser = DocumentParser(config.raw_dir)

            _progress("Parsing documents...")
            documents = await asyncio.get_event_loop().run_in_executor(
                None, parser.parse_topic, topic
            )

            if not documents:
                raise ValueError(f"No parseable documents found in raw/{topic}/")

            _progress(f"Parsed {len(documents)} document(s) — checking for changes...")

            # Resolve model names: per-request config overrides server defaults
            extraction_model = (llm_config.extraction_model if llm_config else None) or config.extraction_model
            query_model = (llm_config.query_model if llm_config else None) or config.query_model

            extraction_llm = make_llm(extraction_model, llm_config, config)
            community_llm = extraction_llm

            store = await build_topic_graph(
                topic=topic,
                documents=documents,
                ontology=ontology,
                config=config,
                extraction_llm=extraction_llm,
                community_llm=community_llm,
                progress_callback=_progress,
                stats_callback=_stats_update,
                force=force,
                thinking=thinking,
                build_context=build_context,
            )

            self._stores[topic] = store
            up_to_date = "already up to date" in self._tasks[topic].progress.lower()
            self._tasks[topic].status = "complete"
            self._tasks[topic].progress = "No changes detected — graph is up to date" if up_to_date else "Build complete"
            self._tasks[topic].up_to_date = up_to_date
            self._tasks[topic].completed_at = datetime.now(timezone.utc)
            logger.info("Build complete for topic '%s'", topic)

        except Exception as exc:
            logger.exception("Build failed for topic '%s': %s", topic, exc)
            if topic in self._tasks:
                self._tasks[topic].status = "error"
                self._tasks[topic].error = str(exc)
                self._tasks[topic].completed_at = datetime.now(timezone.utc)

    async def start_merge(
        self,
        topic: str,
        llm_config: Optional[LLMConfig],
        query_engines: dict,
        thinking: bool = False,
    ) -> None:
        """Launch a background merge task. Raises RuntimeError if a task is already running."""
        existing = self._tasks.get(topic)
        if existing and existing.status == "building":
            raise RuntimeError(f"A task is already in progress for topic '{topic}'")

        self._tasks[topic] = TaskState(topic=topic, status="building", progress="Starting merge...")
        self.invalidate_store(topic)
        query_engines.pop(topic, None)

        asyncio.create_task(self._run_merge(topic, llm_config, query_engines, thinking))

    async def _run_merge(
        self,
        topic: str,
        llm_config: Optional[LLMConfig],
        query_engines: dict,
        thinking: bool = False,
    ) -> None:
        def _progress(msg: str) -> None:
            if topic in self._tasks:
                self._tasks[topic].progress = msg

        try:
            config = self.config
            extraction_model = (llm_config.extraction_model if llm_config else None) or config.extraction_model
            llm = make_llm(extraction_model, llm_config, config)

            await merge_topic_entities(
                topic=topic,
                llm=llm,
                config=config,
                thinking=thinking,
                progress_callback=_progress,
            )

            self._tasks[topic].status = "complete"
            self._tasks[topic].progress = "Merge complete"
            self._tasks[topic].completed_at = datetime.now(timezone.utc)
            logger.info("Merge complete for topic '%s'", topic)

        except Exception as exc:
            logger.exception("Merge failed for topic '%s': %s", topic, exc)
            if topic in self._tasks:
                self._tasks[topic].status = "error"
                self._tasks[topic].error = str(exc)
                self._tasks[topic].completed_at = datetime.now(timezone.utc)
