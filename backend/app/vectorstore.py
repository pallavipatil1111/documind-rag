"""Vector stores: Pinecone (production, through LangChain) and an in-memory store (tests, local runs)."""
from __future__ import annotations

import math
from typing import Protocol, Sequence

from .config import Settings
from .embeddings import Embeddings
from .models import Chunk, Hit


class VectorStore(Protocol):
    def add(self, chunks: Sequence[Chunk]) -> None: ...
    def search(self, query: str, k: int, doc_ids: Sequence[str] | None = None) -> list[Hit]: ...
    def delete(self, chunk_ids: Sequence[str]) -> None: ...


def _metadata(c: Chunk) -> dict:
    return {"doc_id": c.doc_id, "filename": c.filename, "page": c.page, "index": c.index}


def _chunk(chunk_id: str, text: str, meta: dict) -> Chunk:
    return Chunk(chunk_id, meta["doc_id"], meta["filename"], int(meta["page"]), int(meta["index"]), text)


class MemoryStore:
    """Exact cosine search over vectors kept in a dict."""

    def __init__(self, embeddings: Embeddings):
        self.embeddings = embeddings
        self.rows: dict[str, tuple[Chunk, list[float]]] = {}

    def add(self, chunks: Sequence[Chunk]) -> None:
        vectors = self.embeddings.embed_documents([c.text for c in chunks])
        for c, v in zip(chunks, vectors):
            self.rows[c.id] = (c, v)

    def search(self, query: str, k: int, doc_ids: Sequence[str] | None = None) -> list[Hit]:
        q = self.embeddings.embed_query(query)
        qn = math.sqrt(sum(x * x for x in q)) or 1.0
        hits = []
        for c, v in self.rows.values():
            if doc_ids and c.doc_id not in doc_ids:
                continue
            vn = math.sqrt(sum(x * x for x in v)) or 1.0
            hits.append(Hit(c, sum(a * b for a, b in zip(q, v)) / (qn * vn)))
        hits.sort(key=lambda h: (-h.score, h.chunk.id))
        return hits[:k]

    def delete(self, chunk_ids: Sequence[str]) -> None:
        for i in chunk_ids:
            self.rows.pop(i, None)


class PineconeStore:
    """Pinecone serverless index, written and queried through LangChain's PineconeVectorStore.

    Chunk text and metadata (document, file name, page, position) are stored with each vector so a
    search result can be cited without another lookup. Search can be limited to chosen documents with
    a metadata filter. Deletes go by vector id (serverless indexes don't delete by metadata).
    """

    BATCH = 100

    def __init__(self, settings: Settings, embeddings: Embeddings):
        from langchain_pinecone import PineconeVectorStore
        from pinecone import Pinecone, ServerlessSpec

        if not settings.pinecone_api_key:
            raise RuntimeError("PINECONE_API_KEY is not set (or set VECTOR_STORE=memory for local use)")
        pc = Pinecone(api_key=settings.pinecone_api_key)
        if settings.pinecone_index not in pc.list_indexes().names():
            pc.create_index(name=settings.pinecone_index, dimension=settings.embedding_dimension, metric="cosine",
                            spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region))
        self.namespace = settings.pinecone_namespace
        self.store = PineconeVectorStore(index=pc.Index(settings.pinecone_index), embedding=embeddings,
                                         text_key="text", namespace=self.namespace)

    def add(self, chunks: Sequence[Chunk]) -> None:
        for i in range(0, len(chunks), self.BATCH):
            batch = chunks[i:i + self.BATCH]
            self.store.add_texts([c.text for c in batch], metadatas=[_metadata(c) for c in batch],
                                 ids=[c.id for c in batch], namespace=self.namespace)

    def search(self, query: str, k: int, doc_ids: Sequence[str] | None = None) -> list[Hit]:
        flt = {"doc_id": {"$in": list(doc_ids)}} if doc_ids else None
        results = self.store.similarity_search_with_score(query, k=k, filter=flt, namespace=self.namespace)
        hits = []
        for doc, score in results:
            meta = dict(doc.metadata)
            hits.append(Hit(_chunk(doc.id or f"{meta['doc_id']}-{int(meta['index']):05d}", doc.page_content, meta), float(score)))
        return hits

    def delete(self, chunk_ids: Sequence[str]) -> None:
        for i in range(0, len(chunk_ids), 1000):
            self.store.delete(ids=list(chunk_ids[i:i + 1000]), namespace=self.namespace)


def make_store(settings: Settings, embeddings: Embeddings) -> VectorStore:
    if settings.vector_store == "memory":
        return MemoryStore(embeddings)
    if settings.vector_store == "pinecone":
        return PineconeStore(settings, embeddings)
    raise RuntimeError(f"Unknown VECTOR_STORE: {settings.vector_store}")
