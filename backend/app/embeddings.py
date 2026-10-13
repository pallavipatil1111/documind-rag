"""Embedding models.

- OpenAI text-embedding-3-small (via LangChain) in production: 1536-dimensional semantic vectors.
- HashingEmbeddings: a deterministic bag-of-words vector for tests and offline development. It needs
  no API key but only matches shared words, not meaning, so never use it to judge retrieval quality.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

from .config import Settings


class Embeddings(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


_WORD = re.compile(r"[a-z0-9]+")
_STOP = frozenset("a an and are as at be by for from has have how i in is it of on or that the this to was what when where which who why will with you your do does can".split())


class HashingEmbeddings:
    def __init__(self, dimension: int = 512):
        self.dimension = dimension

    def _vector(self, text: str) -> list[float]:
        v = [0.0] * self.dimension
        words = [w for w in _WORD.findall(text.lower()) if w not in _STOP]
        for w in words:
            stem = w[:-1] if len(w) > 4 and w.endswith("s") else w
            h = int.from_bytes(hashlib.md5(stem.encode()).digest()[:4], "little")
            v[h % self.dimension] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


def make_embeddings(settings: Settings) -> Embeddings:
    if settings.embedding_provider == "hashing":
        return HashingEmbeddings()
    if settings.embedding_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set (or set EMBEDDING_PROVIDER=hashing for offline use)")
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key,
                                dimensions=settings.embedding_dimension)
    raise RuntimeError(f"Unknown EMBEDDING_PROVIDER: {settings.embedding_provider}")
