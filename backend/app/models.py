"""Plain data types shared across the pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Page:
    number: int          # 1-based page number in the PDF
    text: str


@dataclass(frozen=True)
class Chunk:
    """A piece of a document that gets embedded and stored in the vector index."""
    id: str
    doc_id: str
    filename: str
    page: int
    index: int           # position of the chunk within the document
    text: str


@dataclass(frozen=True)
class Hit:
    """A chunk returned by vector search, with its cosine similarity to the question."""
    chunk: Chunk
    score: float


@dataclass(frozen=True)
class Source:
    """A passage shown to the model and to the user, numbered for citations: [1], [2]…"""
    number: int
    doc_id: str
    filename: str
    page: int
    text: str
    score: float


@dataclass
class DocumentInfo:
    id: str
    filename: str
    pages: int
    chunks: int
    created_at: str
    chunk_ids: list[str] = field(default_factory=list, repr=False)
