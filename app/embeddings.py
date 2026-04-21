"""
Optional sentence-embeddings pre-filter for community selection.

Activated by `EMBEDDINGS_ENABLED=true` in `.env`. On graphs past ~200
communities, keyword overlap starts missing semantically related communities
(synonyms, paraphrases). Cosine similarity between a query embedding and a
cached per-community embedding fixes that without changing the rest of the
pipeline — community summaries still drive the LLM relevance check.

Cache layout: `graphs/<topic>/community_embeddings.json`
    {
      "model": "<embedding model id>",
      "dim": 384,
      "items": {"<community_id>": {"hash": "<sha1 of summary>", "vec": [...]}}
    }
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-loaded singleton — sentence-transformers / torch are heavy imports.
_model_cache: dict[str, object] = {}


def _summary_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def get_model(model_id: str):
    """Load and cache a SentenceTransformer model. Returns None on failure."""
    if model_id in _model_cache:
        return _model_cache[model_id]
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.warning(
            "embeddings_enabled=true but sentence-transformers is not installed. "
            "Run `pip install sentence-transformers` or set EMBEDDINGS_ENABLED=false."
        )
        _model_cache[model_id] = None
        return None
    try:
        model = SentenceTransformer(model_id)
        _model_cache[model_id] = model
        return model
    except Exception as exc:
        logger.warning("Could not load embedding model '%s': %s", model_id, exc)
        _model_cache[model_id] = None
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    # Both vectors are L2-normalised at encode time → dot == cosine.
    return sum(x * y for x, y in zip(a, b))


class CommunityEmbeddingIndex:
    """
    Per-topic embedding cache. Loads from disk on construction, lazily encodes
    any community whose summary changed (or is new), persists on flush.
    """

    def __init__(self, cache_path: Path, model_id: str):
        self.cache_path = Path(cache_path)
        self.model_id = model_id
        self.dim: Optional[int] = None
        self.items: dict[str, dict] = {}  # cid → {hash, vec}
        self._dirty = False
        self._load()

    def _load(self) -> None:
        if not self.cache_path.exists():
            return
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if data.get("model") == self.model_id:
                self.dim = data.get("dim")
                self.items = data.get("items", {}) or {}
            else:
                # Model changed → wipe; vectors from a different model don't compare
                logger.info(
                    "Embedding cache model mismatch (%s → %s) — rebuilding",
                    data.get("model"), self.model_id,
                )
        except Exception as exc:
            logger.warning("Could not read embedding cache %s: %s", self.cache_path, exc)

    def flush(self) -> None:
        if not self._dirty:
            return
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(
                json.dumps(
                    {"model": self.model_id, "dim": self.dim, "items": self.items},
                    indent=2,
                ),
                encoding="utf-8",
            )
            self._dirty = False
        except Exception as exc:
            logger.warning("Could not write embedding cache %s: %s", self.cache_path, exc)

    def sync(self, summaries: dict[str, str]) -> None:
        """Encode any community whose summary is new or changed."""
        model = get_model(self.model_id)
        if model is None:
            return
        to_encode_cids: list[str] = []
        to_encode_text: list[str] = []
        for cid, text in summaries.items():
            cid_s = str(cid)
            h = _summary_hash(text)
            current = self.items.get(cid_s)
            if current and current.get("hash") == h and current.get("vec"):
                continue
            to_encode_cids.append(cid_s)
            to_encode_text.append(text)

        # Drop cached entries for communities no longer in the graph.
        gone = set(self.items.keys()) - {str(c) for c in summaries.keys()}
        for cid in gone:
            self.items.pop(cid, None)
            self._dirty = True

        if not to_encode_text:
            return

        try:
            vecs = model.encode(
                to_encode_text,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        except Exception as exc:
            logger.warning("Embedding encode failed: %s", exc)
            return

        for cid, text, vec in zip(to_encode_cids, to_encode_text, vecs):
            vec_list = [float(x) for x in vec]
            self.items[cid] = {"hash": _summary_hash(text), "vec": vec_list}
            self.dim = len(vec_list)
        self._dirty = True

    def rank(self, query: str) -> list[tuple[str, float]]:
        """Return [(cid, similarity)] sorted descending."""
        model = get_model(self.model_id)
        if model is None or not self.items:
            return []
        try:
            q_vec = model.encode([query], normalize_embeddings=True)[0]
            q_list = [float(x) for x in q_vec]
        except Exception as exc:
            logger.warning("Query embedding failed: %s", exc)
            return []
        scored = [(cid, _cosine(q_list, item["vec"])) for cid, item in self.items.items()]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
