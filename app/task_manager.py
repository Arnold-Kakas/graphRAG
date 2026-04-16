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

from .config import Settings
from .graph_store import GraphRAGStore
from .models import LLMConfig, OntologyConfig, TaskState
from .parser import DocumentParser
from .pipeline import build_topic_graph

logger = logging.getLogger(__name__)

# Known provider base URLs
_PROVIDER_URLS = {
    "lmstudio": "http://localhost:1234/v1",
    "ollama": "http://localhost:11434/v1",
}


def make_llm(model: str, llm_config: Optional[LLMConfig] = None, fallback: Optional[Settings] = None):
    """
    Create an LLM client from a per-request LLMConfig (preferred) or server-level Settings (fallback).

    Never persists the API key — it's only used for this single client instance.
    """
    kwargs = {"model": model, "temperature": 0}

    if llm_config:
        # Per-request config from the browser session
        if llm_config.api_key:
            kwargs["api_key"] = llm_config.api_key
        base_url = llm_config.base_url or _PROVIDER_URLS.get(llm_config.provider)
        if base_url:
            kwargs["api_base"] = base_url
        # Local providers may not need a real key
        if llm_config.provider != "openai" and "api_key" not in kwargs:
            kwargs["api_key"] = "not-needed"
    elif fallback:
        # Server-level .env config (for headless / CLI usage)
        if fallback.openai_api_key:
            kwargs["api_key"] = fallback.openai_api_key
        if fallback.llm_base_url:
            kwargs["api_base"] = fallback.llm_base_url

    return OpenAI(**kwargs)


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
    ) -> None:
        """
        Launch a background build task for the given topic.
        If a build is already running, raises RuntimeError.
        """
        existing = self._tasks.get(topic)
        if existing and existing.status == "building":
            raise RuntimeError(f"Build already in progress for topic '{topic}'")

        self._tasks[topic] = TaskState(topic=topic, status="building", progress="Starting...")
        self.invalidate_store(topic)
        query_engines.pop(topic, None)

        asyncio.create_task(
            self._run_build(topic, ontology or OntologyConfig(), llm_config, query_engines)
        )

    # ── Internal ───────────────────────────────────────────────────────────────

    async def _run_build(
        self,
        topic: str,
        ontology: OntologyConfig,
        llm_config: Optional[LLMConfig],
        query_engines: dict,
    ) -> None:
        def _progress(msg: str) -> None:
            if topic in self._tasks:
                self._tasks[topic].progress = msg

        try:
            config = self.config
            parser = DocumentParser(config.raw_dir)

            _progress("Parsing documents...")
            documents = await asyncio.get_event_loop().run_in_executor(
                None, parser.parse_topic, topic
            )

            if not documents:
                raise ValueError(f"No parseable documents found in raw/{topic}/")

            _progress(f"Parsed {len(documents)} documents — building graph...")

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
            )

            self._stores[topic] = store
            self._tasks[topic].status = "complete"
            self._tasks[topic].progress = "Build complete"
            self._tasks[topic].completed_at = datetime.now(timezone.utc)
            logger.info("Build complete for topic '%s'", topic)

        except Exception as exc:
            logger.exception("Build failed for topic '%s': %s", topic, exc)
            if topic in self._tasks:
                self._tasks[topic].status = "error"
                self._tasks[topic].error = str(exc)
                self._tasks[topic].completed_at = datetime.now(timezone.utc)
