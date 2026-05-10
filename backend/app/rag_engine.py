from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

_TOKEN = re.compile(r"[a-z0-9]+", re.I)


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text)]


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    body: str


class ManualRAG:
    """Lexical BM25 retrieval over local markdown knowledge files."""

    def __init__(self, knowledge_dir: Path) -> None:
        self._knowledge_dir = knowledge_dir
        self._chunks: list[Chunk] = []
        self._bm25: BM25Okapi | None = None
        self._tokenized: list[list[str]] = []

    def load(self) -> int:
        self._chunks.clear()
        self._tokenized.clear()
        if not self._knowledge_dir.is_dir():
            return 0

        for path in sorted(self._knowledge_dir.glob("*.md")):
            self._chunks.extend(_chunk_markdown(path))

        self._tokenized = [_tokenize(c.title + " " + c.body) for c in self._chunks]
        self._bm25 = BM25Okapi(self._tokenized) if self._tokenized else None
        return len(self._chunks)

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    def retrieve(self, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        if not self._bm25 or not self._chunks:
            return []
        q = _tokenize(query)
        if not q:
            return []
        scores = self._bm25.get_scores(q)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        out: list[tuple[Chunk, float]] = []
        for idx, score in ranked:
            out.append((self._chunks[idx], float(score)))
        return out


def _chunk_markdown(path: Path) -> list[Chunk]:
    text = path.read_text(encoding="utf-8")
    doc_id = path.stem
    parts = re.split(r"\n(?=#{1,6}\s)", text)
    chunks: list[Chunk] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        title = doc_id.replace("-", " ").title()
        body = part
        if part.startswith("#"):
            lines = part.splitlines()
            title = lines[0].lstrip("#").strip() or title
            body = "\n".join(lines[1:]).strip() or part
        chunks.append(
            Chunk(
                chunk_id=f"{doc_id}-{uuid.uuid4().hex[:8]}",
                doc_id=doc_id,
                title=title,
                body=body[:8000],
            )
        )
    if not chunks:
        chunks.append(
            Chunk(chunk_id=f"{doc_id}-full", doc_id=doc_id, title=doc_id, body=text[:8000])
        )
    return chunks
