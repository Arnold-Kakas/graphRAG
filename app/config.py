from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── LLM Provider ────────────────────────────────────────────────────────────
    # Supports OpenAI and any OpenAI-compatible API (LM Studio, Ollama, etc.)
    openai_api_key: str = ""

    # Set this to use a local/custom endpoint, e.g.:
    #   LLM_BASE_URL=http://localhost:1234/v1   (LM Studio)
    #   LLM_BASE_URL=http://localhost:11434/v1  (Ollama with OpenAI compat)
    llm_base_url: Optional[str] = None

    extraction_model: str = "gpt-4o-mini"
    query_model: str = "gpt-4o"

    # ── Data directories ────────────────────────────────────────────────────────
    raw_dir: Path = Path("./raw")
    graphs_dir: Path = Path("./graphs")

    # ── LLM context window (required for non-OpenAI models) ─────────────────────
    llm_context_window: int = 81920

    # ── LLM request timeout in seconds (increase for slow local models) ─────────
    llm_request_timeout: float = 300.0

    # ── Max tokens for LLM responses (increase for longer wiki articles / answers)
    llm_max_tokens: int = 16384

    # ── Pipeline parameters ─────────────────────────────────────────────────────
    max_paths_per_chunk: int = 20
    num_workers: int = 4
    max_cluster_size: int = 10
    max_documents: int = 50

    # ── Embeddings-based community pre-filter (opt-in) ──────────────────────────
    # On graphs with hundreds of communities, keyword overlap starts missing
    # semantically related communities (synonyms, paraphrases). When enabled,
    # the query engine ranks communities by cosine similarity between the query
    # and each community summary embedding. Embeddings are cached on disk per
    # community summary so subsequent queries pay only the query-encoding cost.
    embeddings_enabled: bool = False
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"


settings = Settings()
