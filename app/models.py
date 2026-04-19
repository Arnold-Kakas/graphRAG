from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Ontology ───────────────────────────────────────────────────────────────────

class OntologyConfig(BaseModel):
    """Per-topic ontology. Defaults to a generic schema suitable for any domain."""

    entity_types: list[str] = Field(
        default=[
            "PERSON",
            "ORGANIZATION",
            "CONCEPT",
            "EVENT",
            "LOCATION",
            "DOCUMENT",
            "TECHNOLOGY",
            "PRODUCT",
        ]
    )
    relation_types: list[str] = Field(
        default=[
            "RELATED_TO",
            "PART_OF",
            "CREATED_BY",
            "LOCATED_IN",
            "REFERENCES",
            "OPPOSES",
            "SUPPORTS",
            "REGULATES",
        ]
    )
    aliases: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Explicit merge map: {alias: canonical}. "
            "Any node whose name matches an alias key is merged into the canonical node. "
            "Use this for rebrands, abbreviations, or known synonyms that the LLM may emit. "
            "Example: {\"Facebook\": \"Meta\", \"FB\": \"Meta\"}"
        ),
    )


# ── Extraction models (used by pipeline + LLM structured predict) ──────────────

class ExtractedEntity(BaseModel):
    name: str = Field(description="Name of the entity, capitalized")
    type: str = Field(description="One of the allowed entity types")
    description: str = Field(description="Brief description of the entity and its role")


class ExtractedRelationship(BaseModel):
    source: str = Field(description="Name of the source entity")
    target: str = Field(description="Name of the target entity")
    relation: str = Field(description="One of the allowed relationship types")
    description: str = Field(description="Sentence explaining the relationship")


class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[ExtractedRelationship] = Field(default_factory=list)


# ── LLM provider config (per-request, never persisted on disk) ────────────────

class LLMConfig(BaseModel):
    """
    LLM provider settings passed from the browser session with every request.
    The API key lives only in sessionStorage — it is never saved to disk.
    """

    provider: str = "openai"  # openai | lmstudio | ollama | custom
    api_key: Optional[str] = None  # for OpenAI; empty for local providers
    base_url: Optional[str] = None  # auto-set for known providers, or custom URL
    extraction_model: str = "gpt-4o-mini"
    query_model: str = "gpt-4o"
    max_tokens: Optional[int] = None  # overrides server LLM_MAX_TOKENS if set


# ── API request / response models ─────────────────────────────────────────────

class BuildRequest(BaseModel):
    ontology: Optional[OntologyConfig] = None
    llm: Optional[LLMConfig] = None
    force: bool = False
    thinking: bool = False
    build_context: Optional[str] = None


class QueryRequest(BaseModel):
    query: str
    llm: Optional[LLMConfig] = None
    mode: str = "graph"  # "graph" | "extended" (graph + LLM knowledge)


class SourceCommunity(BaseModel):
    id: str
    summary: str


class QueryResponse(BaseModel):
    answer: str
    communities_checked: int
    relevant_communities: int
    sources: list[SourceCommunity] = []


class TopicStatus(BaseModel):
    topic: str
    has_raw_files: bool
    has_graph: bool
    node_count: Optional[int] = None
    edge_count: Optional[int] = None
    community_count: Optional[int] = None
    build_status: str = "idle"   # idle | building | complete | error
    build_progress: Optional[str] = None
    build_error: Optional[str] = None
    docs_processed: Optional[int] = None
    docs_total: Optional[int] = None
    nodes_extracted: Optional[int] = None
    edges_extracted: Optional[int] = None


# ── Internal task state ────────────────────────────────────────────────────────

class TaskState(BaseModel):
    topic: str
    status: str = "building"   # building | complete | error
    progress: str = "Starting..."
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    up_to_date: bool = False    # True when build skipped because no files changed
    docs_processed: int = 0
    docs_total: int = 0
    nodes_extracted: int = 0
    edges_extracted: int = 0
