"""
Document parser — reads files from raw/<topic>/ and extracts plain text.

Supported formats: .pdf, .docx, .html/.htm, .txt, .md, .csv
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".html", ".htm", ".txt", ".md", ".csv"}


class DocumentParser:
    def __init__(self, raw_dir: Path):
        self.raw_dir = Path(raw_dir)

    def parse_topic(self, topic: str) -> list[dict]:
        """
        Scan raw/<topic>/, parse each supported file, return a list of:
          [{"filename": str, "text": str, "metadata": dict}, ...]
        Unsupported extensions are skipped with a warning.
        """
        topic_dir = self.raw_dir / topic
        if not topic_dir.exists():
            raise FileNotFoundError(f"Topic directory not found: {topic_dir}")

        documents = []
        for path in sorted(topic_dir.iterdir()):
            if not path.is_file():
                continue
            ext = path.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                logger.warning("Skipping unsupported file: %s", path.name)
                continue

            try:
                text, extra_meta = self._dispatch(path, ext)
            except Exception as exc:
                logger.error("Failed to parse %s: %s", path.name, exc)
                continue

            if not text or not text.strip():
                logger.warning("Empty content after parsing: %s", path.name)
                continue

            documents.append(
                {
                    "filename": path.name,
                    "text": text.strip(),
                    "metadata": {
                        "source": str(path),
                        "filename": path.name,
                        "mtime": path.stat().st_mtime,
                        **extra_meta,
                    },
                }
            )

        logger.info("Parsed %d documents from topic '%s'", len(documents), topic)
        return documents

    # ── Dispatcher ─────────────────────────────────────────────────────────────

    def _dispatch(self, path: Path, ext: str) -> tuple[str, dict]:
        """Return (text, extra_metadata) for the given file."""
        if ext == ".pdf":
            return self._parse_pdf(path), {}
        if ext == ".docx":
            return self._parse_docx(path), {}
        if ext in (".html", ".htm"):
            return self._parse_html(path), {}
        if ext == ".txt":
            return self._parse_txt(path), {}
        if ext == ".md":
            return self._parse_txt(path), {}  # markdown is plain text
        if ext == ".csv":
            return self._parse_csv(path)
        raise ValueError(f"No parser for extension: {ext}")

    # ── Format-specific parsers ────────────────────────────────────────────────

    def _parse_pdf(self, path: Path) -> str:
        import fitz  # PyMuPDF

        doc = fitz.open(str(path))
        pages = [page.get_text() for page in doc]
        doc.close()
        return "\n\n".join(pages)

    def _parse_docx(self, path: Path) -> str:
        from docx import Document

        doc = Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)

    def _parse_html(self, path: Path) -> str:
        import trafilatura

        raw_html = path.read_bytes()
        text = trafilatura.extract(raw_html, include_comments=False, include_tables=True)
        if not text:
            # Fallback to BeautifulSoup
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(raw_html, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n")
        return text or ""

    def _parse_txt(self, path: Path) -> str:
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        return path.read_bytes().decode("utf-8", errors="replace")

    def _parse_csv(self, path: Path) -> tuple[str, dict]:
        """
        CSV handling, three modes:

        1. Narrative — a column named full_text/text/content/body/article exists.
           Each row's narrative is concatenated, separated by ---.
        2. Entity-per-row — a name/title column AND a type/category/kind column exist.
           Each row is emitted as a labelled entity block with schema-anchored fields.
           This gives the LLM strong extraction signal for tabular reference data
           (lists of tools, products, organisations, glossary terms, etc.).
        3. Generic table — neither pattern matches. The CSV is rendered as a schema
           preamble plus row-by-row key=value list, much easier for an LLM to parse
           than the full `df.to_string()` block (which truncates wide tables).
        """
        import pandas as pd

        df = pd.read_csv(str(path))
        if df.empty:
            return "", {"row_count": 0, "csv_mode": "empty"}

        cols_lower = {c.lower(): c for c in df.columns}

        # Mode 1: narrative column wins outright
        narrative_keys = ("full_text", "text", "content", "body", "article", "description")
        text_col = next((cols_lower[k] for k in narrative_keys if k in cols_lower), None)
        if text_col:
            rows = df[text_col].dropna().astype(str).tolist()
            return "\n\n---\n\n".join(rows), {"row_count": len(df), "csv_mode": "narrative"}

        # Mode 2: entity-per-row
        name_keys = ("name", "title", "entity", "label", "term")
        type_keys = ("type", "category", "kind", "class", "group")
        name_col = next((cols_lower[k] for k in name_keys if k in cols_lower), None)
        type_col = next((cols_lower[k] for k in type_keys if k in cols_lower), None)

        if name_col and type_col:
            blocks: list[str] = []
            other_cols = [c for c in df.columns if c not in (name_col, type_col)]
            for _, row in df.iterrows():
                name = self._csv_cell(row[name_col])
                kind = self._csv_cell(row[type_col])
                if not name:
                    continue
                lines = [f"## {name}", f"- **Type:** {kind or 'unspecified'}"]
                for c in other_cols:
                    val = self._csv_cell(row[c])
                    if val:
                        lines.append(f"- **{c}:** {val}")
                blocks.append("\n".join(lines))
            text = "\n\n".join(blocks)
            return text, {"row_count": len(df), "csv_mode": "entity_per_row"}

        # Mode 3: generic structured table — emit schema then row list
        schema = ", ".join(f"{c} ({df[c].dtype})" for c in df.columns)
        row_lines: list[str] = []
        # Cap rows to keep the LLM prompt bounded; warn in metadata if truncated.
        cap = 200
        for _, row in df.head(cap).iterrows():
            kvs = [f"{c}={self._csv_cell(row[c])}" for c in df.columns if self._csv_cell(row[c])]
            if kvs:
                row_lines.append("- " + "; ".join(kvs))
        text = (
            f"Schema: {schema}\n\n"
            f"Rows ({min(cap, len(df))} of {len(df)}):\n" + "\n".join(row_lines)
        )
        meta = {"row_count": len(df), "csv_mode": "table"}
        if len(df) > cap:
            meta["truncated_to"] = cap
        return text, meta

    @staticmethod
    def _csv_cell(value) -> str:
        """Stringify a CSV cell, dropping NaN/None and normalising whitespace."""
        import pandas as pd  # local — keeps import cost off cold start
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return ""
        s = str(value).strip()
        return " ".join(s.split())
